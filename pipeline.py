"""Evaluator-optimizer orchestration.

Flow (see DESIGN.md):
  categorize -> generate -> (judges + length check) -> final judge -> gate
The Final Judge's revision_notes are injected back into the storyteller, bounded
to MAX_REVISIONS. A separate compulsory-safety gate decides what gets printed.
"""
import json
import re
from dataclasses import dataclass, field

import checks
import prompts
from llm import call_model

MAX_REVISIONS = 2          # 1 initial draft + up to 2 revisions = max 3 generations.
MIN_QUALITY = 3            # Each quality score must reach this to "pass".

STORY_TEMP = 0.9           # Hot: creative generation.
JUDGE_TEMP = 0.2           # Cold: consistent evaluation.
ROUTER_TEMP = 0.0          # Deterministic categorization.
GUARD_TEMP = 0.0           # Deterministic input screening.

DEFAULT_REDIRECT = "Let's pick a happier story! How about a friendly dragon who loves to bake?"


@dataclass
class StoryResult:
    story: str
    categories: list[str]
    assessment: dict           # Final Judge structured output.
    compulsory_ok: bool        # Did every compulsory item pass?
    iterations: int            # How many times the storyteller ran.
    history: list[dict] = field(default_factory=list)  # Per-iteration trace.
    guard: dict = field(default_factory=dict)          # Input-guard verdict.
    blocked: bool = False      # True if the request was hard-blocked at the door.
    block_message: str = ""    # Kid-friendly redirect shown when blocked.


def _parse_json(text: str) -> dict | None:
    """Best-effort JSON extraction from a model response."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def screen_input(text: str) -> dict:
    """Front-door guard: classify the request's intent before generating.

    Returns a dict with 'severity' in {safe, mild, egregious}. On an unparseable
    response we fail *soft* to 'mild' (sanitize and proceed) rather than blocking
    a legitimate child over a parse glitch — the downstream judges + gate remain.
    """
    raw = call_model(prompts.input_guard_prompt(text), temperature=GUARD_TEMP, max_tokens=200)
    verdict = _parse_json(raw)
    if verdict is None or verdict.get("severity") not in {"safe", "mild", "egregious"}:
        return {
            "severity": "mild",
            "reason": "Guard response could not be parsed; defaulting to gentle handling.",
            "sanitize_note": "Keep everything calm, kind, and age-appropriate.",
            "safe_redirect": DEFAULT_REDIRECT,
        }
    return verdict


def categorize(user_input: str) -> list[str]:
    raw = call_model(prompts.categorize_prompt(user_input), temperature=ROUTER_TEMP, max_tokens=60)
    found = [c.strip().lower() for c in raw.split(",")]
    matched = [c for c in found if c in prompts.CATEGORIES]
    return matched or ["other"]


def evaluate(story: str) -> dict:
    """Run the three judges + deterministic check, then the Final Judge."""
    critiques = {
        stance: call_model(prompts.judge_prompt(story, stance), temperature=JUDGE_TEMP, max_tokens=400)
        for stance in ("positive", "negative", "general")
    }
    length_report = checks.length_report(story)

    raw = call_model(
        prompts.final_judge_prompt(story, critiques, length_report),
        temperature=JUDGE_TEMP,
        max_tokens=800,
    )
    assessment = _parse_json(raw)
    if assessment is None:
        # If the judge returned unparseable output, fail closed: treat as not
        # passed and feed the raw text back as a revision nudge.
        assessment = {
            "compulsory": {},
            "quality_scores": {},
            "passed": False,
            "revision_notes": "The evaluation could not be parsed; simplify and shorten the story.",
        }
    assessment["_critiques"] = critiques
    assessment["_length_report"] = length_report
    return assessment


def compulsory_ok(assessment: dict) -> bool:
    """Independently confirm every compulsory item is marked pass.

    We do not trust the judge's top-level `passed` for the safety gate; we check
    the per-item verdicts ourselves. A missing item counts as a failure.
    """
    verdicts = assessment.get("compulsory", {})
    for key in prompts.COMPULSORY:
        if str(verdicts.get(key, "fail")).lower() != "pass":
            return False
    return True


def _quality_ok(assessment: dict) -> bool:
    scores = assessment.get("quality_scores", {})
    if not scores:
        return False
    try:
        return min(int(v) for v in scores.values()) >= MIN_QUALITY
    except (TypeError, ValueError):
        return False


def is_passing(assessment: dict) -> bool:
    """Overall pass = all compulsory items pass AND quality is good enough."""
    return compulsory_ok(assessment) and _quality_ok(assessment)


def generate_story(
    user_input: str,
    categories: list[str],
    revision_notes: str | None = None,
    previous_story: str | None = None,
    user_feedback: str | None = None,
    sanitize_note: str | None = None,
) -> str:
    prompt = prompts.storyteller_prompt(
        user_input,
        categories,
        revision_notes=revision_notes,
        previous_story=previous_story,
        user_feedback=user_feedback,
        sanitize_note=sanitize_note,
    )
    return call_model(
        prompt,
        system=prompts.storyteller_system(),
        temperature=STORY_TEMP,
    ).strip()


def run(
    user_input: str,
    categories: list[str] | None = None,
    previous_story: str | None = None,
    user_feedback: str | None = None,
    verbose: bool = True,
    guard_enabled: bool = True,
) -> StoryResult:
    """Generate and refine a story for a single request.

    `previous_story` + `user_feedback` seed a human-requested revision; otherwise
    a fresh story is written from `user_input`.

    `guard_enabled=False` skips the front-door guard so the downstream judges +
    compulsory gate can be exercised in isolation (used by the eval harness to
    test the gate's fail-closed path).
    """
    # 1) Front-door guard on the incoming text (the request, or the human's
    #    change request on a feedback turn).
    if guard_enabled:
        guard = screen_input(user_feedback or user_input)
    else:
        guard = {"severity": "safe", "reason": "guard disabled (eval)",
                 "sanitize_note": "", "safe_redirect": ""}
    if verbose:
        print(f"[guard] severity={guard.get('severity')}: {guard.get('reason', '')}")

    if guard.get("severity") == "egregious":
        # Hard block: never call the storyteller.
        return StoryResult(
            story="",
            categories=[],
            assessment={},
            compulsory_ok=False,
            iterations=0,
            guard=guard,
            blocked=True,
            block_message=guard.get("safe_redirect") or DEFAULT_REDIRECT,
        )

    # Mild requests are sanitized; this note steers every generation below.
    sanitize_note = guard.get("sanitize_note") if guard.get("severity") == "mild" else None

    if categories is None:
        categories = categorize(user_input)
        if verbose:
            print(f"[router] categories: {', '.join(categories)}")

    story = generate_story(
        user_input,
        categories,
        previous_story=previous_story,
        user_feedback=user_feedback,
        sanitize_note=sanitize_note,
    )

    history: list[dict] = []
    assessment: dict = {}

    for attempt in range(1, MAX_REVISIONS + 2):  # 1 draft + MAX_REVISIONS revisions.
        assessment = evaluate(story)
        # Pull the per-iteration detail off the assessment so the top-level copy
        # stays clean while history keeps the full picture for every attempt.
        critiques = assessment.pop("_critiques", {})
        length_report = assessment.pop("_length_report", "")
        passed = is_passing(assessment)
        history.append({
            "attempt": attempt,
            "story": story,
            "judges": critiques,                 # all three judges' critiques verbatim
            "length_check": length_report,       # deterministic sentence-length report
            "final_judge": assessment,           # structured verdict (compulsory/scores/notes)
            "passed": passed,
            "compulsory_ok": compulsory_ok(assessment),
        })
        if verbose:
            scores = assessment.get("quality_scores", {})
            print(f"[judge] attempt {attempt}: passed={passed} "
                  f"compulsory_ok={compulsory_ok(assessment)} scores={scores}")

        if passed or attempt == MAX_REVISIONS + 1:
            break

        # Not passing and budget remains -> revise with the judge's nudge.
        notes = assessment.get("revision_notes") or "Simplify the language and shorten sentences."
        if verbose:
            print(f"[reviser] nudging storyteller: {notes}")
        story = generate_story(
            user_input,
            categories,
            revision_notes=notes,
            previous_story=story,
            user_feedback=user_feedback,
            sanitize_note=sanitize_note,
        )

    return StoryResult(
        story=story,
        categories=categories,
        assessment=assessment,
        compulsory_ok=compulsory_ok(assessment),
        iterations=len(history),
        history=history,
        guard=guard,
    )
