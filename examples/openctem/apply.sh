#!/bin/bash
# Migrate live with the rehearsed migrations, fast-forward the live checkout, regenerate contract files.
# Usage: apply.sh SHA. octl stops/starts the api around this script when a migration is destructive.
# The DB password is read from the root .env at run time and never printed.
set -euo pipefail
P=$1; ROOT=/home/ubuntu/projects/openctemio; SP=$ROOT/agent-ops/supervisor
TS=$(cat "$SP/ts"); M="$SP/mig-$TS"
[ -d "$M" ] || { echo "no rehearsed migrations at $M" >&2; exit 1; }
PW=$(grep -E '^DB_PASSWORD=' "$ROOT/.env" | cut -d= -f2-)
docker run --rm --network openctemio_openctem-network -v "$M":/m:ro migrate/migrate:v4.18.3 \
  -path /m -database "postgres://openctem:${PW}@postgres:5432/openctem?sslmode=disable" up 2>&1 | tail -6
git -C "$ROOT/openctem" merge --ff-only "$P" 2>&1 | tail -1
(cd "$ROOT/openctem" && bash scripts/generate-in-docker.sh) >/dev/null
docker rm -f deploy-rehearsal-pg >/dev/null 2>&1 || true
echo "applied $P"
