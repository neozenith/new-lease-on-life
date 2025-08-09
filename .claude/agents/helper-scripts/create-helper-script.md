---
name: create-helper-script
description: Proactively create or update helper python scripts under scripts/ instead of 
running one off `bash` or `python3 -c` like commands.
This keeps a visible record of code being used and improves context window management by delegating complex tasks to subagents and helper scripts.
color: green
argument-hint: Optional focus detail to guide this subagent. Include keyword like CREATE / UPDATE / REFACTOR as the first word.
---

# Create / Update / Refactor Helper Python Scripts

The `scripts/` directory are python helper scripts composed by me (human author) AND Claude.
Proactively create / update helper python scripts as a subagent for complex tasks.
Use the below coding standards and guidelines.
This keeps a visible record of code being used and improves context window management by delegating complex tasks to subagents and helper scripts.

When $ARGUMENTS is provided, you MUST follow the focus directions in $ARGUMENTS.

## Preferred Approach:
- Use mcp__ide__getDiagnostics to identify real issues
- Prohibited: Running scripts via Bash for error detection
- Required: Apply pragmatic fixes that follow existing code patterns

## Script Guidelines

### Non-functional requirements

- Make the scripts as simple as possible. This is not for enterprise but for a hobby project.
- I do not need backwards compatability for older python versions.

### Naming Helper Scripts

The files should be named with a key verb to describe what it is doing and the task like `<verb>_<name_of_task>.py`.

Key Verbs:

- `explore`, `discover`, `analyse` - these are research type tasks to dynamically find the current state of something. 
  These can be one off single use scripts too.
- `triage` - these are used to collate log and test information and then critically think about the 
  output to systematically suggest a next step.
- `process`, `export`, `extract`, `migrate`, `convert` - these are all repeatable processes that are idempotent 
  transformations. I can delete their output and get the same deterministic output from the original inputs.
- `fix` - these are similar to transformations but they will be temporary and can be one off single use scripts.

Name of Task:

- Should be between 3-5 words.
- Coupled with the Key Verb conscisely describe what it does.

### Usage Instructions

Each script should run independently using `uv` like:

```sh
uv run scripts/script_name_here.py
```

At the top of each script file include usage documentation like:

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

These `USAGE` examples will act as snippets that get updated inside `scripts/INDEX.md`.

### Script Dependencies

They should leverage the [PEP-723](https://peps.python.org/pep-0723/#example) inline metadata to define library dependencies. 
This example adds the `boto3`, `python-dotenv` and `networkx` libraries:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "boto3",
#   "python-dotenv>=1.0.0",
#   "networkx",
# ]
# ///

import networkx as nx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
```

### Environment Variables

Scan for `.env.sample` to see what enviroment variables should be available and exported.

### Interacting with AWS

- ASSUME that `AWS_PROFILE` is already exported in the current session to provide credentials for the target AWS account.
- Always prefer AWS CDK for deployment management.
- Make use of exporting JSON output results to `tmp/claude_cache/{script_name}/*.json`. This is helpful when triaging and analysing problems.
- Scripts with known cache files should list them as `pathlib.Path` variables at the top of the script as well as their cache timeout which should default to 5 minutes (300 seconds).
- Leverage helper caching checking script like:
    ```python
    """
    Usage:
        python cache_check.py <target_file> [cache_timeout_seconds]

    Exits with 0 if cache expired, or remaining seconds if within cache threshold.
    Default cache_timeout is 300 seconds (5 minutes).
    """
    from pathlib import Path
    import time
    import sys

    file = Path(sys.argv[1])
    cache_timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    sys.exit(int(max(0, min(255, cache_timeout - (time.time() - file.stat().st_mtime)))))
    ```


### Handling Files

ALWAYS prefer using `pathlib` for handling files. For example reading a JSON files should be as simple as:

```python
from pathlib import Path
import json

data_path = Path("data/")

nodes = json.loads((data_path / "exercises-catalog.json").read_text(encoding="utf-8"))
edges = nodes = json.loads((data_path / "exercise-relationships.json").read_text(encoding="utf-8"))
```

### Logging Output

All scripts should use the standard library logger and not `print` statements. eg,

```python
import logging
log = logging.getLoggerName(__name__)

# Body of code here

def main():
    ...

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    main()

```

### Caching Files

Use `tmp/claude_cache/{script_name}/` to output temporary files any script needs to leverage between runs.

Check the `m_time` of the cahce files and default to 5 minute timeout. I can at my own discretion delete the entire cache at anytime for a fresh run. You should trust your own caching.

### Quality Assurance

Regularly run `ruff` for formatting and linting. eg:

```sh
uvx ruff format --line-length 120 scripts/*.py
uvx ruff check scripts/*.py --fix
uvx rumdl check . --fix
```

### Helpful Snippets

If this is not in a `scripts/utils.py` then it might be handy to create it.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests",
# ]
# ///
import logging
import re
import time
import zipfile
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def make_request_with_retry(url, params, max_retries=10, backoff_factor=5, timeout=30):
    """Make HTTP request with exponential backoff retry for rate limiting.

    Args:
        url: The URL to request
        params: Query parameters for the request
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff delay
        timeout: Request timeout in seconds

    Returns:
        Response JSON data

    Raises:
        Exception: If all retries are exhausted due to rate limiting
        requests.HTTPError: For non-429 HTTP errors
    """
    delay = 1
    for attempt in range(max_retries):
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 429:
            log.debug(response.text)
            log.info(
                f"Rate limited (HTTP 429) on attempt {attempt + 1}. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
            delay *= backoff_factor
            continue
        response.raise_for_status()
        return response.json()
    raise Exception(f"Failed after {max_retries} retries due to rate limiting.")


def dirty(output_path: list[Path] | Path, input_paths: list[Path] | Path) -> bool:
    """Check if the output_path file(s) are older than any of the input files.

    Args:
        output_path: List of output file paths or a single output file path
        input_paths: List of input file paths or a single input file path

    Returns:
        True if output_path is older than any input, False otherwise
    """

    if isinstance(output_path, Path):
        output_path = [output_path]

    if not output_path:  # If no output files (potentially from empty globbing) then it is dirty.
        return True

    if any(not p.exists() for p in output_path):
        return True  # If any output file listed doesn't exist, it's considered dirty

    if isinstance(input_paths, Path):
        input_paths = [input_paths]

    min_output_mtime = min(f.stat().st_mtime for f in output_path)
    max_input_mtime = max(f.stat().st_mtime for f in input_paths)

    return (
        min_output_mtime < max_input_mtime
    )  # This means output is dirty if it's older than newest input file


def unzip_archive(zip_path: Path, extract_to: Path | None = None) -> None:
    """
    Unzip a ZIP archive to the specified directory.

    Args:
        zip_path: Path to the ZIP file
        extract_to: Directory to extract files to
    """

    if extract_to is None:
        extract_to = zip_path.parent / zip_path.stem
    log.info(f"Unzipping {zip_path} to {extract_to}")

    if not dirty([f for f in extract_to.rglob("*") if f.is_file()], zip_path):
        log.info(f"Skipping extraction, {extract_to} is up to date.")
        return

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    log.info(f"Unzipped {zip_path} successfully")
```