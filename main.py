"""Bedtime story generator — CLI entry point.

Pipeline and design: see DESIGN.md. This file handles I/O: it runs the
evaluator-optimizer pipeline, applies the compulsory-safety gate, and offers the
reader a feedback turn to request changes.

Before submitting the assignment, describe here in a few sentences what you
would have built next if you spent 2 more hours on this project:

  Next: (1) replace the JSON-in-prompt judge contract with structured/function
  calling for reliability; (2) add a small bad-word + PII deterministic filter to
  complement the LLM safety judges; (3) cache categorization and add a few-shot
  example bank per category to lift story quality; (4) add a lightweight eval
  harness (a fixed set of prompts scored by the same judges) to measure
  regressions when prompts change.
"""
import argparse

import pipeline

SAFE_FALLBACK = (
    "I'm sorry, I couldn't make a story that was just right and safe for you. "
    "Want to try a different idea?"
)


def present(result: pipeline.StoryResult, print_unsafe: bool) -> None:
    """Apply the input guard + compulsory-safety gate, then print the outcome."""
    # Hard-blocked at the front door: show only the friendly redirect.
    if result.blocked:
        print("\n" + result.block_message + "\n")
        return

    if result.compulsory_ok:
        print("\n" + result.story + "\n")
        return

    # A compulsory item failed after the revision budget was exhausted.
    if print_unsafe:
        print("\n" + "=" * 60)
        print("WARNING: this story did not pass all compulsory safety checks.")
        failed = [
            k for k in result.assessment.get("compulsory", {})
            if str(result.assessment["compulsory"].get(k)).lower() != "pass"
        ]
        if failed:
            print("Failed items: " + ", ".join(failed))
        print("=" * 60 + "\n")
        print(result.story + "\n")
    else:
        print("\n" + SAFE_FALLBACK + "\n")


def feedback_loop(result: pipeline.StoryResult, user_input: str, print_unsafe: bool) -> None:
    """Let the reader request changes; re-enter the pipeline with their note."""
    while True:
        try:
            answer = input("Would you like any changes? (e.g. 'make it funnier', or 'no'): ").strip()
        except EOFError:
            return
        if not answer or answer.lower() in {"no", "n", "nope", "nah","quit", "exit"}:
            print("Sweet dreams!")
            return

        result = pipeline.run(
            user_input,
            categories=result.categories,
            previous_story=result.story,
            user_feedback=answer,
        )
        present(result, print_unsafe)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tell a bedtime story for ages 5-10.")
    parser.add_argument(
        "--print-unsafe",
        action="store_true",
        help="Eval/debug only: print the story with a WARNING even if it fails a "
             "compulsory safety check (default: withhold and show a safe fallback).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the pipeline trace (router/judge/reviser logs).",
    )
    args = parser.parse_args()

    user_input = input("What kind of story do you want to hear? ")
    result = pipeline.run(user_input, verbose=not args.quiet)
    present(result, args.print_unsafe)
    feedback_loop(result, user_input, args.print_unsafe)


if __name__ == "__main__":
    main()
