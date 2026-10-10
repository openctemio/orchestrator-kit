#!/usr/bin/env python3
"""Status line: model, context tokens in use, and a warning when the context is big.

Reads the status-line JSON on stdin (model.display_name, context_window.total_input_tokens,
context_window.used_percentage). Warns at $OCTL_CTX_WARN tokens (default 400000) or 80 percent,
because every turn re-reads the whole context: past that point a fresh session is cheaper.
"""
import json
import os
import sys


def render(d, warn):
    model = (d.get("model") or {}).get("display_name") or "?"
    cw = d.get("context_window") or {}
    used = int(cw.get("total_input_tokens") or 0)
    pct = cw.get("used_percentage")
    parts = [f"[{model}]", f"ctx {used/1000:.0f}k" + (f" ({pct:.0f}%)" if isinstance(pct, (int, float)) else "")]
    if used >= warn or (isinstance(pct, (int, float)) and pct >= 80):
        parts.append("BIG CONTEXT: write HANDOFF and start fresh")
    return " ".join(parts)


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    print(render(data, int(os.environ.get("OCTL_CTX_WARN") or 400000)))
