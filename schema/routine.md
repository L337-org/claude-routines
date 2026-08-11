# Routine file schema

One file per routine under `routines/`, named `<slug of name>.yaml`. Mechanically checked by
`scripts/validate_routines.py` — this doc explains the *why*; the script is the source of truth for
the exact rules.

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | yes | string | The routine's identity. Matching between this repo and the live account is by exact name string, never by id. Renaming a routine here creates a new live routine and orphans the old name (which then gets disabled) — treat a rename as delete+create. |
| `enabled` | yes | boolean | Mirrors the live `enabled` flag exactly. |
| `schedule.cron` or `schedule.run_once_at` | yes, exactly one | string | 5-field cron, UTC (1 hour minimum interval) or an RFC3339 UTC timestamp for a one-shot. |
| `model` | yes | string | e.g. `claude-sonnet-5`, `claude-opus-5`. |
| `environment` | yes | string | The environment's **name** (e.g. `Default`), never its `environment_id`. See "Why no raw ids" below. |
| `repositories` | yes | list of URLs | `https://github.com/...` sources the routine's session is given. |
| `allowed_tools` | yes | list of strings | Tool names the routine's session may use. |
| `mcp_connectors` | no | list of strings | MCP connector **names** (e.g. `Slack`), never `connector_uuid`. |
| `network_allowlist` | no | list of hostnames | Domains this routine's cloud environment needs on its outbound allowlist to do its job (bare hostnames, no scheme/path). Best-effort — populated from domains a routine's own prompt explicitly names as required, not an exhaustive audit of every fetch target. Extend it when a routine reports a blocked domain it needs. |
| `note` | no | string | Context for a human reading this file. Not part of the live routine config — the reconcile routine ignores it. |
| `prompt` | yes | string (block literal) | The routine's full instructions, verbatim, except for cross-routine references (see below). |

## Why no raw ids

A routine's own id, its connector's `connector_uuid`, and its `environment_id` are all
account-specific and get reissued the moment a routine is recreated — restoring from this repo into
a different account, or even re-creating in the same account, produces new values. Storing them
would be both a minor privacy leak (they identify this specific account's internal state) and dead
weight: useless the moment they'd actually be needed. So every one of them is named, not quoted, and
resolved to a live id at apply time by the reconcile routine. This is the general form of "don't
store the routine's own URL" — the URL is just the most visible instance of the same problem.

## Cross-routine references

A prompt that needs to trigger or name a *sibling* routine (for example, one routine that runs
another via `RemoteTrigger action: "run"`) uses a placeholder instead of a hardcoded id:

```
{{routine: Exact Sibling Routine Name}}
```

The reconcile routine substitutes the sibling's current live id for this placeholder each time it
applies a file. `scripts/validate_routines.py` fails the build if a placeholder names a routine that
doesn't exist anywhere in this repo, or if a raw `trig_…`/`env_…` id or bare UUID appears anywhere
in a file (the tell that someone pasted live state directly instead of using a name).
