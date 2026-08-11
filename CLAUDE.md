# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **MIRROR RULE (do not skip): `CLAUDE.md` and `.github/copilot-instructions.md` are mirrors.**
> `.github/copilot-instructions.md` drives GitHub Copilot's review of *every* PR, so it must stay
> current. **Any change to the schema or the redaction rules below MUST update BOTH files in the
> same change.**

## Project

`claude-routines` holds authoritative, version-controlled copies of every Claude cloud routine
("scheduled cloud agent") running for L337-org — its prompt, schedule, enabled state, required
tools/connectors, and any cloud-environment requirements (e.g. a network allowlist entry). It is
**not** a product repo; it ships no code, no package, no release. Its only output is the live
routine configuration a human applies by hand (see "Applying changes to the live account" below).

**This repo is authoritative, always.** Live routine state is a projection of the files here, never
the reverse. Nothing here reads live state back into a file — that direction only exists as a
one-off seeding step when a routine is first added.

## Layout

- `routines/*.yaml` — one file per routine, named from a slugified `name`. Field reference:
  `schema/routine.md`.
- `scripts/validate_routines.py` — schema and redaction checks, run in CI
  (`.github/workflows/validate.yaml`) on every push and PR, required on `main`.

## Redaction rules (enforced by `scripts/validate_routines.py`, not just convention)

1. **No secrets or private data in any routine file.** A prompt is operational instructions, never
   a place for a credential, token, or anything an attacker could use.
2. **No routine's own id/URL.** `https://claude.ai/code/routines/{id}` is never stored — a restored
   routine gets a new id, so the URL is both meaningless for that purpose and not something to
   publish. Routines are identified and matched **by exact `name` string**, never by id.
3. **No other account-specific id, for the identical reason.** `connector_uuid` and
   `environment_id` are reissued on restore exactly like a routine's own id. They're referenced by
   **name** instead (`environment: Default`, `mcp_connectors: [Slack]`), resolved to the current
   live id by hand at apply time (see `schema/routine.md`).
4. **A cross-routine reference inside a `prompt` uses `{{routine: <exact name>}}`**, never a
   hardcoded `trigger_id` — see `docker-py-sdk-audit-phase-1-detect.yaml` for the real example this
   rule exists because of (its prompt used to hardcode a sibling routine's id).
5. **Slack channel names/ids are the one exception** — kept as-is in prompt text. A channel isn't
   reissued on restore, and which channel a routine posts to is part of its actual behaviour, not an
   artefact of this account.

The validator scans raw file text (not just parsed fields) for bare UUIDs and `trig_…`/`env_…`
patterns, so a leaked id anywhere — including inside the prompt — fails CI.

## Applying changes to the live account

There is no automatic apply step, and there permanently won't be — this isn't a gap waiting on a
fix, it's a settled platform limitation. A cloud routine cannot call `RemoteTrigger`: a routine
built for exactly this purpose (read this repo, reconcile the live account) searched exhaustively
for it at runtime and found nothing, despite `RemoteTrigger` being accepted in its `allowed_tools`
at creation time. Separately, there is no API for creating, updating, or listing routines at all —
routine management only works from a session with a claude.ai subscription login (the web UI, the
Desktop app, or the CLI); a stored API credential used by an unattended process was considered and
ruled out because no such credential exists for this API in the first place, not because of a risk
tradeoff.

Apply a merged change from an interactive session that has `RemoteTrigger` (or the `schedule`
skill): read the changed file(s), resolve `environment`/`mcp_connectors` names and any
`{{routine: …}}` placeholders to live ids by hand, and call `RemoteTrigger action: "create"` /
`"update"` matching by exact `name`. Never delete a live routine whose file was removed here — the
API can't anyway — disable it instead.

## Checklist when adding or changing a routine

1. Add or edit `routines/<slug>.yaml` per `schema/routine.md`. Never paste in a raw id — name it.
2. If it references a sibling routine, use `{{routine: <exact name>}}`.
3. Update the summary table in `README.md`.
4. `.github/copilot-instructions.md` — mirror any structural/convention change here too (see the
   MIRROR RULE above).
5. Open a PR; CI runs `scripts/validate_routines.py`. Merge, then apply it to the live account by
   hand (see "Applying changes to the live account" above).

## Git and pull requests

Same rules as the rest of L337-org: no direct commits to `main`, PR + ≥1 approval with code-owner
review, squash-only, signed commits, resolved threads, Copilot review, required status checks green
(`Validate routines`). `CODEOWNERS`: `@GavinLucas @claudeleet`.

A `main` ruleset enforces all of this, matching `docker-mcp`'s own `main` ruleset — deletion/
force-push/signature protection, 1 approval with required code-owner review, dismiss stale reviews,
resolved threads required, squash-only, Copilot review on every push, `Validate routines` as the
required status check. It's checked in for reference at
[`.github/rulesets/main.json`](.github/rulesets/main.json) — keep the file in sync by hand if the
live ruleset changes (its `required_status_checks` is this repo's own CI job name, `Validate
routines`, and it omits `code_scanning`/`code_quality` since this repo ships no application code to
scan).

## Visibility

Public, matching every other L337-org repo. Reviewed for content before publishing: no secrets,
no issue keys or wiki links, no raw account-specific ids (enforced by `scripts/validate_routines.py`
in CI). The audit/review heuristics a routine's prompt documents (e.g. what `ci-failure responder`
treats as flaky-vs-real) are public in the same sense this org's CI configuration already is —
not a meaningfully greater disclosure.
