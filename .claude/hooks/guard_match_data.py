#!/usr/bin/env python3
"""PreToolUse hook enforcing rule R1: match data must never reach a cloud LLM.

The competition terms forbid making the provided video, datasets "or any extracts thereof"
available to a hosted LLM. Claude is one. This hook refuses any tool call whose paths or shell
command point at the match assets. File *content* that Claude writes is not scanned: it is code,
and code may name the files it will read when a human runs it locally.

Exit 2 blocks the call and shows stderr to Claude; exit 0 allows it.
"""

import json
import re
import sys

# Keys whose values are paths, globs or shell commands. Deliberately not "content"/"new_string".
SCANNED_KEYS = ("file_path", "path", "pattern", "glob", "command", "notebook_path")

MATCH_DATA = re.compile(
    r"\bdata\b(?!/README\.md\b)"             # the data folder, however it is spelled or reached
    r"|\.mp4\b"                              # either match video
    r"|_atd\b"                               # tracking
    r"|_homography\b"                        # camera geometry
    r"|_smart_tagging\b"                     # tactical tagging
    r"|\.local\b",                           # stats measured on the match
    re.IGNORECASE,
)

# Shell commands that legitimately read the match and print what they find: humans run these.
HUMAN_ONLY_COMMANDS = re.compile(
    r"\bmake\s+(submission|measure|baseline|eval)\b"
    r"|-m\s+['\"]?match\b"                   # pytest -m match
    r"|\b(make_submission|measure_degradation|baseline)\.py\b"
    r"|\bgrep\s+-\w*[rR]"                    # recursive grep ignores .gitignore
    r"|\bfind\s"                             # so does find
)

MESSAGE = ("Blocked by R1: match data must not reach a cloud LLM. "
           "Ask a human to run this locally and paste back aggregate scores only.")


def is_blocked(tool_name, tool_input):
    """Return the refusal message if this call touches match data, else None."""
    for key in SCANNED_KEYS:
        value = tool_input.get(key)
        if not isinstance(value, str):
            continue
        if MATCH_DATA.search(value) or (key == "command" and HUMAN_ONLY_COMMANDS.search(value)):
            return "{} ({}: {})".format(MESSAGE, tool_name, key)
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # not a hook payload; nothing to judge
    reason = is_blocked(payload.get("tool_name", ""), payload.get("tool_input") or {})
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
