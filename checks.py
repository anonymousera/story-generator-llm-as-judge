"""Deterministic (non-LLM) checks.

Some preferences are cheaper and far more reliable to verify in plain Python
than by asking a model. Sentence length is the clearest example: an LLM will
miscount words, but a split on terminal punctuation will not. The result feeds
into the Final Judge alongside the LLM critiques.
"""
import re

MAX_WORDS = 25


def split_sentences(text: str) -> list[str]:
    """Split on sentence-terminating punctuation (. ? !)."""
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def long_sentences(text: str, max_words: int = MAX_WORDS) -> list[tuple[str, int]]:
    """Return (sentence, word_count) for sentences with >= max_words words."""
    flagged = []
    for sentence in split_sentences(text):
        word_count = len(sentence.split())
        if word_count >= max_words:
            flagged.append((sentence, word_count))
    return flagged


def length_report(text: str, max_words: int = MAX_WORDS) -> str:
    """Human-readable summary the Final Judge can fold into its assessment."""
    flagged = long_sentences(text, max_words)
    if not flagged:
        return f"PASS: every sentence is under {max_words} words."

    lines = [f"FAIL: {len(flagged)} sentence(s) reach {max_words}+ words (should be < {max_words}):"]
    for sentence, count in flagged:
        preview = sentence if len(sentence) <= 80 else sentence[:77] + "..."
        lines.append(f"  - ({count} words) {preview}")
    return "\n".join(lines)
