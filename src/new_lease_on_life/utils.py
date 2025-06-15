# Utility functions

# Standard Library
import logging
import pathlib
import shlex
import sys


log = logging.getLogger(__name__)

LOG_FORMAT: str = "%(levelname)s|%(asctime)s|%(filename)s:%(lineno)d - %(message)s"
JSON_LOG_FORMAT: str = (
    '{"level": "%(levelname)s", "time": "%(asctime)s",'
    '"file": "%(pathname)s", "line": %(lineno)d, "message": "%(message)s"}'
)
# https://docs.python.org/3/library/datetime.html#format-codes
ISO8601_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
ISO8601_DATE_FORMAT_EXT: str = "%Y-%m-%d %H:%M:%S.%f %:z"


# Python function that captures SIGTERM
def handle_process_signals(signum, frame):
    log.warning("application received SIG signal: " + str(signum))

    handle_graceful_shutdown()

    log.warning("exiting the container gracefully")
    # You can at this point use the sys.exit() to exit the program, or
    # continue on with the rest of the code.
    sys.exit(signum)


def handle_graceful_shutdown(e: Exception | None = None) -> None:
    """Respond to any error scenbario to gracefully shutdown."""
    log.warning("Gracefully shutting down.")
    # Graceful shutdown code here.
    log.info("Cleaning up resources")


def __parse_env_line(line: str) -> tuple[str | None, str | None]:
    """Parses a single line into a key-value pair. Handles quoted values and inline comments.
    Returns (None, None) for invalid lines."""
    # Guard checks for empty lines or lines without '='
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None, None

    # Split the line into key and value at the first '='
    key, value = line.split("=", 1)
    key = key.strip()

    # Use shlex to process the value (handles quotes and comments)
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True  # Tokenize by whitespace
    value = "".join(lexer)  # Preserve the full quoted/cleaned value

    return key, value


def read_env_file(file_path: str) -> dict[str, str] | None:
    """Reads a .env file and returns a dictionary of key-value pairs.
    If the file does not exist or is not a regular file, returns None.
    """
    file = pathlib.Path(file_path)
    return (
        {
            key: value
            for key, value in map(__parse_env_line, file.read_text().splitlines())
            if key is not None and value is not None
        }
        if file.is_file()
        else None
    )


def export_env_vars(env_vars: dict[str, str] | None) -> None:
    """Exports environment variables from a dictionary."""
    if env_vars is None:
        env_vars = read_env_file(".env")

    if env_vars is not None:
        for key, value in env_vars.items():
            log.info(f"Exporting {key}={value}")
            # Use os.environ to set the environment variable
            # This will only affect the current process and its children
            sys.modules["os"].environ[key] = value
