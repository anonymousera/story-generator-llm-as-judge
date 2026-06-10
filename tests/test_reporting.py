"""JSON artifact writers (no API key needed)."""
import json

import pipeline
import reporting


def _sample_result():
    return pipeline.StoryResult(
        story="Once upon a time...",
        categories=["friends"],
        assessment={"compulsory": {"no_violence": "pass"}, "passed": True},
        compulsory_ok=True,
        iterations=1,
        history=[{"attempt": 1, "passed": True}],
        guard={"severity": "safe"},
    )


def test_make_turn_embeds_result_and_metadata():
    turn = reporting.make_turn(_sample_result(), "feedback", feedback="make it funnier")
    assert turn["kind"] == "feedback"
    assert turn["feedback"] == "make it funnier"
    assert turn["story"] == "Once upon a time..."          # full StoryResult detail inlined
    assert turn["guard"]["severity"] == "safe"


def test_conversation_updates_same_file_across_turns(tmp_path):
    path = str(tmp_path / "conv.json")

    # Initial turn.
    turns = [reporting.make_turn(_sample_result(), "initial")]
    reporting.save_conversation("a story about a cat", turns, path)

    # Feedback turn appended -> same file, rewritten.
    turns.append(reporting.make_turn(_sample_result(), "feedback", feedback="shorter please"))
    reporting.save_conversation("a story about a cat", turns, path)

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["request"] == "a story about a cat"
    assert data["turn_count"] == 2
    assert data["turns"][0]["kind"] == "initial"
    assert data["turns"][1]["kind"] == "feedback"
    assert data["turns"][1]["feedback"] == "shorter please"
    # Only one file exists for the conversation.
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_save_report_writes_summary_and_results(tmp_path):
    out = tmp_path / "report.json"
    rows = [{"request": "x", "outcome": "PRINTED", "compulsory_ok": True}]
    summary = {"passed": 1, "total": 1}
    path = reporting.save_report(rows, summary, path=str(out))
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["summary"]["passed"] == 1
    assert data["results"][0]["outcome"] == "PRINTED"
    assert "generated_at" in data
