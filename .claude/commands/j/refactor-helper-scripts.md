---
argument-hint: Integer number of tech debt tasks to attempt implementing from `scripts/TODO.md`.
description: Implement the top $ARGUMENTS of tech debt items from `scripts/TODO.md`.
---

$tech_debt_items = The top $ARGUMENTS tech debt items out of `scripts/TODO.md` that are NOT marked as completed.

for $tech_debt_item in $tech_debt_items:
    Use create-helper-script subagent with arguments "REFACTOR $tech_debt_item"