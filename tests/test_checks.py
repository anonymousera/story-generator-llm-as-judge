"""Deterministic sentence-length checks (no LLM, no API key needed)."""
import checks


def test_split_sentences_on_terminal_punctuation():
    text = "Hello there. How are you? I am fine! "
    assert checks.split_sentences(text) == ["Hello there", "How are you", "I am fine"]


def test_split_sentences_ignores_blanks():
    assert checks.split_sentences("...!!!???") == []


def test_short_sentences_pass():
    text = "The cat sat down. It was a sunny day."
    assert checks.long_sentences(text) == []
    assert checks.length_report(text).startswith("PASS")


def test_sentence_at_threshold_is_flagged():
    # Exactly 20 words: the rule is "< 20", so 20 must be flagged.
    twenty = " ".join(["word"] * 20) + "."
    flagged = checks.long_sentences(twenty)
    assert len(flagged) == 1
    assert flagged[0][1] == 20


def test_nineteen_words_passes():
    nineteen = " ".join(["word"] * 19) + "."
    assert checks.long_sentences(nineteen) == []


def test_length_report_lists_offenders():
    long = " ".join(["word"] * 25) + "."
    report = checks.length_report("Short one. " + long)
    assert report.startswith("FAIL")
    assert "25 words" in report


def test_custom_max_words():
    text = "One two three four five."
    assert checks.long_sentences(text, max_words=5) == [("One two three four five", 5)]
    assert checks.long_sentences(text, max_words=6) == []
