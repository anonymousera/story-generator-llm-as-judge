"""Bedtime story generator — CLI entry point.

This file handles I/O: it runs the
evaluator-optimizer pipeline, applies the compulsory-safety gate, and offers the
reader a feedback turn to request changes.

What I'd have build next with 2 more hours: 

1. Restructuring JSON-outputs to be more readable and easier to understand for analysis and debugging.
2. Add a deterministic bad-word / PII filter to complement the LLM safety judges.
3. Run few more experiments to manually evaluate performace of the system, primarily to understand if it is too complex, or could it have performed better or similar without so many constraints. 
Right now I'm implementing based on industry best practices, my own innovation to the design of the system and its prompts, and my own context-specific knowledge.  
   1. measure whether all four metrics and the multi-judge panel actually beat a simpler configuration
   2. tune the four metrics
   3. tune the quality threshold.
4. Would have also preferred to use different models for judges, guard, and storyteller, but the assignment constraint was to use the same model (gpt-3.5-turbo) for all.
"""
import argparse

import pipeline
import reporting

SAFE_FALLBACK = (
    "I'm sorry, I couldn't make a story that was just right and safe for you. "
    "Want to try a different idea?"
)

MAX_FEEDBACK = 5  # how many times the user may request changes


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


def feedback_loop(result: pipeline.StoryResult, user_input: str, print_unsafe: bool,
                  turns: list, path: str, verbose: bool) -> None:
    """Let the reader request changes (up to MAX_FEEDBACK times). Each round is
    appended to the same conversation file rather than creating a new one."""
    rounds = 0
    base_request = user_input
    while rounds < MAX_FEEDBACK:
        remaining = MAX_FEEDBACK - rounds
        try:
            answer = input(
                f"Would you like any changes? ({remaining} left — e.g. 'make it funnier', or 'no'): "
            ).strip()
        except EOFError:
            return
        if not answer or answer.lower() in {"no", "n", "nope", "nah", "quit", "exit"}:
            print("Sweet dreams!")
            return

        rounds += 1
        if result.blocked or not result.story:
            # Nothing to refine (the prior turn was blocked/withheld) -> treat the
            # input as a brand-new request rather than feedback on a missing story.
            base_request = answer
            result = pipeline.run(base_request, verbose=verbose)
        else:
            result = pipeline.run(
                base_request,
                categories=result.categories,
                previous_story=result.story,
                user_feedback=answer,
                verbose=verbose,
            )
        present(result, print_unsafe)
        turns.append(reporting.make_turn(result, "feedback", feedback=answer))
        reporting.save_conversation(user_input, turns, path)
        print(f"[trace] conversation updated -> {path}")

    print(f"That's the limit of {MAX_FEEDBACK} changes for one story. Sweet dreams!")


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
        help="Suppress the live pipeline logs (router/judge/reviser). The JSON "
             "trace is always written regardless.",
    )
    args = parser.parse_args()

    verbose = not args.quiet
    user_input = input("What kind of story do you want to hear? ")
    result = pipeline.run(user_input, verbose=verbose)
    present(result, args.print_unsafe)          # story printed to the terminal

    # One conversation = one JSON file, updated in place across feedback rounds.
    path = reporting.new_conversation_path()
    turns = [reporting.make_turn(result, "initial")]
    reporting.save_conversation(user_input, turns, path)
    print(f"[trace] full run details saved to {path}")

    feedback_loop(result, user_input, args.print_unsafe, turns, path, verbose)

if __name__ == "__main__":
    main()
