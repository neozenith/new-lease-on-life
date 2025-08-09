# Scripts

These are python helper scripts composed by me (human author) AND Claude.

@INDEX.md - Complete helper script documentation
@TODO.md - Technical debt and improvements

## Script Guidelines

### Running Scripts

Each script should run independently using `uv` like:

```sh
uv run scripts/script_name_here.py
```

### Script Dependencies

They should leverage the [PEP-723](https://peps.python.org/pep-0723/#example) inline metadata to define library dependencies like this example which adds the `networkx` library:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "networkx",
# ]
# ///

import networkx as nx
```

### Handling Files

Always prefer using `pathlib` for handling files. For example reading a JSON files should be as simple as:

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
