# GitHub Copilot Instructions

This file provides guidance to GitHub Copilot when working with code in this repository. It mirrors
`CLAUDE.md` — see the MIRROR RULE at the top of that file. Any change to the schema or the redaction
rules below must update both files together.

## Project

`claude-routines` holds authoritative, version-controlled copies of every Claude cloud routine
("scheduled cloud agent") running for L337-org — its prompt, schedule, enabled state, required
tools/connectors, and any cloud-environment requirements (e.g. a network allowlist entry). It ships
no code, no package, no release; its only output is the live routine configuration it drives.

**This repo is authoritative, always.** Live routine state is a projection of the files here, never
the reverse.

## Layout

- `routines/*.yaml` — one file per routine, named from a slugified `name`. Field reference:
  `schema/routine.md`.
- `scripts/validate_routines.py` — schema and redaction checks, run in CI
  (`.github/workflows/validate.yaml`) on every push and PR, required on `main`.

## Redaction rules (enforced by `scripts/validate_routines.py`, not just convention)

1. **No secrets or private data in any routine file.**
2. **No routine's own id/URL.** A restored routine gets a new id, so the
   `https://claude.ai/code/routines/{id}` URL is never stored. Routines are matched **by exact
   `name` string**, never by id.
3. **No other account-specific id, for the identical reason** — `connector_uuid` and
   `environment_id` are reissued on restore too. Reference them by **name**
   (`environment: Default`, `mcp_connectors: [Slack]`); resolved to the current live id by hand at
   apply time.
4. **A cross-routine reference inside a `prompt` uses `{{routine: <exact name>}}`**, never a
   hardcoded `trigger_id`.
5. **Slack channel names/ids are the one exception** — kept as-is; a channel isn't reissued on
   restore and is part of the routine's actual behaviour.

The validator scans raw file text for bare UUIDs and `trig_…`/`env_…` patterns, so a leaked id
anywhere fails CI.

## Applying changes to the live account

There is no automatic apply step, permanently — a settled platform limitation, not a gap waiting on
a fix. A cloud routine cannot call `RemoteTrigger`: a routine built for exactly this purpose (read
this repo, reconcile the live account) searched exhaustively for it at runtime and found nothing,
despite `RemoteTrigger` being accepted in its `allowed_tools` at creation time. Separately, there is
no API for creating, updating, or listing routines at all — routine management only works from a
session with a claude.ai subscription login (web UI, Desktop app, or CLI); a stored API credential
for an unattended process was ruled out because no such credential exists for this API, not because
of a risk tradeoff. **Apply a merged change by hand** from an interactive session with
`RemoteTrigger` (or the `schedule` skill): resolve `environment`/`mcp_connectors` names and any
`{{routine: …}}` placeholders to live ids, then create/update matching by exact `name`. Never delete
a live routine whose file was removed here — the API can't anyway — disable it instead.

## Review checklist for a PR touching `routines/*.yaml`

- No raw `trigger_id`, `connector_uuid`, `environment_id`, or bare UUID pasted into any field —
  `scripts/validate_routines.py` should already have failed CI if so, but flag it if seen.
- A cross-routine reference uses `{{routine: <exact name>}}`, and that name exists somewhere in this
  repo.
- `README.md`'s summary table reflects the change.
- Renaming a routine's `name` is delete+create, not a rename, on the live side — whoever next
  applies this repo by hand should disable the old name as an orphan, which is expected but worth
  calling out in the PR description.

## Git and pull requests

Same rules as the rest of L337-org: no direct commits to `main`, PR + ≥1 approval with code-owner
review, squash-only, signed commits, resolved threads, Copilot review, required status checks green
(`Validate routines`). `CODEOWNERS`: `@GavinLucas @claudeleet`.

A `main` ruleset enforces all of this, matching `docker-mcp`'s own `main` ruleset — deletion/
force-push/signature protection, 1 approval with required code-owner review, dismiss stale reviews,
resolved threads required, squash-only, Copilot review on every push, `Validate routines` as the
required status check. It's checked in for reference at
[`.github/rulesets/main.json`](.github/rulesets/main.json) — keep it in sync by hand if the live
ruleset changes.

## Visibility

Public, matching every other L337-org repo. Reviewed for content before publishing: no secrets, no
issue keys or wiki links, no raw account-specific ids (enforced by `scripts/validate_routines.py` in
CI). The audit/review heuristics a routine's prompt documents are public in the same sense this
org's CI configuration already is.

## Review canaries (temporary - spike branch, never merged)

The rules in this section exist only to establish how instruction context reaches the Copilot
reviewer. They are not project policy, and this branch is not intended for merge.

- `scripts/spike_probe.py` must never call `time.sleep`. If a change adds one, flag it and include
  the exact string `CANARY-BASE-7Q2F` in your comment.

Read `docs/ai/instructions.md` before reviewing anything under `scripts/`. It carries further rules
that apply to this review and are deliberately not repeated here.
