# Scripts

These are python helper scripts composed by me (human author) AND Claude.

@INDEX.md - Complete helper script documentation
@TODO.md - Technical debt and improvements

## Script Guidelines

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

### Running Scripts

Each script should run independently using `uv` like:

```sh
uv run scripts/script_name_here.py
```

You should be able to extract full usage information with the `--help` flag.

```sh
uv run scripts/script_name_here.py --help
```

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

### Caching Files

Use `tmp/claude_cache/{script_name}/` to output temporary files any script needs to leverage between runs.

Check the `m_time` of the cahce files and default to 5 minute timeout. I can at my own discretion delete the entire cache at anytime for a fresh run. You should trust your own caching.

### Handling Files

Always prefer using `pathlib` for handling files. For example reading a JSON files should be as simple as:

```python
from pathlib import Path
import json

data_path = Path("data/")

nodes = json.loads((data_path / "exercises-catalog.json").read_text(encoding="utf-8"))
edges = nodes = json.loads((data_path / "exercise-relationships.json").read_text(encoding="utf-8"))
```

### Configuration and Paths

- All key configuration should be towards the top of the file under the imports.
- They should be all capitalised. (I know this is not "Pythonic" or PEP-8 compliant.)
- All Paths should be relative to `SCRIPT_DIR` as shown in the code example below.

```python
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
ISOCHRONE_FOOT = SCRIPT_DIR.parent / "data/geojson_fixed/foot/"
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

### Minimal CLI Argument Parser

- Always implement a minimal `ArgumentParser` that includes a definition of the script itself.
  This makes it easier for people and agentic coding tools to leverage the `--help` flag to index how to use it.
- DO NOT replace capitalised config variables with CLI arguments or flags.
- **"Minimal" means description only** - avoid adding arguments unless specifically required for the task.

```python
import argparse


if __name__ == "__main__":
    # logger setup excluded in this example
    parser = argparse.ArgumentParser(
        description="Always implement a minimal argument parser that includes a definition of the script itself"
    )
    args = parser.parse_args()
```

### Quality Assurance

Regularly run `ruff` for formatting and linting. eg:

```sh
uvx ruff format --line-length 120 scripts/*.py
uvx ruff check scripts/*.py --fix
uvx rumdl check . --fix
```

# Principles

## High Quality

Where possible abide by the following popular SDLC Principles:

- [Twelve Factor App](https://www.12factor.net/)
- [SOLID](https://en.wikipedia.org/wiki/SOLID)

## Pragmatism

Also consider these pragmatic perspectives:

1. The Frugal Startup Founder Perspective:

  - Time is the most scarce resource
  - Working code > perfect code
  - Technical debt is only debt if you have to pay it back
  - Many startups die with perfect code that never shipped
  - Hardcoded values are fine if they rarely change
  - Duplication is fine if the scripts work independently
  - "Best practices" often optimize for problems you don't have

2. The Experienced Engineer Perspective:

  - Not all technical debt is created equal
  - Some "debt" is actually just different trade-offs
  - Context matters more than principles
  - YAGNI (You Aren't Gonna Need It) is often right
  - Premature abstraction can be worse than duplication
  - Working code that ships has infinite more value than perfect code that doesn't

3. The Time-Poor Developer Perspective:

  - Every refactoring has opportunity cost
  - If it works, don't fix it
  - Scripts that run once a month don't need to be perfect
  - Copy-paste is often faster than abstraction
  - Understanding 5 simple scripts is easier than understanding 1 complex framework


## Less is More

IMPORTANT: None of the above principles are more important than:

- Each script needs to stand-alone.
- There is such thing as too much refactoring.

## Pragmatic Filtering Criteria

Before refactoring code, ask:

1. **Does this cause actual failures or data issues?** If no, skip it.
2. **Has this caused a problem in the last 6 months?** If no, skip it.
3. **Would fixing this take more than 1 hour?** If yes, it better be critical.
4. **Is the "fix" more complex than the "problem"?** If yes, skip it.
5. **Will anyone notice if we don't fix this?** If no, skip it.

### Examples of What NOT to refactor:

- Hardcoded URLs that haven't changed in years
- Duplicate retry logic that works fine in each script
- Magic numbers that are commented inline
- Scripts doing "too much" if they work reliably
- Missing abstractions if the concrete implementations work
- Inconsistent patterns if each pattern works for its context
- Configuration that could be extracted but doesn't need to be

### Examples of What TO refactor / fix:

- Code that crashes: `async def` without implementation
- Data corruption risks: Writing to wrong directory
- Security issues: API keys in code (not just hardcoded endpoints)
- Performance issues that matter: 30-second operation that could be 1 second
- Frequent pain points: Something you fix manually every week
