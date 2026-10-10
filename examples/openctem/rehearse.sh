#!/bin/bash
# Backup live, extract the commit's migrations, rehearse them on a restored copy.
# Usage: rehearse.sh SHA   (octl passes a validated, quoted commit id)
set -euo pipefail
P=$1; ROOT=/home/ubuntu/projects/openctemio; SP=$ROOT/agent-ops/supervisor
TS=$(date -u +%Y%m%dT%H%M%SZ); echo "$TS" > "$SP/ts"
mkdir -p ~/backups
docker exec openctemio-postgres-1 pg_dump -U openctem -d openctem -Fc > ~/backups/openctem-pre-deploy-$TS.dump
ls -lh ~/backups/openctem-pre-deploy-$TS.dump | awk '{print "backup",$5}'
M="$SP/mig-$TS"; mkdir -p "$M"
git -C $ROOT/openctem archive "$P" api/migrations | tar -x -C "$M" --strip-components=2
echo "migrations: $(ls "$M" | wc -l) files, max $(ls "$M" | grep up.sql | sort | tail -1)"
docker rm -f deploy-rehearsal-pg >/dev/null 2>&1 || true
docker run -d --name deploy-rehearsal-pg -e POSTGRES_PASSWORD=rehearse -e POSTGRES_USER=openctem -e POSTGRES_DB=openctem postgres:17-alpine >/dev/null
for i in $(seq 1 30); do docker exec deploy-rehearsal-pg pg_isready -U openctem -q 2>/dev/null && break; sleep 1; done; sleep 2
docker cp ~/backups/openctem-pre-deploy-$TS.dump deploy-rehearsal-pg:/tmp/r.dump
docker exec deploy-rehearsal-pg pg_restore -U openctem -d openctem --no-owner /tmp/r.dump 2>&1 | grep -vE 'role .* does not exist|errors ignored|^$' | head -5 || true
Q="select (select count(*) from audit_logs) audit,(select count(*) from assets) assets,(select count(*) from findings) findings,(select count(*) from users) users,(select count(*) from tenants) tenants"
echo "before: $(docker exec deploy-rehearsal-pg psql -U openctem -d openctem -tAc "$Q")"
docker run --rm --network container:deploy-rehearsal-pg -v "$M":/m:ro migrate/migrate:v4.18.3 -path /m -database "postgres://openctem:rehearse@127.0.0.1:5432/openctem?sslmode=disable" up 2>&1 | tail -12
echo "after:  $(docker exec deploy-rehearsal-pg psql -U openctem -d openctem -tAc "$Q")"
V=$(docker exec deploy-rehearsal-pg psql -U openctem -d openctem -tAc 'select version,dirty from schema_migrations')
echo "version: $V"
case "$V" in *"|t") echo "rehearsal left the schema dirty" >&2; exit 1 ;; esac
