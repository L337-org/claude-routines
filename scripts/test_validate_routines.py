#!/usr/bin/env python3
"""Tests for `validate_routines.py`'s non-obvious logic.

Plain asserts, no test framework: this repo has one CI job and no test dependency, and
adding one for a single module would cost more than it returns. Run with
`python scripts/test_validate_routines.py`; CI runs it alongside the validator itself.

Only `opens_pull_requests` is covered, because it is the only part that decides anything
by judgement rather than by shape. It gates the review-body requirement, so a false
negative silently exempts a routine from that check - and a first attempt at it did
exactly that, scanning a fixed window for the substring "never" and so letting an
unrelated "NEVER push to `main`" nearby suppress a real match.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_routines import opens_pull_requests  # noqa: E402

# (prompt fragment, opens a PR?, what the case is for)
CASES = [
    ("NEVER push to `main`. Open the PR into `main`.", True,
     "an unrelated negation nearby must not suppress a real match"),
    ("NEVER merge anything, including your own PR - a human merges. Open the PR into `main`.", True,
     "nor one further back in the same bullet"),
    ("If it's something you can safely fix, open a PR:", True, "plain affirmative"),
    ("Open a pull request into `main`.", True, "the long spelling counts too"),
    ("It opens a PR when the fix is safe.", True, "third person"),
    ("You are READ-ONLY: never open a PR or an issue.", False, "explicit prohibition"),
    ("This routine is read-only: never commit, never open a PR or issue.", False,
     "prohibition after an unrelated clause"),
    ("Do not open a PR for this.", False, "'do not'"),
    ("Don't open a PR.", False, "'don't'"),
    ("Don’t open a PR.", False, "'don't' with a typographic apostrophe"),
    ("Never ever open a PR.", False, "negation with an intervening word"),
    ("Report to Slack only; you cannot open a PR.", False, "'cannot'"),
    ("Never open a pull request.", False, "prohibition, long spelling"),
]


def main():
    failures = []
    for prompt, expected, description in CASES:
        actual = opens_pull_requests(prompt)
        if actual != expected:
            failures.append(f"  expected {expected}, got {actual}: {description}\n    {prompt!r}")

    if failures:
        print(f"{len(failures)} of {len(CASES)} opens_pull_requests case(s) failed:", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f"OK: {len(CASES)} opens_pull_requests case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
