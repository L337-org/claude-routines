# Reviewer instructions (temporary - spike branch, never merged)

Reached only by the pointer in `docs/ai/instructions.md`, which is itself reached only by the
pointer in `.github/copilot-instructions.md`. This is the second hop, and the depth the proposed
architecture actually relies on.

The rule below is not project policy.

- `scripts/spike_probe.py` must never use `%`-style string formatting. Use an f-string. If a change
  uses `%` formatting, flag it and include the exact string `CANARY-LEAF-8T3K` in your comment.
