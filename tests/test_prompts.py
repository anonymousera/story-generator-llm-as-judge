"""Storyteller prompt construction (pure string logic, no API key)."""
import prompts


def test_feedback_included_without_previous_story():
    # Regression: feedback used to be gated behind a non-empty previous_story,
    # so it was silently dropped after a blocked/empty turn.
    p = prompts.storyteller_prompt(
        "a story about horror and guns",
        ["other"],
        previous_story="",
        user_feedback="make it about beaches instead",
    )
    assert "make it about beaches instead" in p
    assert "top priority" in p.lower()


def test_feedback_and_previous_story_both_present():
    p = prompts.storyteller_prompt(
        "a story about a cat",
        ["friends"],
        previous_story="Once upon a time there was a cat.",
        user_feedback="make it funnier",
    )
    assert "Once upon a time there was a cat." in p
    assert "make it funnier" in p
    # Previous story shown exactly once.
    assert p.count("Once upon a time there was a cat.") == 1


def test_revision_notes_and_feedback_coexist():
    p = prompts.storyteller_prompt(
        "a story about a cat",
        ["friends"],
        previous_story="draft",
        revision_notes="shorten the long sentence",
        user_feedback="add a dog",
    )
    assert "add a dog" in p
    assert "shorten the long sentence" in p
