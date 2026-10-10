---
name: deploy
description: Guarded deploy of the base branch to the project's live environment through the octl live hooks - rehearse on a copy, apply, verify. Use only when the owner asks to deploy.
argument-hint: "[commit]"
disable-model-invocation: true
---

Deploying changes a live system: do it only on the owner's explicit request in this conversation.

1. `octl status` - base-branch CI must be green and live healthy. Otherwise stop and report.
2. `octl deploy rehearse $ARGUMENTS` - backup and rehearsal on a restored copy (project hook). Read only the
   tail it prints. Any error, data-count drop or dirty version: stop and report.
3. Tell the owner what will change (commit, new migrations, destructive ones, whether the service stops) and
   wait for a yes.
4. `octl deploy apply $ARGUMENTS` - refuses unless that exact commit was rehearsed.
5. Wait about a minute (one `sleep 60` in a background command, not a polling loop), then `octl deploy verify`.
6. On CHECK: report the failing probe and the rollback the project documents; do not improvise a rollback.
7. For tasks merged in this deploy: `octl task advance <ID>` (deploy -> handoff).

Report: commit, migrations applied, verify result.
