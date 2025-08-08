---
name: index-helper-script
description: After create-helper-script runs proactively run index-helper-scripts.
color: purple
---

# Index Helper Python Scripts

Proactively keep `scripts/INDEX.md` up to date to index each of the stand alone python helper scripts (`scripts/*.py`).

## Maintain Helper Python Scripts

Where the python scripts themselves are not up to date and compliant with the below usage documentation, analyse the code and keep the documentation up to date.

## Example Usage Instructions

Curate usage instructions from the top of each helper script which should take this format:

```python
"""
DESCRIPTION: Very verbose description of the intent of this script.

TASK: Normal operation
USAGE:
    uv run scripts/script_name_here.py --extra-args

OUTPUT:
    <example output for the above run usage command.>

TASK: Getting help
USAGE:
    uv run scripts/script_name_here.py --help

OUTPUT:
    <The help output here>
"""
```

## Example Output

```markdown
    # Helper Script Snippet Index

    ## script_name_here

    TITLE: A very concise description of the task the tool achieves.
    DESCRIPTION: Very verbose description of the intent of this script.

    SOURCE: scripts/script_name_here.py

    LANGUAGE: python
    USAGE:
        Concisely describe the inputs for flags or files needed.
    ```sh
        uv run scripts/script_name_here.py --extra-args
    ```
    OUTPUT:
    ```sh
        <example output for the above run usage command.>
    ```

    ----------------------------------------

    ## another_script_name_here

    TITLE: A very concise description of the task this other tool achieves.
    DESCRIPTION: Very verbose description of the intent of this script.

    SOURCE: scripts/another_script_name_here.py

    LANGUAGE: python
    USAGE:
        Concisely describe the inputs for flags or files needed.
    ```sh
        uv run scripts/another_script_name_here.py --input-dir data/
    ```
    OUTPUT:
        Concisely describe the output for the shell or what files are generated or modified.
    ```sh
        <example output for the above run usage command.>
    ```

    ----------------------------------------
```