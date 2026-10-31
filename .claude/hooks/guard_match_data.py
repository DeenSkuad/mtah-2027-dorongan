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
    r"(^|[\s/'\"=(])data/(?!README\.md\b)"   # anything under data/ except its README
    r"|\.mp4\b"                              # either match video
    r"|_atd\.(txt|xml)\b"                    # tracking
    r"|_homography\.csv\b"                   # camera geometry
    r"|_smart_tagging\.xml\b"                # tactical tagging
    r"|\.local\.json\b"                      # stats measured on the match
)

MESSAGE = ("Blocked by R1: match data must not reach a cloud LLM. "
           "Ask a human to run this locally and paste back aggregate scores only.")


def is_blocked(tool_name, tool_input):
    """Return the refusal message if this call touches match data, else None."""
    for key in SCANNED_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and MATCH_DATA.search(value):
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
