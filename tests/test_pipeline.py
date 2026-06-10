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

def _stub_generation(monkeypatch):
    """Stub categorize + generate_story; return the call recorder for asserts."""
    calls = []

    def fake_generate(user_input, categories, revision_notes=None,
                      previous_story=None, user_feedback=None):
        calls.append({"revision_notes": revision_notes, "previous_story": previous_story})
        return f"story v{len(calls)}"

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
