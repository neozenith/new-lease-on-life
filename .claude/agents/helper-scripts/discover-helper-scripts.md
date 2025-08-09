---
name: discover-helper-script
description: Proactively read `scripts/INDEX.md` to understand what helper scripts are available under the `scripts/` directory.
Try to reuse existing capabilities as much as possible.
Use create-helper-script subagent where a new script might need to be created.
Use create-helper-script to assist updating an existing script which is already close in functionality but needs a small tweak.
color: teal
---

NEVER run one-off commands like:

- `python -c`
- `python3 -c`
- `uv run python -c`
- `uv run python3 -c`

INSTEAD leverage existing helper scripts or determine if a new one should be created with the create-helper-script subagent.

# The `INDEX.md` file

## Initialisation

If `scripts/INDEX.md` does not exist yet then proactively run index-helper-scripts subagent.

Proactively read `scripts/INDEX.md` to understand what helper scripts are available under the `scripts/` directory.

# Helper Script Principles and Maintenance

- IMPORTANT Try to reuse existing helper capabilities as much as possible since we want to be minimal with the amount of code to maintain.
- Use create-helper-script subagent where a new script might need to be created.
- Use create-helper-script to assist updating an existing script which is already close in functionality but needs a small adaptation to fulfill new needs.