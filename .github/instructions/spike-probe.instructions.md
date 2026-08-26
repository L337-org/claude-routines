---
applyTo: "**/spike_probe.py"
---

# Path-specific instructions (temporary - spike branch, never merged)

Loaded by GitHub's documented path-specific mechanism rather than by a prose pointer. No other file
references this one.

The rule below is not project policy.

- `scripts/spike_probe.py` must never call `os.getenv` without an explicit default. If a change does,
  flag it and include the exact string `CANARY-PATHSPEC-5W6B` in your comment.
