---
description: "Analyze codebase and update Mermaid architecture diagram in README"
allowed-tools: ["Bash", "Read", "Write", "LS", "Glob", "Edit", "git"]
---

Hardest think analysing:

- Leverage git repo information as need be.
- Respect the .gitignore file.
- Make use of the Language Server Protocol where available to get the ASTs.
- Try to detect if the repo is a multi-project monorepo.
    - IF multi-project THEN for-each subproject recursively run this command /j:arch
- The file and folder structure of this repo.
- The source code files and their conventions used.
- Significant library dependencies.
- Extra information from markdown files.

Then in the root README.md under a heading called "Architecture Diagram(s)"
create one or many MermaidJS architecture diagram(s) or update the existing one(s)
to appropriately capture the architecture of the project.

If there is already mermaidjs diagrams then use those diagrams as a reference for quality and make better diagrams.
