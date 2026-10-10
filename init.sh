#!/usr/bin/env bash
# Scaffold the kit into a target repository as a project template (no plugin install needed).
#   ./init.sh /path/to/repo [--force] [--dry-run]
# Idempotent: existing files are left alone unless --force; identical files are skipped.
# Never deletes anything.
set -euo pipefail

KIT=$(cd "$(dirname "$0")" && pwd)
TARGET=""; FORCE=0; DRY=0
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) TARGET=$a ;;
  esac
done
[ -n "$TARGET" ] || { echo "usage: $0 /path/to/repo [--force] [--dry-run]" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "no such directory: $TARGET" >&2; exit 2; }
TARGET=$(cd "$TARGET" && pwd)
[ "$TARGET" != "$KIT" ] || { echo "refusing to scaffold into the kit itself" >&2; exit 2; }

created=0; skipped=0
TMPF=$(mktemp)
trap 'rm -f "$TMPF"' EXIT
# put SRC DST [MODE] [REWRITE]: copy one file; REWRITE=1 points bare octl/consult calls at .claude/bin
put() {
  local src=$1 dst=$TARGET/$2 mode=${3:-644} rewrite=${4:-0} tmp=$TMPF
  if [ "$rewrite" = 1 ]; then
    sed -e 's#`octl #`./.claude/bin/octl #g' -e 's#`consult #`./.claude/bin/consult #g' "$src" > "$tmp"
  else
    cat "$src" > "$tmp"
  fi
  if [ -e "$dst" ] && cmp -s "$tmp" "$dst"; then
    skipped=$((skipped + 1))
  elif [ -e "$dst" ] && [ "$FORCE" = 0 ]; then
    echo "keep     $2 (exists; --force to overwrite)"; skipped=$((skipped + 1))
  else
    echo "write    $2"
    if [ "$DRY" = 0 ]; then
      mkdir -p "$(dirname "$dst")"; cat "$tmp" > "$dst"; chmod "$mode" "$dst"
    fi
    created=$((created + 1))
  fi
}

put "$KIT/bin/octl" .claude/bin/octl 755
put "$KIT/bin/consult" .claude/bin/consult 755
for f in "$KIT"/hooks/scripts/*; do [ -f "$f" ] || continue; put "$f" ".claude/hooks/scripts/$(basename "$f")" 755; done
put "$KIT/statusline/statusline.py" .claude/statusline.py 755
for f in "$KIT"/agents/*.md; do put "$f" ".claude/agents/$(basename "$f")" 644 1; done
for d in "$KIT"/skills/*/; do
  n=$(basename "$d"); put "$d/SKILL.md" ".claude/skills/$n/SKILL.md" 644 1
done
put "$KIT/templates/settings.json" .claude/settings.json
put "$KIT/templates/BRIEF-common.md" .claude/BRIEF-common.md 644 1
put "$KIT/templates/mcp.json" .mcp.json.example
put "$KIT/templates/CLAUDE.md" CLAUDE.md 644 1
put "$KIT/templates/octl.json" octl.json
put "$KIT/templates/HANDOFF.md" HANDOFF.md

# ignore local state (task board, reservations, council records)
if [ "$DRY" = 0 ]; then
  touch "$TARGET/.gitignore"
  for line in ".octl/" ".claude/council/" ".claude/settings.local.json"; do
    grep -qxF "$line" "$TARGET/.gitignore" || { echo "$line" >> "$TARGET/.gitignore"; echo "ignore   $line"; }
  done
fi

echo "done: $created written, $skipped kept. Next:"
echo "  1. edit octl.json (repo, base_branch) and CLAUDE.md (project, commands)"
echo "  2. ./.claude/bin/octl status --short   and   ./.claude/bin/octl route --kind change"
echo "  3. optional MCP: copy .mcp.json.example to .mcp.json, keep only what you use, set tokens as env vars"
