# GitHub Copilot Instructions

This file provides guidance to GitHub Copilot when working with code in this repository. It mirrors
`CLAUDE.md` — see the MIRROR RULE at the top of that file. Any change to the schema, the reconcile
routine's behaviour, or the redaction rules below must update both files together.

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
- `routines/reconcile-routines-with-claude-routines.yaml` — the routine that applies this repo to
  the live account, tracked here like any other routine.

## Redaction rules (enforced by `scripts/validate_routines.py`, not just convention)

1. **No secrets or private data in any routine file.**
2. **No routine's own id/URL.** A restored routine gets a new id, so the
   `https://claude.ai/code/routines/{id}` URL is never stored. Routines are matched **by exact
   `name` string**, never by id.
3. **No other account-specific id, for the identical reason** — `connector_uuid` and
   `environment_id` are reissued on restore too. Reference them by **name**
   (`environment: Default`, `mcp_connectors: [Slack]`); the reconcile routine resolves the current
   live id for that name at apply time.
4. **A cross-routine reference inside a `prompt` uses `{{routine: <exact name>}}`**, never a
   hardcoded `trigger_id`.
5. **Slack channel names/ids are the one exception** — kept as-is; a channel isn't reissued on
   restore and is part of the routine's actual behaviour.

The validator scans raw file text for bare UUIDs and `trig_…`/`env_…` patterns, so a leaked id
anywhere fails CI.

## Reconcile routine

`Reconcile routines with claude-routines` fires on push to this repo (GitHub push webhook, wired
once by hand; not scoped to `main` — the API rejected every branch-filter key tried — but harmless,
since the git source always clones `main` regardless of which branch triggered it) plus a daily
fallback cron: reads every routine file, lists live routines, resolves `{{routine: …}}`
placeholders, creates/updates to match the repo, and **disables** (never deletes) any live routine
with no matching file — reporting all of it to Slack, silently on a clean run.

## Review checklist for a PR touching `routines/*.yaml`

- No raw `trigger_id`, `connector_uuid`, `environment_id`, or bare UUID pasted into any field —
  `scripts/validate_routines.py` should already have failed CI if so, but flag it if seen.
- A cross-routine reference uses `{{routine: <exact name>}}`, and that name exists somewhere in this
  repo.
- `README.md`'s summary table reflects the change.
- Renaming a routine's `name` is delete+create, not a rename, on the live side — the old name gets
  disabled as an orphan on the next reconcile run, which is expected but worth calling out in the
  PR description.

## Git and pull requests

Same rules as the rest of L337-org: no direct commits to `main`, PR + ≥1 approval with code-owner
review, squash-only, signed commits, resolved threads, Copilot review, required status checks green
(`Validate routines`). `CODEOWNERS`: `@GavinLucas @claudeleet`.

## Visibility

Private for now, revisit once the redaction rules above have been in place for a while.
