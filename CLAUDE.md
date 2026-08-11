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

## Reconcile routine — disabled, documents an algorithm it cannot currently run itself

`routines/reconcile-routines-with-claude-routines.yaml` documents the intended reconciliation
algorithm (read every file, list live routines via `RemoteTrigger`, resolve `{{routine: …}}`
placeholders, create/update to match, **disable** — never delete, the API can't — any live routine
with no matching file, report to Slack, silent on a clean run) but its live routine is **disabled**.
Its first real run (fired correctly by the push webhook — wired via `RemoteTrigger
create_webhook_trigger`, once, by hand) discovered that `RemoteTrigger`, despite being accepted in
`allowed_tools` at creation time, is not actually present inside a cloud routine's own session —
confirmed by exhaustive `ToolSearch` calls inside that run, not merely an assumption. Every step of
the algorithm needs it, so the routine can only ever fail; it correctly diagnosed this and posted an
honest Slack failure notice instead of pretending to succeed, then was disabled to stop it repeating
that failure daily.

**Applying a change is manual until this has a real mechanism.** From an interactive session that
does have `RemoteTrigger` (or the `schedule` skill), read the changed file(s) and apply the same
algorithm by hand. See the routine file's `note` for the candidate fixes under consideration (an
interactive/human apply step permanently, vs. a scoped API credential a routine could call over
plain HTTPS instead of the tool — the latter is a new stored-secret decision needing explicit
sign-off, not something to build unprompted).

The webhook itself does fire correctly on every push to this repo (not scoped to `main` — the API
rejected every branch-scoping key tried, only an empty filter was accepted — but harmless, since the
git source always clones `main` regardless, so an off-main push would only ever cost one no-op
pass); the gap is entirely in what the routine can do once it runs.

## Checklist when adding or changing a routine

1. Add or edit `routines/<slug>.yaml` per `schema/routine.md`. Never paste in a raw id — name it.
2. If it references a sibling routine, use `{{routine: <exact name>}}`.
3. Update the summary table in `README.md`.
4. `.github/copilot-instructions.md` — mirror any structural/convention change here too (see the
   MIRROR RULE above).
5. Open a PR; CI runs `scripts/validate_routines.py`. Merge, then apply it to the live account by
   hand (see "Reconcile routine" above) — there is currently no automatic apply step.

## Git and pull requests

Same rules as the rest of L337-org: no direct commits to `main`, PR + ≥1 approval with code-owner
review, squash-only, signed commits, resolved threads, Copilot review, required status checks green
(`Validate routines`). `CODEOWNERS`: `@GavinLucas @claudeleet`.

**Most of this is enforced already**, via a `main` ruleset created and maintained through the GitHub
**web UI** (not the API — see below), checked in for reference at
[`.github/rulesets/main.json`](.github/rulesets/main.json) and kept in sync with `docker-mcp`'s own
`main` ruleset shape by hand (its `required_status_checks` is this repo's own CI job name, `Validate
routines`, and it omits `code_scanning`/`code_quality` since this repo ships no application code to
scan). **The one exception is "Require review from Code Owners"** — gated behind a public repo or a
paid plan even in the UI, so it's off until this repo goes public; that's the one item on the
"revisit when public" list, not a general enforcement gap.

The REST **and** GraphQL write APIs are blocked entirely for a private repo on the org's free plan
— confirmed by testing both, not assumed: `gh api` create/update and a GraphQL
`updateRepositoryRuleset` mutation all return `403 Upgrade to GitHub Pro or make this repository
public`, regardless of `enforcement: "active"` vs `"disabled"`. GraphQL *reads* work fine (that's
how the ruleset's live state gets diffed against `.github/rulesets/main.json`), so treat any
future ruleset change as **UI-only while private** — don't reach for `gh api` expecting it to work.

## Visibility

Private for now — this repo carries the full operating instructions of every org routine, which
isn't necessary to publish for the "recreate on demand" goal even though none of it is secret. This
is also the reason nothing above is enforced yet (see the ruleset note above) — going public is
what would activate it, "when it would be needed most anyway."
