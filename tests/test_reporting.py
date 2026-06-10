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


def test_save_trace_writes_valid_json(tmp_path):
    path = reporting.save_trace(_sample_result(), "a story about a cat", out_dir=str(tmp_path))
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["request"] == "a story about a cat"
    assert data["story"] == "Once upon a time..."
    assert data["guard"]["severity"] == "safe"
    assert data["compulsory_ok"] is True


def test_save_report_writes_summary_and_results(tmp_path):
    out = tmp_path / "report.json"
    rows = [{"request": "x", "outcome": "PRINTED", "compulsory_ok": True}]
    summary = {"passed": 1, "total": 1}
    path = reporting.save_report(rows, summary, path=str(out))
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["summary"]["passed"] == 1
    assert data["results"][0]["outcome"] == "PRINTED"
    assert "generated_at" in data
