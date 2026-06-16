"""JSON artifacts for debugging.

The pipeline itself keeps everything in memory; these helpers are the only place
that touches the filesystem.

  A "conversation" is one original request plus any follow-up feedback rounds.
  It lives in a single file (runs/<timestamp>.json) that is rewritten in place
  after every turn — so feedback updates the original trace instead of spawning
  new files.

  new_conversation_path -> allocate runs/<timestamp>.json (once per conversation)
  make_turn             -> build one turn dict from a pipeline.StoryResult
  save_conversation     -> (over)write the whole conversation to its file
  save_report           -> eval_report.json : the full eval_cases.py sweep
"""
import json
import os
import time
from dataclasses import asdict


def new_conversation_path(out_dir: str = "runs") -> str:
    """Allocate a stable path for one conversation (no write yet)."""
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return os.path.join(out_dir, f"{stamp}.json")


def make_turn(result, kind: str, feedback: str | None = None) -> dict:
    """One turn = how this draft came to be + the full StoryResult detail.

    kind is "initial" or "feedback"; feedback carries the user's change request.
    """
    turn = {"kind": kind}
    if feedback is not None:
        turn["feedback"] = feedback
    turn.update(asdict(result))
    return turn


def save_conversation(request: str, turns: list[dict], path: str) -> str:
    """Write the whole conversation (all turns so far) to `path`, overwriting."""
    payload = {
        "request": request,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "turn_count": len(turns),
        "turns": turns,
    }
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
