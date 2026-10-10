# Common brief for every agent (read fully before starting)

## Workspace
- Work only in your own directory: `<work_dir>/<task-id>/`. One clone per agent; one git worktree per PR inside it.
- Never write in the live checkout, another agent's directory, or a shared temp file.
- Run multi-step shell work as `bash -c '...'` with absolute paths; prefer `git -C <dir>` over `cd`.
- No `rm` inside `bash -c` or on paths built from variables (the built-in deletion check stops and prompts the
  owner): use a fresh directory, `find <absolute path> -delete`, or `git clean` in your own clone.
- Keep your scripts, env files and temp files in your own directory; never source a shared one.
- Builds: shared build caches, low parallelism (`nice`, 2-4 workers), one image build at a time.
- Scratch services: reserve ports with `octl port reserve <task> N`; name containers `<task>-*`;
  remove them before you report (`docker rm -f <task>-pg ...`).
- Migrations: use only numbers from `octl mig reserve <task> N`; tests find migrations by name, not number.

## Safety
- Security first: every change states its threat model and authorization/data-isolation impact, with tests for
  the negative cases.
- Never print, copy or commit secrets. Credentials come from environment variables.
- Never kill processes by pattern (`pkill -f`, `killall`) and never run host-wide cleanup (`docker * prune`).
  Kill only PIDs you started; remove only resources you named.
- Never force-push a shared branch. Never merge, release, deploy, delete data or message anyone: those are
  human actions. Stop and ask.

## Token budget
Cost is roughly turns x context size. Keep both small.
- Never paste big output into context: pipe through `tail -n 40`, `grep`, `head` or `jq`; tests to a file,
  print failures only; Read with offset/limit.
- No polling turns: push, then run ONE background `gh pr checks N --watch --fail-fast | tail -5` and act once.
- Run only the tests of the packages you touched; CI runs the rest.
- Independent tool calls go in parallel in one turn. Delegate lookups to the scout agent.
- Report once at the end, then stop. Follow-ups are cheaper in a fresh, short session.

## Process
1. Check existing branches and PRs for your task first; build on existing work.
2. Small PR, one concern. Record it: `octl task pr <task> N`, `octl task advance <task>`.
3. Verify for real (`verify-before-done` skill): build, lint changed code, touched tests, a test that fails
   without the change, and a real functional check.
4. CI green and every review thread resolved, bots too (`pr-review-sweep` skill), before you call it done.
5. Final report (short, plain English): PRs, what changed, what was verified, what the owner must decide.

## Stop conditions
Stop and report when: the PR is green and clean; your budget or turn limit is near; the same gate failed twice
(`octl task fail <task> "why"`); you need a decision; or the next step is outward-facing or irreversible.
