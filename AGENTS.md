# AGENTS.md

The shared instruction file for this repository. Every assistant reads this one; `CLAUDE.md` and
`.github/copilot-instructions.md` are pointers to it.

## Project

`claude-routines` holds authoritative, version-controlled copies of every Claude cloud routine
("scheduled cloud agent") running for L337-org — its prompt, schedule, enabled state, required
tools/connectors, and any cloud-environment requirements (e.g. a network allowlist entry). It is
**not** a product repo; it ships no code, no package, no release. Its only output is the live
routine configuration a human applies by hand (see "Applying changes to the live account" below).

Nothing here reads live state back into a file. That direction exists only as a one-off seeding step
when a routine is first added.

## Layout

- `routines/*.yaml` — one file per routine, named from a slugified `name`. Field reference:
  `schema/routine.md`.
- `scripts/validate_routines.py` — schema and redaction checks, run in CI
  (`.github/workflows/validate.yaml`) on every push and PR, required on `main`.

## Redaction rules (enforced by `scripts/validate_routines.py`, not just convention)

The rules on redacting account-specific identifiers come from the shared policy and are not
restated here. One exception is local:

- **Slack channel names and ids are the one exception** — kept as-is in prompt text. A channel isn't
   reissued on restore, and which channel a routine posts to is part of its actual behaviour, not an
   artefact of this account.

The validator scans raw file text (not just parsed fields) for bare UUIDs and `trig_…`/`env_…`
patterns, so a leaked id anywhere — including inside the prompt — fails CI.

## Checklist when adding or changing a routine

1. Add or edit `routines/<slug>.yaml` per `schema/routine.md`. Never paste in a raw id — name it.
2. If it references a sibling routine, use `{{routine: <exact name>}}`.
3. Update the summary table in `README.md`.
4. Open a PR; CI runs `scripts/validate_routines.py`. Merge, then apply it to the live account by
   hand (see "Applying changes to the live account" above).

## Review checklist for a PR touching `routines/*.yaml`

- No raw `trigger_id`, `connector_uuid`, `environment_id`, or bare UUID pasted into any field —
  `scripts/validate_routines.py` should already have failed CI if so, but flag it if seen.
- A cross-routine reference uses `{{routine: <exact name>}}`, and that name exists somewhere in this
  repo.
- `README.md`'s summary table reflects the change.
- Renaming a routine's `name` is delete+create, not a rename, on the live side — whoever next
  applies this repo by hand should disable the old name as an orphan, which is expected but worth
  calling out in the PR description.

<!-- BEGIN GENERATED -->
## Read these when they apply

- Read `.agents/policy/review-context.md` always - these apply to every activity.
- Read `.agents/policy/testing.md` when writing or running tests, or adding behaviour that needs them.
- Read `.agents/policy/architecture.md` when changing module structure, public surface, docstrings, generated files, deprecation, or log levels.

<!-- END GENERATED -->
