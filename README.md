# claude-routines

Authoritative, version-controlled copies of every Claude cloud routine ("scheduled cloud agent")
running for L337-org, so the org's automation can be audited, reviewed via PR like any other
change, and recreated on demand rather than existing only as opaque state in a web UI.

**This repo is authoritative.** A routine's live configuration should be a projection of its file
here, never the other way round.

**Applying a change is currently manual, not automatic.** [`Reconcile routines with claude-routines`](routines/reconcile-routines-with-claude-routines.yaml)
documents the intended algorithm (create what's missing, update what's drifted, disable — never
delete, the API doesn't allow it — any live routine with no matching file here) but is **disabled**:
its first real run confirmed that `RemoteTrigger`, despite being accepted in `allowed_tools` at
creation time, is not actually available inside a cloud routine's own session, so it cannot list,
create, update, or disable anything. Until that's resolved (see the routine file's `note` for the
options under consideration), apply a merged change by hand — from an interactive Claude Code
session that does have `RemoteTrigger` (or the `schedule` skill), read the changed file(s) and
apply them following the same algorithm the disabled routine documents.

## Layout

One YAML file per routine under [`routines/`](routines/), named from a slugified version of its
`name`. See [`schema/routine.md`](schema/routine.md) for the field reference, and
[`scripts/validate_routines.py`](scripts/validate_routines.py) — run in CI on every push and PR —
for the checks that keep files honest.

## What's excluded, and why

- **No secrets or private data.** A routine's prompt is operational instructions, not a place for
  credentials, tokens, or anything an attacker could use.
- **No routine URL.** The `https://claude.ai/code/routines/{id}` link for a routine is not stored.
  It's meaningless for the stated purpose here (a restored routine gets a new id and therefore a
  new URL) and there's no reason to publish it.
- **No other account-specific id, for the same reason.** A routine's own id, its MCP connector's
  `connector_uuid`, and its `environment_id` are all reissued on restore, so none of them are
  stored raw. Each is referenced **by name** instead (`environment: Default`,
  `mcp_connectors: [Slack]`), and the sync routine resolves the current live id for that name each
  time it runs (or would, once reconciliation runs anywhere). A prompt that needs to name a *sibling* routine (e.g. one routine triggering
  another) uses a `{{routine: <exact name>}}` placeholder rather than a hardcoded id — see
  `docker-py-sdk-audit-phase-1-detect.yaml` for a real example, and `schema/routine.md` for the
  convention. `scripts/validate_routines.py` fails the build if a raw id, uuid, or unresolved
  placeholder slips into a file.

Slack channel names/ids embedded in a routine's own prompt (e.g. `#docker-mcp`, `C0BAP2FTQ6N`) are
kept as-is — unlike the ids above, a channel doesn't get reissued on restore, and it's part of the
routine's actual functional behaviour (which channel it posts to), not an artefact of this account.

## Routines

| Name | Schedule (UTC) | Enabled | Repositories | Purpose |
|---|---|---|---|---|
| [MCP surface standard audit](routines/mcp-surface-standard-audit.yaml) | Monthly, 8th 09:00 | ✅ | docker-mcp, send-to-influx | Audits both MCP servers' tool surfaces against the org's AI-consumer tool-quality standard. |
| [MCP Registry marker drift](routines/mcp-registry-marker-drift.yaml) | Weekly, Wed 08:30 | ✅ | docker-mcp | Checks docker-mcp's MCP Registry ownership markers and listing haven't drifted from `server.json`. |
| [APT channel serving check](routines/apt-channel-serving-check.yaml) | Daily 07:40 | ✅ | apt, send-to-influx | Confirms the apt.l337.org APT channel actually serves an installable package, from the outside. |
| [Blocked-on-upstream re-evaluation](routines/blocked-on-upstream-re-evaluation.yaml) | Monthly, 1st 09:00 | ✅ | send-to-influx, docker-mcp, homebrew-tap | Re-tests recorded upstream blockers (e.g. the Homebrew dylib issue) to see if any have cleared. |
| [Weekly standards reminder (org)](routines/weekly-standards-reminder-org.yaml) | Weekly, Fri 08:15 | ✅ | docker-mcp, send-to-influx, apt, .github, homebrew-tap | Org-wide sweep for policy drift (action pins, lockfiles, docs mirrors, CI coverage, `.github` content). |
| [send-to-influx ci-failure responder](routines/send-to-influx-ci-failure-responder.yaml) | Every 6h | ✅ | send-to-influx, apt | Triages open `ci-failure` issues: investigates, fixes, or stands down for a human. |
| [ci-failure responder](routines/ci-failure-responder.yaml) | Every 6h | ✅ | docker-mcp | Triages open `ci-failure` issues: investigates, fixes, or stands down for a human. |
| [Glama listing drift check](routines/glama-listing-drift-check.yaml) | Weekly, Wed 08:00 | ✅ | docker-mcp | Checks docker-mcp's Glama.ai directory listing (grade, metadata) for drift from the live repo. |
| [docker-py SDK audit (Phase 1 — detect)](routines/docker-py-sdk-audit-phase-1-detect.yaml) | Weekly, Mon 08:00 | ✅ | docker-mcp | Detects docker-py SDK coverage gaps / deprecated surface; files an issue and triggers Phase 2. |
| [docker-py SDK audit (Phase 2 — draft PR)](routines/docker-py-sdk-audit-phase-2-draft-pr.yaml) | — (manual only) | ❌ | docker-mcp | Drafts a PR for an issue Phase 1 filed. Disabled by design — fires only when Phase 1 runs it. |
| [Reconcile routines with claude-routines](routines/reconcile-routines-with-claude-routines.yaml) | Daily 06:00 + push webhook (any branch) | ❌ (see note) | claude-routines | Documents the intended reconcile algorithm; disabled — cloud routines can't call `RemoteTrigger`. |

## Recreating or updating a routine

Read its file, then apply it by hand from an interactive session with `RemoteTrigger` (or the
`schedule` skill) — `RemoteTrigger action: "create"` / `"update"`, matching by exact `name`,
resolving `environment`/`mcp_connectors` names and any `{{routine: …}}` placeholders to live ids
yourself (see `schema/routine.md`). For a brand-new routine that needs an MCP connector not
currently attached to anything live, attach the connector once via
<https://claude.ai/customize/connectors> first — there's no way to invent a connector id, only carry
forward one that already exists on some live routine.

## Making a change

Edit the routine's YAML file (or add a new one) and open a PR as usual. `scripts/validate_routines.py`
runs in CI. Once merged, apply it to the live account by hand (see above) until automatic
reconciliation has a working mechanism.
