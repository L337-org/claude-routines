# Common AI instruction router (temporary - spike branch, never merged)

This file stands in for the single common instruction file LO's restructure proposes: a router that
points at the further instructions relevant to the action being performed. It is reached only by the
pointer in `.github/copilot-instructions.md`; nothing loads it natively.

The rules below are not project policy. They exist to establish what reaches the reviewer.

- `scripts/spike_probe.py` must never use the `dict()` constructor. Use a dict literal. If a change
  uses `dict()`, flag it and include the exact string `CANARY-ROUTER-4M9X` in your comment.

Read `docs/ai/review.md` before reviewing a pull request. It carries the rules specific to
reviewing, which are deliberately not repeated here.
