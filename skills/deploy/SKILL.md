---
name: deploy
description: Guarded deploy of the base branch to the project's live environment - back up, rehearse the migrations on a restored copy, apply, verify. Uses the octl live hooks when configured. Use only when the owner asks to deploy.
argument-hint: "[commit]"
disable-model-invocation: true
---

Deploying changes a live system: do it only on the owner's explicit request in this conversation.

1. `octl status` - base-branch CI must be green at the target commit and live healthy. Otherwise stop and report.
2. `octl deploy rehearse $ARGUMENTS` - backup and rehearsal on a restored copy (project hook). Read only the
   tail it prints. Any error, unexpected row-count change or dirty migration version: stop and report.
3. Tell the owner what will change (commit, new migrations, destructive ones, whether the service stops) and
   wait for a yes.
4. `octl deploy apply $ARGUMENTS` - refuses unless that exact commit was rehearsed.
5. Wait about a minute (one `sleep 60` in a background command, not a polling loop), then `octl deploy verify`.
6. On CHECK: report the failing probe and the rollback the project documents; do not improvise a rollback.
7. For tasks merged in this deploy: `octl task advance <ID>` (deploy -> handoff).

Report: commit, migrations applied, verify result.

## Rules behind the hooks (also for projects without octl)

- **Backup, then rehearse on a restore of that backup.** Apply the new migrations to the copy and compare row
  counts of the key tables before and after. A migration that copies rows into a new table shows up here, and
  so does one that silently drops them.
- **Migrate, then switch code.** A hot-reload dev server rebuilds the binary but does not run migrations: new
  code against the old schema error-loops. Apply migrations from the target commit's own files, never from
  another checkout or branch (one deploy ran migrations from a partial tree and the app started against
  missing tables).
- **Stop the service only for destructive migrations** (drop, rename, type change): old code cannot read the
  renamed table. Additive migrations run with the service up. Always restart it, even when a step fails.
- **Fast-forward only.** The live checkout must hold no local edits: check `git status --porcelain` first;
  an untracked migration file there can break the next deploy. Agents never write in the live checkout.
- **Dependencies:** if the lock file changed, reinstall inside the container and restart it.
- **Verify like a user:** health endpoint, the login page and a bad-credential login (expect 401, not 500),
  the database log for new ERRORs, background workers or sensors still checking in. Front-end changes need a
  hard refresh in open browser tabs.
- **Record it:** one line in the handoff file with the commit, migration version, backup name and result.
