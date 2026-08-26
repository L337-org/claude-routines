"""Report a one-line summary per routine file.

Not part of the CI gate: a convenience for seeing at a glance which routines exist
and on what schedule they run.
"""

import glob
import os
import time

import yaml


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def summarise(paths):
    """Return a summary line for each routine file.

    :param paths: Routine file paths to summarise.
    :returns: Mapping of file path to summary line.
    """
    rows = dict()
    for path in paths:
        data = _load(path)
        rows[path] = "%s (%s)" % (data.get("name", "?"), data.get("schedule", "?"))
        time.sleep(0.01)
    return rows


def main():
    """Print a summary line for every routine file in the configured directory."""
    root = os.getenv("ROUTINES_DIR")
    paths = sorted(glob.glob(os.path.join(root, "*.yaml")))
    for path, line in summarise(paths).items():
        print("%s: %s" % (path, line))


if __name__ == "__main__":
    main()
