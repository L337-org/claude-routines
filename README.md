# claude-routines

Authoritative, version-controlled copies of every Claude cloud routine ("scheduled cloud agent")
running for L337-org, so the org's automation can be audited, reviewed via PR like any other
change, and recreated on demand rather than existing only as opaque state in a web UI.

**This repo is authoritative.** A routine's live configuration should be a projection of its file
here, never the other way round.

**Applying a change is manual, and stays that way by design.** A cloud routine cannot call
`RemoteTrigger` - confirmed by testing, not assumed - and there is no API for creating, updating, or
listing routines at all; routine management is only ever possible from a session with a claude.ai
subscription login (the web UI, the Desktop app, or the CLI). So there is no automatic apply step to
build here. Apply a merged change from an interactive Claude Code session with `RemoteTrigger` (or
the `schedule` skill) - see "Recreating or updating a routine" below.

## Layout

One YAML file per routine under [`routines/`](routines/), named from a slugified version of its
`name`. See [`schema/routine.md`](schema/routine.md) for the field reference, and
[`scripts/validate_routines.py`](scripts/validate_routines.py) - run in CI on every push and PR -
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
  `mcp_connectors: [Slack]`), resolved to the current live id by hand when a change is applied. A
  prompt that needs to name a *sibling* routine (e.g. one routine triggering
  another) uses a `{{routine: <exact name>}}` placeholder rather than a hardcoded id - see
  `schema/routine.md` for the convention. `scripts/validate_routines.py` fails the build if a raw
  id, uuid, or unresolved placeholder slips into a file.

Slack channel names/ids embedded in a routine's own prompt (e.g. `#docker-mcp`, `C0BAP2FTQ6N`) are
kept as-is - unlike the ids above, a channel doesn't get reissued on restore, and it's part of the
routine's actual functional behaviour (which channel it posts to), not an artefact of this account.

## Routines

| Name | Schedule (UTC) | Enabled | Repositories | Purpose |
|---|---|---|---|---|
| [MCP surface standard audit](routines/mcp-surface-standard-audit.yaml) | Monthly, 8th 09:00 | ✅ | docker-mcp, send-to-influx | Checks the tool-surface guard tests in both repos still assert what they claim, and reviews recently-changed docstring prose in docker-mcp. |
| [MCP Registry marker drift](routines/mcp-registry-marker-drift.yaml) | Weekly, Wed 08:30 | ✅ | docker-mcp | Checks the published `.mcpb` checksum and the live MCP Registry listing. The in-repo markers are asserted by docker-mcp's own tests. |
| [APT channel serving check](routines/apt-channel-serving-check.yaml) | Daily 07:40 | ✅ | apt, send-to-influx | Confirms the apt.l337.org APT channel actually serves an installable package, from the outside. |
| [Blocked-on-upstream re-evaluation](routines/blocked-on-upstream-re-evaluation.yaml) | Monthly, 1st 09:00 | ✅ | send-to-influx, docker-mcp, homebrew-tap | Re-tests recorded upstream blockers (e.g. the Homebrew dylib issue) to see if any have cleared. |
| [Weekly standards reminder (org)](routines/weekly-standards-reminder-org.yaml) | Weekly, Fri 08:15 | ✅ | docker-mcp, send-to-influx, apt, .github, homebrew-tap | Org-wide sweep for policy drift (action pins, lockfiles, instruction files, CI coverage, `.github` content). |
| [ci-failure responder](routines/ci-failure-responder.yaml) | Twice daily, 06:20 and 18:20 | ✅ | docker-mcp, send-to-influx, apt | Sweeps CI failures across all three repos: records confirmed defects in Jira, reports transient ones to Slack, and opens a PR where a fix is safe. |
| [Glama listing drift check](routines/glama-listing-drift-check.yaml) | Weekly, Wed 08:00 | ✅ | docker-mcp | Compares the three letter grades on docker-mcp's Glama.ai listing against a fixed baseline. Grades only; no metadata and no repo comparison. |
| [MCP vs skills figure drift](routines/mcp-vs-skills-figure-drift.yaml) | Weekly, Thu 07:00 | ✅ | docker-mcp | Re-measures `MCP_VS_SKILLS.md`'s figures and the server/skill functional comparison; opens a PR when a movement is worth republishing. |
| [docker-py SDK audit](routines/docker-py-sdk-audit.yaml) | Weekly, Mon 08:00 | ✅ | docker-mcp | Detects docker-py SDK coverage gaps / deprecated surface, implements the safe ones and opens a PR. |
| [Claude model deprecation check](routines/claude-model-deprecation-check.yaml) | Monthly, 15th 09:00 | ✅ | claude-routines | Checks every `model:` value used in this repo against Anthropic's published deprecation/retirement dates. |

## Recreating or updating a routine

Read its file, then apply it by hand from an interactive session with `RemoteTrigger` (or the
`schedule` skill) - `RemoteTrigger action: "create"` / `"update"`, matching by exact `name`,
resolving `environment`/`mcp_connectors` names and any `{{routine: <exact name>}}` placeholders to live ids
yourself (see `schema/routine.md`). For a brand-new routine that needs an MCP connector not
currently attached to anything live, attach the connector once via
<https://claude.ai/customize/connectors> first - there's no way to invent a connector id, only carry
forward one that already exists on some live routine.

## Making a change

Edit the routine's YAML file (or add a new one) and open a PR as usual. `scripts/validate_routines.py`
runs in CI. Once merged, apply it to the live account by hand (see above).
