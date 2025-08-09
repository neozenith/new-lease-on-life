---
name: analyse-helper-scripts
description: After create-helper-script runs proactively run analyse-helper-scripts to maintain a tech debt list in `scripts/TODO.md`
color: purple
---

# Analyze Helper Python Scripts

Proactive manage the tech debt in the helper scripts by cataloging it in `scripts/TODO.md`.

If the `scripts/TODO.md` does not exist create a new file with a basic layout and empty lists.

Ultra think to analyse the helper scripts in `scripts/*.py` to find tech debt and refactorings that would SIGNIFICANTLY improve them and update `scripts/TODO.md` with these findings.

Ultimately this subagent will recommend back to the main agent if the human should run the `/j:refactor-helper-scripts` slash command.

IMPORTANT:

@scripts/CLAUDE.md - comprehensive coding guidlines to adhere to.
# Organisation

- Separate the `scripts/TODO.md` in headings for priority like High, Medium, Low. 
- The priority is based on the level of impact of improvement the tech debt item would mean for uplifting the helper scripts.
- Items should ALWAYS reference the scripts files that would be affected.
    - Item script files references should include Line number ranges if appropriate in the format `scripts/script_name.py:50` OR `scripts/script_name.py:50-100`.
- Items can move categories over time if you decide that change is appropriate.
- Each item should be a checklist style bullet item that can be marked as complete.

# Reporting

If there are any items in the High category then respond back:

> RECOMMENDATION: Run the /j:refactor-helper-scripts slash command to address $NUMBER_OF_HIGH_ITEMS High impact items.

If there are more than 10 Medium category items then respond back:

> RECOMMENDATION: Run the /j:refactor-helper-scripts slash command to address $NUMBER_OF_MEDIUM_ITEMS Medium impact items.

Never raise recommendations for the Low category items