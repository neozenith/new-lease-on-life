#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
# ]
# ///

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

git_root = Path(__file__).parent.parent.resolve()
log_file = git_root / "claude_hooks.log"

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),  # Append to file
            logging.StreamHandler(),  # Also output to console
        ],
    )

    # Read hook context from stdin
    try:
        hook_data = json.loads(sys.stdin.read())
        hook_event = hook_data.get("hook_event_name", "Unknown")
        session_id = hook_data.get("session_id", "Unknown")
        tool_name = hook_data.get("tool_name", "N/A")

        log.info(f"CLAUDE HOOKS::{hook_event}::SessionID={session_id}::Tool={tool_name}")

        # Log additional context for specific events
        if hook_event == "PreToolUse" and "tool_input" in hook_data:
            tool_input = (
                str(hook_data["tool_input"])[:200] + "..."
                if len(str(hook_data["tool_input"])) > 200
                else str(hook_data["tool_input"])
            )
            log.info(f"CLAUDE HOOKS::{hook_event}::ToolInput={tool_input}")
        elif hook_event == "UserPromptSubmit" and "prompt" in hook_data:
            prompt = (
                hook_data["prompt"][:100] + "..."
                if len(hook_data["prompt"]) > 100
                else hook_data["prompt"]
            )
            log.info(f"CLAUDE HOOKS::{hook_event}::Prompt={prompt}")

    except (json.JSONDecodeError, Exception) as e:
        log.error(f"CLAUDE HOOKS::ERROR::Failed to parse hook data: {e}")
        log.info(f"CLAUDE HOOKS::FALLBACK::Running with args: {sys.argv[1:]}")
