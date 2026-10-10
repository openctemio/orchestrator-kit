#!/usr/bin/env bash
# SessionStart: inject a short, local-only `octl status --short` (no network) as context.
# Silent when the project has no octl.json.
set -u
dir=$(cd "$(dirname "$0")" && pwd)
octl="$dir/../../bin/octl"
root="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -f "$root/octl.json" ] || [ -n "${OCTL_CONFIG:-}" ] || exit 0
out=$(cd "$root" && timeout 10 python3 "$octl" status --short 2>/dev/null | head -n 6) || exit 0
[ -n "$out" ] || exit 0
python3 -c "import json,sys; print(json.dumps({\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": sys.stdin.read()}}))" <<<"$out"
