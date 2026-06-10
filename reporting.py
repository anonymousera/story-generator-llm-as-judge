"""JSON artifacts for debugging and submission.

The pipeline itself keeps everything in memory; these helpers are the only place
that touches the filesystem. Two outputs:

  save_trace  -> runs/<timestamp>.json : one StoryResult (story + guard verdict +
                 per-iteration judge scores) for a single request.
  save_report -> eval_report.json      : the full eval_cases.py sweep.
"""
import json
import os
import time
from dataclasses import asdict


def save_trace(result, request: str, out_dir: str = "runs") -> str:
    """Persist a single run (a pipeline.StoryResult) as pretty JSON."""
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"{stamp}.json")
    payload = {"request": request, "saved_at": stamp, **asdict(result)}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def save_report(results: list[dict], summary: dict, path: str = "eval_report.json") -> str:
    """Persist a full eval sweep (per-case rows + summary) as pretty JSON."""
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path
