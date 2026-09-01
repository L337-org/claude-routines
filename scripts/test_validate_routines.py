#!/usr/bin/env python3
"""Tests for `validate_routines.py`'s non-obvious logic.

Plain asserts, no test framework: this repo has one CI job and no test dependency, and
adding one for a single module would cost more than it returns. Run with
`python scripts/test_validate_routines.py`; CI runs it alongside the validator itself.

Two things are covered. `opens_pull_requests` decides by judgement rather than by shape,
and it gates both of the PR-opening requirements, so a false negative silently exempts a
routine from them - a first attempt at it did exactly that, scanning a fixed window for the
substring "never" and so letting an unrelated "NEVER push to `main`" nearby suppress a real
match. The `autofix_on_pr_create` rule is covered because a routine that loses that field
stops being woken for its own PRs, silently, and the field is invisible in the web UI.
`check_prompt_is_instructional` is covered because it is the only check that rejects text
on judgement rather than shape, so its false positives are what would get it switched off:
a Slack channel is not an issue reference, and a date placeholder in a branch name is not a
date.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_routines import (  # noqa: E402
    check_file,
    check_prompt_is_instructional,
    opens_pull_requests,
)

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

    for prompt, autofix, expected, description in AUTOFIX_CASES:
        actual = len(_autofix_errors(prompt, autofix))
        if actual != expected:
            failures.append(
                f"  expected {expected} autofix error(s), got {actual}: {description}\n"
                f"    autofix={autofix!r} prompt={prompt!r}"
            )

    total = len(CASES) + len(AUTOFIX_CASES) + len(INSTRUCTIONAL_CASES)
    for prompt, expected, why in INSTRUCTIONAL_CASES:
        got = len(_instructional_errors(prompt))
        if got != expected:
            failures.append(
                f"check_prompt_is_instructional({prompt!r}) gave {got} error(s), "
                f"expected {expected} - {why}"
            )

    if failures:
        print(f"{len(failures)} of {total} case(s) failed:", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(
        f"OK: {len(CASES)} opens_pull_requests, {len(AUTOFIX_CASES)} autofix and "
        f"{len(INSTRUCTIONAL_CASES)} instructional-prompt case(s) passed"
    )
    return 0



# A prompt fragment that trips `opens_pull_requests`, and one that does not.
OPENS = "If it is something you can safely fix, open a PR into `main`."
READ_ONLY = "You are READ-ONLY: never open a PR or an issue. Report to Slack only."


def _autofix_errors(prompt, autofix):
    """The autofix-specific errors check_file() raises for a minimal routine."""
    data = {"prompt": prompt}
    if autofix is not None:
        data["autofix_on_pr_create"] = autofix
    errors = []
    check_file("routines/example.yaml", "", data, errors)
    return [e for e in errors if "autofix_on_pr_create" in e]


AUTOFIX_CASES = [
    (OPENS, True, 0, "a PR-opening routine declaring true is correct"),
    (OPENS, False, 1, "false suppresses the PR-event subscription, so it must be rejected"),
    (OPENS, None, 1, "absent cannot be relied on: the web UI writes false on every edit"),
    (READ_ONLY, None, 0, "a read-only routine correctly carries no such field"),
    (READ_ONLY, True, 1, "the field does nothing on a routine that opens no PR"),
    (READ_ONLY, False, 1, "likewise false: the file should describe what is configured"),
]

# (prompt fragment, expected error count, what the case is for)
INSTRUCTIONAL_CASES = [
    ("Post to Slack #docker-mcp (channel id C0BAP2FTQ6N) when a marker disagrees.", 0,
     "a Slack channel is not an issue reference: the digits rule is what separates them"),
    ("Branch `sdk-audit/<YYYY-MM-DD>`, which matches no ruleset.", 0,
     "a date placeholder in a branch name is a template, not a dated claim"),
    ("File a `ci-failure` issue ONLY if it has happened more than once.", 0,
     "an instruction that happens to describe recurrence is not narration"),
    ("Read the workflow's `concurrency` block before deciding.", 0,
     "the ordinary instructional case must stay clean"),
    ("As of 2026-08-10 a human confirmed the only rulesets are per-repo.", 1,
     "a dated confirmation goes stale and the routine cannot tell"),
    ("Issues filed by earlier runs carry them: apt#1, #2 and send-to-influx#107.", 3,
     "each issue reference is closed history the routine could read for itself"),
    ("That is confirmed observed behaviour on L337-org/apt, not a theory.", 2,
     "evidence that a rule is true, which the routine does not act on"),
    ("It has leaked this way before, so none of these checks is optional.", 1,
     "same shape, and the instruction survives without it"),
]


def _instructional_errors(prompt):
    errors = []
    check_prompt_is_instructional("routines/example.yaml", prompt, errors)
    return errors


if __name__ == "__main__":
    sys.exit(main())
