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
    check_readme_table,
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

    total = len(CASES) + len(AUTOFIX_CASES) + len(INSTRUCTIONAL_CASES) + len(README_CASES)
    for prompt, expected, why in INSTRUCTIONAL_CASES:
        got = len(_instructional_errors(prompt))
        if got != expected:
            failures.append(
                f"check_prompt_is_instructional({prompt!r}) gave {got} error(s), "
                f"expected {expected} - {why}"
            )

    for case in README_CASES:
        paths, names, text, expected, why = case[:5]
        exists = case[5] if len(case) > 5 else True
        got = len(_readme_errors(paths, names, text, exists))
        if got != expected:
            failures.append(
                f"check_readme_table({paths}, {text!r}) gave {got} error(s), "
                f"expected {expected} - {why}"
            )

    if failures:
        print(f"{len(failures)} of {total} case(s) failed:", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(
        f"OK: {len(CASES)} opens_pull_requests, {len(AUTOFIX_CASES)} autofix, "
        f"{len(INSTRUCTIONAL_CASES)} instructional-prompt and {len(README_CASES)} "
        f"readme-table case(s) passed"
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
    ("Two runs reached opposite conclusions on L337-org/apt#16 for this reason.", 1,
     "the org-qualified form is what the prompts used, and the first pattern missed it"),
    ("See https://github.com/L337-org/apt/issues/16 for the detail.", 0,
     "a bare URL carries no hash-digits, so it is not caught by this rule"),
    ("That is confirmed observed behaviour on L337-org/apt, not a theory.", 2,
     "evidence that a rule is true, which the routine does not act on"),
    ("It has leaked this way before, so none of these checks is optional.", 1,
     "same shape, and the instruction survives without it"),
    ("At the time of writing the narrower grep finds 3 sites in 2 modules.", 1,
     "a snapshot the routine can re-derive, and which its own successful run invalidates"),
    ("The tap is at present dispatch-only, so a release trigger is the finding.", 1,
     "same shape in a phrasing that does not name writing"),
    ("As of now the Projects table lists customer-facing repos only.", 1,
     "and again, since one phrasing being caught proves nothing about the others"),
    ("Poll every 2 minutes for about 20 minutes, up to 3 fix cycles, and stop at 1%.", 0,
     "thresholds are instructions: a bare count must never be read as a snapshot"),
]


def _instructional_errors(prompt):
    errors = []
    check_prompt_is_instructional("routines/example.yaml", prompt, errors)
    return errors


# (files, names, README text, expected error count, what the case is for)
# `names_seen` is a dict of name -> path, exactly as check_file() builds it. Passing a set here
# instead was what let the swapped-label case below go unnoticed: membership was all the test
# could express, so membership was all the check did.
_A = "routines/a.yaml"
_B = "routines/b.yaml"
_NAMES = {"A": _A, "B": _B}

README_CASES = [
    ([_A], {"A": _A}, "| [A](routines/a.yaml) | x |", 0,
     "a file listed under its exact name is the clean case"),
    ([_A], {"A": _A}, "nothing here", 1,
     "a routine missing from the table is the failure a rename or an addition causes"),
    ([], {}, "| [Ghost](routines/ghost.yaml) | x |", 1,
     "a row linking a file that does not exist is the failure a removal causes"),
    ([_A], {"A": _A}, "| [Different](routines/a.yaml) | x |", 1,
     "matching is by exact name, so a row naming it after nothing is wrong"),
    ([_A, _B], _NAMES,
     "| [B](routines/a.yaml) | x |\n| [A](routines/b.yaml) | x |", 2,
     "two rows with their labels swapped: every name and file exists, and every row is wrong"),
    ([_A, _B], _NAMES,
     "| [A](routines/a.yaml) | x |\n| [B](routines/b.yaml) | x |", 0,
     "the same two rows, correctly paired, must stay clean"),
    ([_A, _B], _NAMES,
     "| [B](routines/a.yaml) | x |\n| [B](routines/b.yaml) | x |", 2,
     "a wrong row must not be excused by a later correct row for the same name"),
    ([_A, _B], _NAMES,
     "| [A](routines/a.yaml) | x |\n| [B](routines/a.yaml) | x |\n| [B](routines/b.yaml) | x |", 3,
     "nor by a later correct row for the same file"),
    ([_A], {"A": _A}, None, 1,
     "a missing README.md is reported rather than passing silently",
     False),
]


def _readme_errors(paths, names, text, exists=True):
    """Run check_readme_table against a stubbed README, including the absent case.

    `text=None, exists=False` exercises the branch that fires when README.md is missing
    altogether - a failure path with no other way to reach it, since the real file is
    always there.
    """
    import validate_routines as v

    real = v.Path

    class _Stub:
        def __init__(self, *_):
            pass

        def exists(self):
            return exists

        def read_text(self, **_):
            return text

    v.Path = _Stub
    try:
        errors = []
        check_readme_table(paths, names, errors)
        return errors
    finally:
        v.Path = real


if __name__ == "__main__":
    sys.exit(main())
