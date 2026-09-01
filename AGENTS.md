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
   hardcoded `trigger_id`.
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
4. Open a PR; CI runs `scripts/validate_routines.py`. Merge, then apply it to the live account by
   hand (see "Applying changes to the live account" above).
5. **The pull request into `main` enumerates the apply steps**, one line each, because applying is
   manual and the person doing it may not be the person who wrote the change. Say which routines are
   created, which are updated, which must be **disabled** as orphans, and any connector that has to
   be attached first. A change that merges without that list leaves the live account silently behind
   the repository, and nothing detects that gap - no routine can reach the routines API to notice.

## Review checklist for a PR touching `routines/*.yaml`

- No raw `trigger_id`, `connector_uuid`, `environment_id`, or bare UUID pasted into any field —
  `scripts/validate_routines.py` should already have failed CI if so, but flag it if seen.
- A cross-routine reference uses `{{routine: <exact name>}}`, and that name exists somewhere in this
  repo.
- The `prompt` reads as an instruction rather than a changelog: no dates, no issue or pull
  request references, no narration asserting a rule is true. `scripts/validate_routines.py`
  fails CI on all three, but flag prose that passes the check and still records history
  rather than instructing. Anything a human needs belongs in `note:`.
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
