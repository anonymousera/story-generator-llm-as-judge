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
    # Exactly MAX_WORDS: the rule is "< MAX_WORDS", so the boundary must flag.
    at_limit = " ".join(["word"] * checks.MAX_WORDS) + "."
    flagged = checks.long_sentences(at_limit)
    assert len(flagged) == 1
    assert flagged[0][1] == checks.MAX_WORDS


def test_just_under_limit_passes():
    under = " ".join(["word"] * (checks.MAX_WORDS - 1)) + "."
    assert checks.long_sentences(under) == []


def test_length_report_lists_offenders():
    count = checks.MAX_WORDS + 5
    long = " ".join(["word"] * count) + "."
    report = checks.length_report("Short one. " + long)
    assert report.startswith("FAIL")
    assert f"{count} words" in report


def test_custom_max_words():
    text = "One two three four five."
    assert checks.long_sentences(text, max_words=5) == [("One two three four five", 5)]
    assert checks.long_sentences(text, max_words=6) == []
