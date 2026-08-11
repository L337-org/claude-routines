# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **MIRROR RULE (do not skip): `CLAUDE.md` and `.github/copilot-instructions.md` are mirrors.**
> `.github/copilot-instructions.md` drives GitHub Copilot's review of *every* PR, so it must stay
> current. **Any change to the schema, the reconcile routine's behaviour, or the redaction rules
> below MUST update BOTH files in the same change.**

## Project

`claude-routines` holds authoritative, version-controlled copies of every Claude cloud routine
("scheduled cloud agent") running for L337-org — its prompt, schedule, enabled state, required
tools/connectors, and any cloud-environment requirements (e.g. a network allowlist entry). It is
**not** a product repo; it ships no code, no package, no release. Its only output is the live
routine configuration it drives via the reconcile routine described below.

**This repo is authoritative, always.** Live routine state is a projection of the files here, never
the reverse. Nothing here reads live state back into a file — that direction only exists as a
one-off seeding step when a routine is first added.

## Layout

- `routines/*.yaml` — one file per routine, named from a slugified `name`. Field reference:
  `schema/routine.md`.
- `scripts/validate_routines.py` — schema and redaction checks, run in CI
  (`.github/workflows/validate.yaml`) on every push and PR, required on `main`.
- `routines/reconcile-routines-with-claude-routines.yaml` — the routine that applies this repo to
  the live account. It is tracked here like any other routine (see "Reconcile routine" below).

## Redaction rules (enforced by `scripts/validate_routines.py`, not just convention)

1. **No secrets or private data in any routine file.** A prompt is operational instructions, never
   a place for a credential, token, or anything an attacker could use.
2. **No routine's own id/URL.** `https://claude.ai/code/routines/{id}` is never stored — a restored
   routine gets a new id, so the URL is both meaningless for that purpose and not something to
   publish. Routines are identified and matched **by exact `name` string**, never by id.
3. **No other account-specific id, for the identical reason.** `connector_uuid` and
   `environment_id` are reissued on restore exactly like a routine's own id. They're referenced by
   **name** instead (`environment: Default`, `mcp_connectors: [Slack]`); the reconcile routine
   resolves the current live id for that name each time it runs (see `schema/routine.md` for
   exactly how, including the one-environment bootstrap case and its documented failure mode).
4. **A cross-routine reference inside a `prompt` uses `{{routine: <exact name>}}`**, never a
   hardcoded `trigger_id` — see `docker-py-sdk-audit-phase-1-detect.yaml` for the real example this
   rule exists because of (its prompt used to hardcode a sibling routine's id).
5. **Slack channel names/ids are the one exception** — kept as-is in prompt text. A channel isn't
   reissued on restore, and which channel a routine posts to is part of its actual behaviour, not an
   artefact of this account.

The validator scans raw file text (not just parsed fields) for bare UUIDs and `trig_…`/`env_…`
patterns, so a leaked id anywhere — including inside the prompt — fails CI.

## Reconcile routine

`Reconcile routines with claude-routines` fires on every push to `main` (a GitHub push webhook via
`RemoteTrigger create_webhook_trigger`, wired once by hand — never re-created by the routine itself)
plus a daily fallback cron. Each run it:

1. Reads every `routines/*.yaml` file.
2. Lists live routines via `RemoteTrigger`, builds name→id / name→connector / id→environment
   lookups from what's already live.
3. Resolves `{{routine: …}}` placeholders using those lookups.
4. Creates missing routines, updates drifted ones, leaves matching ones alone.
5. **Disables** (never deletes — the API can't) any live routine whose name has no file here, and
   reports it. A routine created by hand in the UI without a matching file gets disabled on the next
   run — add its file in the same change you create it, or expect it to be turned off.
6. Posts one Slack summary (`#l337-org`) naming everything it changed and any resolution failure it
   hit. A clean run — repo and live state already agreed — posts nothing, matching every other
   routine's silent-on-clean convention.

Its own file, `routines/reconcile-routines-with-claude-routines.yaml`, is reconciled the same way as
everything else — it is not special-cased in the repo, only in the one thing it must never do to
itself (re-wire its own webhook).

## Checklist when adding or changing a routine

1. Add or edit `routines/<slug>.yaml` per `schema/routine.md`. Never paste in a raw id — name it.
2. If it references a sibling routine, use `{{routine: <exact name>}}`.
3. Update the summary table in `README.md`.
4. `.github/copilot-instructions.md` — mirror any structural/convention change here too (see the
   MIRROR RULE above).
5. Open a PR; CI runs `scripts/validate_routines.py`. Merge applies it via the reconcile routine —
   Done never waits on a manual apply step.

## Git and pull requests

Same rules as the rest of L337-org: no direct commits to `main`, PR + ≥1 approval with code-owner
review, squash-only, signed commits, resolved threads, Copilot review, required status checks green
(`Validate routines`). `CODEOWNERS`: `@GavinLucas @claudeleet`.

## Visibility

Private for now — this repo carries the full operating instructions of every org routine, which
isn't necessary to publish for the "recreate on demand" goal even though none of it is secret.
Revisit once the redaction rules above have been in place for a while.
