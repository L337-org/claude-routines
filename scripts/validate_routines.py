#!/usr/bin/env python3
"""Validate routines/*.yaml against the routine schema.

Run locally with `python scripts/validate_routines.py`. CI runs this on every
push and pull request (see .github/workflows/validate.yaml) and it is a
required status check on `main`.

Checks, per file:
  - required fields are present and of the expected shape
  - exactly one of schedule.cron / schedule.run_once_at is set
  - repositories are https://github.com/... URLs
  - network_allowlist entries (if any) are bare hostnames, not URLs
  - the filename slug matches the slugified `name`
  - no account-specific identifier (routine id, connector uuid, environment
    id, or any bare UUID) appears anywhere in the file - these are
    regenerated on every restore and are excluded by policy; reference the
    owning routine/connector/environment by name instead. A cross-routine
    reference inside `prompt` must use the `{{routine: <name>}}` placeholder
    form, never a raw id.
  - every routine file appears in README.md's summary table under its exact
    `name`, and the table links nothing that does not exist
  - a prompt reads as an instruction rather than a changelog: no dates, no
    issue or pull request references, no narration asserting that a rule is
    true. All three are paid for on every run and none changes what the
    routine does. `note:` is exempt, and is where anything a human genuinely
    needs goes, since it is not sent to the model.
  - a prompt that instructs opening a pull request also carries the
    review-body guidance. Such a routine is subscribed to its PRs' reviews,
    and an automated reviewer's lower-confidence findings appear only in the
    review body, never as a thread, so a routine without that guidance can
    report "no new findings" on a review that holds a real one. Prompts that
    never open a PR are exempt - see `opens_pull_requests`, whose own cases
    live in `scripts/test_validate_routines.py`.

Exits non-zero (and prints every failure, not just the first) if any file
fails any check.
"""
import glob
import re
import sys
from pathlib import Path

import yaml

REQUIRED_STRING_FIELDS = ["name", "model", "environment"]
ALLOWED_TOP_LEVEL_KEYS = {
    "name",
    "enabled",
    "schedule",
    "model",
    "environment",
    "repositories",
    "allowed_tools",
    "mcp_connectors",
    "network_allowlist",
    "autofix_on_pr_create",
    "note",
    "prompt",
}
# Keys that must never appear anywhere in a routine file: raw account-specific
# identifiers. Restoring a routine issues new ones, so storing them is both a
# privacy leak (they're tied to this account) and dead weight for a restore.
BANNED_KEYS = {"id", "trigger_id", "connector_uuid", "environment_id", "api_token_hint"}

UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
# trig_/env_ ids are long random suffixes; require >=10 chars so this doesn't
# flag ordinary code identifiers like `env_flag` that legitimately appear in
# a routine's prompt when it's auditing this org's own source.
RAW_ID_RE = re.compile(r"\b(trig|env)_[A-Za-z0-9]{10,}\b")
PLACEHOLDER_RE = re.compile(r"\{\{routine:\s*[^}]+\}\}")


def slugify(name):
    s = name.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s


# A routine that opens pull requests is subscribed to their reviews, and an automated
# reviewer's lower-confidence findings live only in the review BODY - never in a thread.
# That guidance was recorded in one routine and never propagated, and a run duly reported
# "no new findings" on a review whose body held a real defect, then waited for feedback it
# already had. So it is required mechanically here rather than remembered.
# Both spellings, since a prompt may say either.
_OPEN_PR = r"open(?:ing|s)?\s+(?:a|the|one|its)\s+(?:PR|pull request)"
PR_OPENING_RE = re.compile(_OPEN_PR, re.IGNORECASE)
# A prohibition is only a prohibition when the negation sits immediately before the
# phrase - at most two words in between, to allow "never ever open a PR". Scanning a
# fixed window for the substring "never" instead would let an unrelated one nearby
# ("NEVER push to `main`. Open the PR into `main`") suppress a real match, and a false
# negative here silently exempts a routine from the requirement below, which is the one
# failure this check exists to prevent.
_NEGATORS = r"never|not|no|cannot|can[\u2019']t|don[\u2019']t|does\s+not|must\s+not|avoid|without"
NEGATED_OPEN_PR_RE = re.compile(
    rf"\b(?:{_NEGATORS})\b(?:\s+\w+){{0,2}}\s+{_OPEN_PR}", re.IGNORECASE
)
REVIEW_BODY_MARKERS = ("READ THE REVIEW BODY, NOT ONLY THE THREADS", "get_reviews")

# A prompt is an instruction to a model, not a changelog. Three kinds of text fail that
# test and are rejected here, because every one of them is paid for on every run and none
# of them changes what the routine does:
#   - evidence that a rule is true (incident narration, "not a theory")
#   - a dated confirmation, which is a state claim with a shelf life
#   - a specific issue or pull request, which is closed history the routine could read
# The rationale belongs in the commit message and the decision record; anything a human
# reading the file genuinely needs goes in `note:`, which this check deliberately ignores
# because `note` is not sent to the model.
PROMPT_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# Matches a bare `#16`, a repo-qualified `apt#16`, and an org-qualified `L337-org/apt#16`.
# The last form is the one the prompts actually used and the first cut of this pattern
# missed it, which is the failure that matters: a false negative in a gate is silent.
# `#docker-mcp` and `#l337-org` are Slack channels and must not match, which is why digits
# after the hash are required rather than a word.
PROMPT_ISSUE_RE = re.compile(r"(?<![\w/])[A-Za-z0-9._-]*(?:/[A-Za-z0-9._-]+)*#\d+\b")
PROMPT_NARRATION_RE = re.compile(
    r"not a theory|not hypothetical|has leaked this way before|did exactly that"
    r"|confirmed observed behaviour|predates its being written down",
    re.IGNORECASE,
)


def check_prompt_is_instructional(path, prompt, errors):
    """Reject text in a prompt that records history rather than instructing.

    Three shapes, checked separately and reported separately: a date, an issue or pull
    request reference, and narration asserting that a rule is true. "Narration" is the
    name of one of the three rather than the whole, which is why it is not the summary
    here. See the PROMPT_* patterns above for why each is rejected and where the content
    belongs instead.
    """
    for label, regex, why in (
        ("a date", PROMPT_DATE_RE, "a dated claim goes stale and the routine cannot tell"),
        ("an issue or PR reference", PROMPT_ISSUE_RE, "closed history the routine could read for itself"),
        ("narration", PROMPT_NARRATION_RE, "evidence that the rule is true, which the routine does not act on"),
    ):
        for m in regex.finditer(prompt):
            errors.append(
                f"{path}: prompt contains {label} ({m.group(0)!r}) - {why}. A prompt is an "
                f"instruction, not a changelog: move it to `note:` if a human needs it, or to "
                f"the commit message and the decision record."
            )


def opens_pull_requests(prompt):
    """Whether the prompt instructs opening a pull request.

    Prohibitions ("never open a PR", "don't open a Pull Request") do not count: the
    read-only routines all describe themselves that way, and requiring the review-body
    guidance of them would be noise. Matches are compared by end offset, which is shared
    between the phrase and its negated form.
    """
    negated = {match.end() for match in NEGATED_OPEN_PR_RE.finditer(prompt)}
    return any(match.end() not in negated for match in PR_OPENING_RE.finditer(prompt))


def check_file(path, text, data, errors):
    if not isinstance(data, dict):
        errors.append(f"{path}: top-level content is not a mapping")
        return

    unknown = set(data.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if unknown:
        errors.append(f"{path}: unknown top-level key(s): {sorted(unknown)}")

    banned = set(data.keys()) & BANNED_KEYS
    if banned:
        errors.append(f"{path}: field(s) {sorted(banned)} store an account-specific id - remove, reference by name")

    for field in REQUIRED_STRING_FIELDS:
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{path}: missing or empty required string field '{field}'")

    if "enabled" not in data or not isinstance(data["enabled"], bool):
        errors.append(f"{path}: 'enabled' must be a boolean")

    schedule = data.get("schedule")
    if not isinstance(schedule, dict):
        errors.append(f"{path}: 'schedule' must be a mapping")
    else:
        has_cron = "cron" in schedule
        has_once = "run_once_at" in schedule
        if has_cron == has_once:
            errors.append(f"{path}: schedule must set exactly one of 'cron' / 'run_once_at'")

    repos = data.get("repositories")
    if not isinstance(repos, list) or not repos:
        errors.append(f"{path}: 'repositories' must be a non-empty list")
    else:
        for r in repos:
            if not isinstance(r, str) or not r.startswith("https://github.com/"):
                errors.append(f"{path}: repository '{r}' is not a https://github.com/... URL")

    tools = data.get("allowed_tools")
    if not isinstance(tools, list) or not tools:
        errors.append(f"{path}: 'allowed_tools' must be a non-empty list")

    if "mcp_connectors" in data and not isinstance(data["mcp_connectors"], list):
        errors.append(f"{path}: 'mcp_connectors' must be a list of names")

    if "network_allowlist" in data:
        allowlist = data["network_allowlist"]
        if not isinstance(allowlist, list):
            errors.append(f"{path}: 'network_allowlist' must be a list")
        else:
            for host in allowlist:
                if not isinstance(host, str) or "/" in host or host.startswith("http"):
                    errors.append(f"{path}: network_allowlist entry '{host}' must be a bare hostname, not a URL")

    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append(f"{path}: 'prompt' must be a non-empty string")
        # Deliberately no autofix_on_pr_create error in this branch, though the field may
        # well be wrong. Both autofix rules are decided by reading the prompt, so with no
        # usable prompt we cannot know whether the routine opens pull requests, and an
        # error asserting the field "does nothing" would be a claim we cannot support.
        # The file already fails on the prompt; a second error guessing at the cause of
        # the first is worse than none. Every other check below still runs.
        prompt = ""
    else:
        check_prompt_is_instructional(path, prompt, errors)
    if prompt and opens_pull_requests(prompt):
        absent = [m for m in REVIEW_BODY_MARKERS if m not in prompt]
        if absent:
            errors.append(
                f"{path}: opens pull requests but its prompt omits the review-body guidance "
                f"(missing {', '.join(absent)}) - a suppressed review finding would be missed. "
                f"Copy the block verbatim from routines/mcp-vs-skills-figure-drift.yaml."
            )
        if data.get("autofix_on_pr_create") is not True:
            errors.append(
                f"{path}: opens pull requests, so it must declare "
                f"'autofix_on_pr_create: true' (found "
                f"{data.get('autofix_on_pr_create', '(absent)')!r}). `false` suppresses the "
                f"PR-event subscription, so the routine is never woken for CI failures or "
                f"reviews, and absent cannot be relied on - the web UI writes `false` into it "
                f"on every edit and its default is undocumented."
            )
    elif prompt and "autofix_on_pr_create" in data:
        errors.append(
            f"{path}: declares 'autofix_on_pr_create' but never opens a pull request, so the "
            f"field does nothing. Remove it - the read-only routines carry no such field live, "
            f"and this file should describe what is actually configured."
        )

    expected_slug = slugify(data.get("name", ""))
    actual_slug = path.split("/")[-1].removesuffix(".yaml")
    if expected_slug and actual_slug != expected_slug:
        errors.append(f"{path}: filename should be '{expected_slug}.yaml' for name {data.get('name')!r}")

    # Raw-id scan runs over the whole file text, not just parsed values, so a
    # leaked id inside a comment or an unexpected field still gets caught.
    for m in UUID_RE.finditer(text):
        errors.append(f"{path}: contains a raw UUID ({m.group(0)}) - account-specific, reference by name instead")
    for m in RAW_ID_RE.finditer(text):
        errors.append(f"{path}: contains a raw {m.group(1)}_ id ({m.group(0)}) - reference by name instead")


def check_readme_table(paths, names_seen, errors):
    """Every routine file appears in README.md's summary table, and vice versa.

    Twice in one working week a routine's description outlived the routine: a row still
    advertised a check that had been removed, and another named a scope the routine no longer
    had. The table cannot be checked for accuracy mechanically, but it can be checked for
    completeness, which is what silently goes wrong when a routine is added, removed or renamed.
    """
    readme = Path("README.md")
    if not readme.exists():
        errors.append("README.md is missing, so its routine table cannot be checked")
        return
    text = readme.read_text(encoding="utf-8")
    # A list of pairs, never a dict. Collapsing them by name silently discards a duplicate row,
    # so a wrong row would pass whenever a correct row for the same name appeared later - the
    # table could hold two contradictory entries and validate clean.
    rows = re.findall(r"\| \[([^\]]+)\]\(routines/([a-z0-9-]+\.yaml)\)", text)
    filenames = {p.split("/")[-1] for p in paths}
    seen_names, seen_files = set(), set()
    for name, filename in rows:
        if name in seen_names:
            errors.append(f"README.md's table lists {name!r} on more than one row")
        seen_names.add(name)
        if filename in seen_files:
            errors.append(f"README.md's table links routines/{filename} on more than one row")
        seen_files.add(filename)
        path = f"routines/{filename}"
        if filename not in filenames:
            errors.append(f"README.md's table links {path}, which does not exist")
        elif names_seen.get(name) != path:
            # Deliberately compares which file the name belongs to, not merely whether some
            # routine has it. Checking membership alone would pass a table whose rows had their
            # labels swapped: both names exist, both files exist, and every row is wrong. The
            # live apply step matches by exact name, so a swapped label points the reader at the
            # wrong file for the routine they are about to change.
            owner = names_seen.get(name)
            belongs = f"belongs to {owner}" if owner else "belongs to no routine in this repo"
            errors.append(
                f"README.md's table calls {path} {name!r}, but that name {belongs} - "
                f"matching between this repo and the live account is by exact name"
            )
    for filename in sorted(filenames - seen_files):
        errors.append(f"routines/{filename} is missing from README.md's summary table")


def main():
    paths = sorted(glob.glob("routines/*.yaml"))
    if not paths:
        print("no routines/*.yaml files found", file=sys.stderr)
        return 1

    errors = []
    names_seen = {}
    for path in paths:
        with open(path) as f:
            text = f.read()
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            errors.append(f"{path}: invalid YAML: {e}")
            continue
        check_file(path, text, data, errors)
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            name = data["name"]
            if name in names_seen:
                errors.append(f"{path}: duplicate routine name also used by {names_seen[name]}")
            names_seen[name] = path

    # Cross-file check: every {{routine: X}} placeholder must name a routine
    # that actually exists somewhere in this repo.
    for path in paths:
        with open(path) as f:
            text = f.read()
        for m in PLACEHOLDER_RE.finditer(text):
            ref = m.group(0)
            referenced_name = ref[len("{{routine:"):-2].strip()
            if referenced_name.lower() in ("<name>", "name"):
                continue  # generic doc token, e.g. explaining the placeholder syntax itself
            if referenced_name not in names_seen:
                errors.append(f"{path}: {ref} does not match any routine name in this repo")

    check_readme_table(paths, names_seen, errors)

    if errors:
        print(f"{len(errors)} validation error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(paths)} routine file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
