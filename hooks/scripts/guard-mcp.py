#!/usr/bin/env python3
"""PreToolUse guard for MCP tools: ask before any tool that is not clearly read-only.

A tool counts as read-only when its name (after mcp__<server>__) starts with one of
$GUARD_MCP_READ_PREFIXES (comma-separated; default below). Everything else returns
permissionDecision "ask", so a person confirms writes such as creating issues or
merging pull requests. Deny/ask permission rules in settings still apply on top.
"""
import json
import os
import sys

DEFAULT = "get_,list_,search_,read_,describe_,query,find_,view_,fetch_,show_"


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    name = data.get("tool_name") or ""
    if not name.startswith("mcp__"):
        return 0
    tool = name.split("__", 2)[-1].lower()
    prefixes = [p.strip() for p in (os.environ.get("GUARD_MCP_READ_PREFIXES") or DEFAULT).split(",") if p.strip()]
    if any(tool.startswith(p) for p in prefixes):
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "ask",
        "permissionDecisionReason": f"guard-mcp: {name} may change external state; confirm it"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
