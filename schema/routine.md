# Routine file schema

One file per routine under `routines/`, named `<slug of name>.yaml`. Mechanically checked by
`scripts/validate_routines.py` - this doc explains the *why*; the script is the source of truth for
the exact rules.

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | yes | string | The routine's identity. Matching between this repo and the live account is by exact name string, never by id. Renaming a routine here creates a new live routine and orphans the old name (which then gets disabled) - treat a rename as delete+create. |
| `enabled` | yes | boolean | Mirrors the live `enabled` flag exactly. |
| `schedule.cron` or `schedule.run_once_at` | yes, exactly one | string | 5-field cron, UTC (1 hour minimum interval) or an RFC3339 UTC timestamp for a one-shot. |
| `model` | yes | string | e.g. `claude-sonnet-5`, `claude-opus-5`. |
| `environment` | yes | string | The environment's **name** (e.g. `Default`), never its `environment_id`. See "Why no raw ids" below. |
| `repositories` | yes | list of URLs | `https://github.com/...` sources the routine's session is given. |
| `allowed_tools` | yes | list of strings | Tool names the routine's session may use. |
| `mcp_connectors` | no | list of strings | MCP connector **names** exactly as the platform spells them - `Slack`, `Atlassian-Rovo` (a hyphen, not an underscore) attached via <https://claude.ai/customize/connectors>, never `connector_uuid`. **Never list `GitHub` here** - see "GitHub access is not a connector" below. |
| `network_allowlist` | no | list of hostnames | Domains this routine's cloud environment needs on its outbound allowlist to do its job (bare hostnames, no scheme/path). Best-effort - populated from domains a routine's own prompt explicitly names as required, not an exhaustive audit of every fetch target. Extend it when a routine reports a blocked domain it needs. **Not part of the live routine config** (like `note`): the allowlist belongs to the shared *environment*, so this field records what that environment must permit for the routine to work, and `RemoteTrigger` never returns it. Absence from live config is expected, not drift. Declare a host only where the prompt actually instructs a fetch of it - a host merely mentioned in passing does not belong here. |
| `autofix_on_pr_create` | only if the routine opens PRs | boolean | Must be `true` on any routine whose prompt instructs opening a pull request, and absent on every other routine. Validation enforces both. See "Why autofix_on_pr_create must be true, explicitly" below. |
| `note` | no | string | Context for a human reading this file. Not part of the live routine config, and exempt from the prompt-content rule below - so it is where a date, an incident or an issue reference goes when a human needs it and the routine does not. |
| `prompt` | yes | string (block literal) | The routine's full instructions, verbatim, except for cross-routine references (see below). Must read as an instruction, not a changelog: see "Why a prompt carries no history" below. |

## Why `autofix_on_pr_create` must be true, explicitly

This field lives in the live routine's `job_config.ccr.session_context`. It gates whether the
routine is subscribed to its own pull requests' events, so it decides whether the routine is ever
woken for a CI failure or a review on a PR it opened.

**It is undocumented.** As of 21 Aug 2026 it appears nowhere in
<https://code.claude.com/docs/en/routines>, so there is no stated default and no commitment that
today's behaviour continues. Re-check the docs before relying on anything here.

**`false` suppresses PR-event delivery.** Verified by comparing two runs of routines in this repo,
same prompts, days apart:

* `L337-org/docker-mcp#193`, field **absent**: the run log shows a `subscription.created` wake three
  seconds after `create_pull_request`, then further wakes on `pull_request_review.submitted` and
  `issue_comment.created`. The routine acted on them and fixed a review finding.
* `L337-org/docker-mcp#194`, field **`false`**: no wake at all. The session went idle on its own
  `sleep` timer and was never told that CI had finished or that a review existed.

**Absent is not a state this repo can hold.** The claude.ai web UI writes `false` into the field
whenever a routine is edited there - that is how it was turned off on all four PR-opening routines
at once, unnoticed, while their prompts were being edited for an unrelated reason. Declaring `true`
gives a value that can be asserted here and seen to drift; absent gives an undocumented default.

**Read the live config before overwriting a routine.** The UI also adds `outcomes` (generated
`claude/*` branch names) which this repo does not model, so applying from these files without
checking what is live first silently strips fields. Applying is manual, so this check is the only
guard there is.

**This does not replace the prompt's own instructions.** The platform's injected posture text
("drive-to-green") says nothing about reading a review *body*, and a run following it missed a
suppressed reviewer finding on #193. Every PR-opening prompt therefore carries its own
read-the-review-body block, which validation also enforces.

## Why a prompt carries no history

Validation rejects three things in a `prompt`, and they are the same mistake in three
shapes: text that records why a rule exists rather than telling the routine what to do.

* **A date.** A dated confirmation is a state claim with a shelf life, and the routine
  cannot tell when it has expired.
* **An issue or pull request reference.** Closed history the routine could read for itself
  if it needed to, which it does not.
* **Narration asserting the rule is true** - "not a theory", "it has leaked this way
  before", "that is not hypothetical".

Every one of them is sent to the model on every run and none of them changes what the
routine does. The prompts had accumulated enough of it to be a measurable share of their
length, and the restated repository state in particular is what produced a run of commits
correcting claims that had quietly gone stale.

The reasoning still has to live somewhere. `note:` takes anything a human reading the file
needs; the commit message and the decision record take the rest. Slack channel names are
unaffected, because the issue rule requires digits after the hash.

## GitHub access is not a connector

A routine's GitHub tool access (`mcp__github__*` - reading/creating issues, PRs, releases,
rulesets, and so on) is provisioned automatically from its `repositories:` grant, not from
`mcp_connectors`. Checked directly against the live account (`RemoteTrigger action: "list"`, not
assumed): every routine in this repo currently shows exactly one entry in its live
`mcp_connections` - `Slack` - including routines whose prompts rely on GitHub MCP tools as a
fallback and have used them successfully in a real run. There is no attachable "GitHub" connector
in this account's connector settings for one to point at.

**Never add `GitHub` (or similar) to a routine's `mcp_connectors` list.** Unlike `Slack`, it would
not resolve to any live `connector_uuid`, so it would only make the file look like it needs an
attach step that doesn't exist - the applier would go looking for a GitHub connector and find
none. A routine's GitHub access follows from its `repositories:` entry alone and needs no
declaration here.

## The connector uuid comes from the interface, not from a name

`mcp_connections` requires a `connector_uuid`; the API will not resolve a connector by name. An
update passing only `{"name": "Atlassian-Rovo"}` is rejected with
`mcp_connections.0.connector_uuid: Field required`, atomically, so nothing is changed.

A connector being connected at account level does not make it addressable. Its uuid has to come out
of the platform once: add it to a routine through the web interface, read the uuid back with
`RemoteTrigger action: "get"`, and reuse that value for every subsequent apply. Do that on a routine
that opens no pull requests, because the interface writes `autofix_on_pr_create: false` into
whatever it touches and the field cannot afterwards be cleared through the API.

## Two API behaviours to know when applying a file by hand

Both found by testing on 2026-08-14, and both bite in the unsafe direction.

**Omitting `mcp_connections` on create attaches EVERY connector on the account, not none.** A create
call that left the field out came back with `Gmail`, `Atlassian-Rovo`, `Claude_Code_Remote` and
`Slack` all attached - so a read-only diagnostic routine was silently given mail access. The default
is maximal, not minimal, and nothing warns. **Always pass the file's `mcp_connectors` explicitly when
applying**, even when it is a single entry, and re-read the response to confirm what actually got
attached rather than assuming the field you sent is the field that took.

**An empty list is ignored, not applied.** `mcp_connections: []` returns the existing set unchanged;
only an explicit non-empty list replaces it. So "this routine should reach nothing" is not
expressible through the API - the closest you can get is replacing the set with the single connector
it genuinely needs. A routine that must reach nothing has to be created that way in the UI, or left
with one harmless connector and a `note:` explaining why.

## Why no raw ids

A routine's own id, its connector's `connector_uuid`, and its `environment_id` are all
account-specific and get reissued the moment a routine is recreated - restoring from this repo into
a different account, or even re-creating in the same account, produces new values. Storing them
would be both a minor privacy leak (they identify this specific account's internal state) and dead
weight: useless the moment they'd actually be needed. So every one of them is named, not quoted, and
resolved to a live id by hand when a change is applied. This is the general form of "don't store the
routine's own URL" - the URL is just the most visible instance of the same problem.

## Cross-routine references

A prompt that needs to trigger or name a *sibling* routine (for example, one routine that runs
another via `RemoteTrigger action: "run"`) uses a placeholder instead of a hardcoded id:

```
{{routine: Exact Sibling Routine Name}}
```

Whoever applies a file substitutes the sibling's current live id for this placeholder by hand.
`scripts/validate_routines.py` fails the build if a placeholder names a routine that
doesn't exist anywhere in this repo, or if a raw `trig_...`/`env_...` id or bare UUID appears anywhere
in a file (the tell that someone pasted live state directly instead of using a name).
