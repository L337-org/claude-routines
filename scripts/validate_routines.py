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

Exits non-zero (and prints every failure, not just the first) if any file
fails any check.
"""
import glob
import re
import sys

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
    elif opens_pull_requests(prompt):
        absent = [m for m in REVIEW_BODY_MARKERS if m not in prompt]
        if absent:
            errors.append(
                f"{path}: opens pull requests but its prompt omits the review-body guidance "
                f"(missing {', '.join(absent)}) - a suppressed review finding would be missed. "
                f"Copy the block verbatim from routines/mcp-vs-skills-figure-drift.yaml."
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

    if errors:
        print(f"{len(errors)} validation error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(paths)} routine file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
