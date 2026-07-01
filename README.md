# Children's Story Generator

A small agentic system that turns any bedtime-story request into a story that is
**safe and appropriate for ages 5–10**. It is built as a **router** and an **evaluator–optimizer**
loop: a storyteller drafts, a panel of LLM judges critiques against a fixed list
of preferences, a final judge aggregates and gates, and the storyteller revises
(bounded) until the story passes or the budget runs out, with a front-door
safety guard and an interactive feedback loop on top.

> The quality is assessed based on not just the creativity and quality of the story, but also the safety and appropriateness of the story for ages 5 to 10.

---

## Quickstart

```bash
# 1. Install dependencies 
pip install -r requirements.txt

# 2. Add your OpenAI key in the .env file

# 3. Run the main.py file
python main.py
```

### Command-line flags

| Command | Behavior |
|---|---|
| `python main.py` | Normal interactive mode (recommended). |
| `python main.py --quiet` | Hide the live `[guard]`/`[router]`/`[judge]` logs. The JSON trace is still written. |
| `python main.py --print-unsafe` | **Eval/debug only.** Print a story with a `WARNING` header even if it fails a compulsory safety check (default behavior withholds it). |

---

## How it works

```mermaid
flowchart LR
    input([User input]) --> guard{"Input Guard<br/>(temp 0.0)<br/>classify intent:<br/>safe / mild / egregious<br/>+ jailbreak detection"}
    guard -->|egregious| block([Blocked at the door<br/>print safe redirect<br/>storyteller never runs])
    guard -->|"mild → inject sanitize note"| cat
    guard -->|safe| cat
    cat["Categorization<br/>(multi-label, can be &gt;1)<br/>magic · adventure · mystery<br/>educational · family · friends · other"]
    cat --> tmpl["Prompt selection / generation<br/>from the chosen category template(s)"]
    tmpl --> gen["LLM Call — Storyteller<br/>temp ~0.9 (creative)<br/>max 3 generations total"]
    gen --> draft["Story draft"]

    draft --> det["Deterministic checks (Python, no LLM)<br/>sentence length &lt; 25 words<br/>(tokenize on . ? !)"]
    draft --> j1["Judge 1 — positive critique<br/>temp ~0.2"]
    draft --> j2["Judge 2 — negative critique<br/>temp ~0.2"]
    draft --> j3["Judge 3 — general critique<br/>temp ~0.2"]

    det  -->|length report| final
    j1   -->|metric 1| final
    j2   -->|metric 2| final
    j3   -->|metric 3| final

    final["Final Judge<br/>structured output:<br/>• compulsory items → pass/fail<br/>• quality scores<br/>• revision_notes (the nudge)<br/>• passed: bool"]

    final -->|"not passed AND revisions &lt; 2<br/>(inject revision_notes)"| gen
    final -->|"passed OR revisions exhausted"| gate{"Compulsory<br/>safety items<br/>all pass?"}

    gate -->|yes| out([Print story])
    gate -->|"no · print_unsafe = false (default)"| supp([Withhold story<br/>print safe fallback])
    gate -->|"no · print_unsafe = true (eval only)"| warn([Print story<br/>with WARNING header])
```

The pipeline, stage by stage:

1. **Input Guard** — screens the *request* before any generation and classifies
   intent as `safe` / `mild` / `egregious` (also catches jailbreak / prompt
   injection). `mild` requests are sanitized (a steer is injected into the
   storyteller); `egregious` ones are hard-blocked with a friendly redirect and
   the storyteller never runs. Fails *soft* to `mild` on a parse glitch.
2. **Categorization** — multi-label routing into one or more of *magic,
   adventure, mystery, educational, family, friends, other*; each category
   contributes a tailored steering snippet.
3. **Storyteller** — generates the story with a strong system prompt and high
   temperature for creativity.
4. **Evaluation (parallel)** — a deterministic sentence-length check plus three
   LLM judges (positive / negative / general stance) critique the draft against
   the preference list at low temperature.
5. **Final Judge** — aggregates the judges + length report into **structured
   JSON**: per-compulsory-item pass/fail, quality scores, an overall `passed`
   flag, and `revision_notes`.
6. **Bounded revision loop** — if not passing, `revision_notes` are injected back
   into the storyteller; capped at **2 revisions** (3 generations max).
7. **Compulsory safety gate** — before printing, every compulsory item must
   pass. If not, the story is **withheld** (default) or printed with a `WARNING`
   under `--print-unsafe`.
8. **Feedback loop** — the reader can request changes (up to 5), each re-entering
   the pipeline; the whole conversation is saved to a single JSON file

---

Design choices can be found in [DESIGN.md](https://github.com/anonymousera/story-generator-llm-as-judge/blob/main/DESIGN.md). 


---

## Project structure

| File | Responsibility |
|---|---|
| `main.py` | CLI entry point: I/O, safety gate presentation, feedback loop, trace writing |
| `pipeline.py` | Orchestration: guard → categorize → generate → evaluate → bounded revise |
| `prompts.py` | Preferences, category templates, and every prompt builder |
| `checks.py` | Deterministic (non-LLM) checks — sentence length |
| `llm.py` | Thin OpenAI wrapper (model fixed to `gpt-3.5-turbo`) |
| `reporting.py` | JSON artifacts: per-conversation traces and the eval report |
| `eval_cases.py` | Curated live test suite (routing + safety outcomes) |
| `tests/` | Fast, mocked unit tests (no API key needed) |
| `DESIGN.md` | Full system design + block diagram |

### Key configuration (the knobs)

| Constant | Where | Value | Meaning |
|---|---|---|---|
| `MAX_REVISIONS` | `pipeline.py` | `2` | Internal judge-driven revisions (3 generations max) |
| `MIN_QUALITY` | `pipeline.py` | `3` | Minimum per-dimension quality score to pass |
| `MAX_WORDS` | `checks.py` | `25` | Sentence-length limit (preferred, not compulsory) |
| `MAX_FEEDBACK` | `main.py` | `5` | Max user change requests per conversation |
| Temperatures | `pipeline.py` | `0.9 / 0.2 / 0.0` | Storyteller / judges / router & guard |

---

## Output artifacts

- **`runs/<timestamp>.json`** — one file per conversation, rewritten in place as
  feedback rounds are added. Contains every turn (initial + feedback) and, for
  each, the full per-iteration detail (story, all three judges' critiques, the
  length check, and the final judge's structured verdict).
- **`eval_report.json`** — written by `eval_cases.py`; a summary plus per-case
  rows (guard severity, outcome, iterations, story, full history).


---

## Testing & evaluation

```bash
# Fast unit tests — all LLM calls mocked, no API key required
python -m pytest -q

# Live end-to-end eval (needs an API key); writes eval_report.json
python eval_cases.py                 # all groups
python eval_cases.py gate adversarial  # safety-focused subset
```

The unit tests cover the deterministic logic: the length check, JSON parsing,
the compulsory gate (fail-closed on missing items), the categorizer, the input
guard, and the bounded revision loop (including feedback threading and the
withhold path). The live eval exercises routing and the safety gate against the
real model.


