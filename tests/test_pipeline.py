"""Pipeline logic tests.

All LLM calls are mocked, so these run without an API key. They cover the parts
that must be reliable regardless of what the model returns: JSON parsing, the
compulsory-safety gate, the pass/threshold logic, category filtering, and the
bounded revision loop.
"""
import json

import pipeline
import prompts


# --- helpers ---------------------------------------------------------------

def _passing_assessment():
    return {
        "compulsory": {k: "pass" for k in prompts.COMPULSORY},
        "quality_scores": {"simplicity": 4, "engagement": 4, "readability": 4},
        "passed": True,
        "revision_notes": "",
    }


def _failing_assessment():
    bad = {k: "pass" for k in prompts.COMPULSORY}
    bad["no_violence"] = "fail"
    return {
        "compulsory": bad,
        "quality_scores": {"simplicity": 2, "engagement": 2, "readability": 2},
        "passed": False,
        "revision_notes": "Remove the scary part and shorten the sentences.",
    }


# --- _parse_json -----------------------------------------------------------

def test_parse_json_direct():
    assert pipeline._parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_embedded_in_prose():
    assert pipeline._parse_json('Sure! {"a": 1, "b": 2} done') == {"a": 1, "b": 2}


def test_parse_json_unparseable_returns_none():
    assert pipeline._parse_json("there is no json here") is None


# --- compulsory gate -------------------------------------------------------

def test_compulsory_ok_all_pass():
    assert pipeline.compulsory_ok(_passing_assessment()) is True


def test_compulsory_ok_case_insensitive():
    a = _passing_assessment()
    a["compulsory"]["no_violence"] = "PASS"
    assert pipeline.compulsory_ok(a) is True


def test_compulsory_ok_explicit_fail():
    assert pipeline.compulsory_ok(_failing_assessment()) is False


def test_compulsory_ok_missing_key_fails_closed():
    a = _passing_assessment()
    del a["compulsory"]["no_bad_words"]
    assert pipeline.compulsory_ok(a) is False


def test_compulsory_ok_empty_fails_closed():
    assert pipeline.compulsory_ok({"compulsory": {}}) is False


# --- quality threshold -----------------------------------------------------

def test_quality_ok_above_threshold():
    assert pipeline._quality_ok(_passing_assessment()) is True


def test_quality_ok_one_below_threshold():
    a = _passing_assessment()
    a["quality_scores"]["engagement"] = 2
    assert pipeline._quality_ok(a) is False


def test_quality_ok_empty_fails():
    assert pipeline._quality_ok({"quality_scores": {}}) is False


def test_quality_ok_non_numeric_fails():
    assert pipeline._quality_ok({"quality_scores": {"x": "good"}}) is False


def test_is_passing_requires_both():
    a = _passing_assessment()
    a["compulsory"]["no_violence"] = "fail"
    assert pipeline.is_passing(a) is False


# --- categorize ------------------------------------------------------------

def test_categorize_filters_unknown_and_lowercases(monkeypatch):
    monkeypatch.setattr(pipeline, "call_model", lambda *a, **k: "magic, friends, banana, OTHER")
    assert pipeline.categorize("x") == ["magic", "friends", "other"]


def test_categorize_defaults_to_other(monkeypatch):
    monkeypatch.setattr(pipeline, "call_model", lambda *a, **k: "banana, zzz")
    assert pipeline.categorize("x") == ["other"]


# --- evaluate --------------------------------------------------------------

def test_evaluate_parses_valid_final_judge(monkeypatch):
    good = json.dumps(_passing_assessment())

    def fake(prompt, **kw):
        return good if "head editor" in prompt else "a critique"

    monkeypatch.setattr(pipeline, "call_model", fake)
    a = pipeline.evaluate("a nice story")
    assert pipeline.is_passing(a) is True
    assert set(a["_critiques"]) == {"positive", "negative", "general"}
    assert "_length_report" in a


def test_evaluate_fails_closed_on_bad_json(monkeypatch):
    def fake(prompt, **kw):
        return "not json at all" if "head editor" in prompt else "a critique"

    monkeypatch.setattr(pipeline, "call_model", fake)
    a = pipeline.evaluate("a story")
    assert a["passed"] is False
    assert a["revision_notes"]            # a nudge is provided
    assert pipeline.compulsory_ok(a) is False


# --- run: revision-loop control flow ---------------------------------------

def _safe_guard():
    return {"severity": "safe", "reason": "ok", "sanitize_note": "", "safe_redirect": ""}


def _stub_generation(monkeypatch, guard=None):
    """Stub guard + categorize + generate_story; return the call recorder."""
    calls = []

    def fake_generate(user_input, categories, revision_notes=None,
                      previous_story=None, user_feedback=None, sanitize_note=None):
        calls.append({
            "revision_notes": revision_notes,
            "previous_story": previous_story,
            "user_feedback": user_feedback,
            "sanitize_note": sanitize_note,
        })
        return f"story v{len(calls)}"

    monkeypatch.setattr(pipeline, "screen_input", lambda text: guard or _safe_guard())
    monkeypatch.setattr(pipeline, "categorize", lambda x: ["friends"])
    monkeypatch.setattr(pipeline, "generate_story", fake_generate)
    return calls


def test_run_stops_on_first_pass(monkeypatch):
    calls = _stub_generation(monkeypatch)
    monkeypatch.setattr(pipeline, "evaluate", lambda story: _passing_assessment())

    result = pipeline.run("a story please", verbose=False)
    assert result.iterations == 1
    assert len(calls) == 1
    assert result.compulsory_ok is True


def test_run_revises_then_passes(monkeypatch):
    calls = _stub_generation(monkeypatch)
    seq = iter([_failing_assessment(), _passing_assessment()])
    monkeypatch.setattr(pipeline, "evaluate", lambda story: next(seq))

    result = pipeline.run("a story please", verbose=False)
    assert result.iterations == 2
    assert len(calls) == 2
    # The judge's revision_notes were injected into the second generation.
    assert calls[1]["revision_notes"] == _failing_assessment()["revision_notes"]
    assert calls[1]["previous_story"] == "story v1"
    assert result.compulsory_ok is True


def test_run_respects_max_revisions(monkeypatch):
    calls = _stub_generation(monkeypatch)
    monkeypatch.setattr(pipeline, "evaluate", lambda story: _failing_assessment())

    result = pipeline.run("a story please", verbose=False)
    assert result.iterations == pipeline.MAX_REVISIONS + 1   # 1 draft + 2 revisions
    assert len(calls) == pipeline.MAX_REVISIONS + 1
    assert result.compulsory_ok is False                     # gate would withhold


# --- input guard -----------------------------------------------------------

def test_screen_input_parses_valid(monkeypatch):
    payload = '{"severity": "egregious", "reason": "graphic", "sanitize_note": "", "safe_redirect": "try a puppy"}'
    monkeypatch.setattr(pipeline, "call_model", lambda *a, **k: payload)
    v = pipeline.screen_input("something nasty")
    assert v["severity"] == "egregious"


def test_screen_input_fails_soft_to_mild(monkeypatch):
    monkeypatch.setattr(pipeline, "call_model", lambda *a, **k: "not json")
    v = pipeline.screen_input("ambiguous")
    assert v["severity"] == "mild"
    assert v["sanitize_note"]            # a steer is provided


def test_screen_input_rejects_unknown_severity(monkeypatch):
    monkeypatch.setattr(pipeline, "call_model", lambda *a, **k: '{"severity": "spicy"}')
    assert pipeline.screen_input("x")["severity"] == "mild"


def test_run_blocks_egregious_without_generating(monkeypatch):
    guard = {"severity": "egregious", "reason": "graphic", "sanitize_note": "",
             "safe_redirect": "How about a story about a kind robot?"}
    calls = _stub_generation(monkeypatch, guard=guard)
    monkeypatch.setattr(pipeline, "evaluate", lambda story: _passing_assessment())

    result = pipeline.run("write something violent", verbose=False)
    assert result.blocked is True
    assert result.story == ""
    assert result.iterations == 0
    assert len(calls) == 0                # storyteller never ran
    assert result.block_message == guard["safe_redirect"]


def test_run_guard_disabled_withholds_when_gate_fails(monkeypatch):
    """With the front-door guard off, an always-failing judge must drive the
    pipeline to fail-closed (compulsory_ok False) after exhausting revisions —
    the deterministic proof of the WITHHELD path the live eval can only sample."""
    calls = _stub_generation(monkeypatch)

    def boom(text):
        raise AssertionError("screen_input must not run when guard_enabled=False")

    monkeypatch.setattr(pipeline, "screen_input", boom)
    monkeypatch.setattr(pipeline, "evaluate", lambda story: _failing_assessment())

    result = pipeline.run("anything", verbose=False, guard_enabled=False)
    assert result.blocked is False
    assert len(calls) == pipeline.MAX_REVISIONS + 1     # storyteller ran the full budget
    assert result.compulsory_ok is False                # gate withholds end-to-end


def test_history_captures_full_per_iteration_detail(monkeypatch):
    _stub_generation(monkeypatch)

    def fake_eval(story):
        a = _passing_assessment()
        a["_critiques"] = {"positive": "lovely", "negative": "one nit", "general": "solid"}
        a["_length_report"] = "PASS: every sentence is under 20 words."
        return a

    monkeypatch.setattr(pipeline, "evaluate", fake_eval)
    result = pipeline.run("a story", verbose=False)

    h = result.history[0]
    assert h["story"] == "story v1"
    assert h["judges"] == {"positive": "lovely", "negative": "one nit", "general": "solid"}
    assert h["length_check"].startswith("PASS")
    assert h["final_judge"]["passed"] is True
    # The detail is moved out of the top-level assessment, not duplicated there.
    assert "_critiques" not in result.assessment
    assert "_length_report" not in result.assessment


def test_run_threads_feedback_through_revisions(monkeypatch):
    """User feedback must survive the internal revision loop, not just the first
    generation (the bug where revisions dropped user_feedback)."""
    calls = _stub_generation(monkeypatch)
    seq = iter([_failing_assessment(), _passing_assessment()])
    monkeypatch.setattr(pipeline, "evaluate", lambda story: next(seq))

    pipeline.run("original request", categories=["friends"], previous_story="old story",
                 user_feedback="make it about beaches", verbose=False)

    assert calls[0]["user_feedback"] == "make it about beaches"   # initial generation
    assert calls[1]["user_feedback"] == "make it about beaches"   # and the revision


def test_run_sanitizes_mild_and_proceeds(monkeypatch):
    guard = {"severity": "mild", "reason": "mentions a monster",
             "sanitize_note": "Make the monster friendly and silly.", "safe_redirect": ""}
    calls = _stub_generation(monkeypatch, guard=guard)
    monkeypatch.setattr(pipeline, "evaluate", lambda story: _passing_assessment())

    result = pipeline.run("a story about a scary monster", verbose=False)
    assert result.blocked is False
    assert result.iterations == 1
    # The sanitize note was threaded into generation.
    assert calls[0]["sanitize_note"] == guard["sanitize_note"]
