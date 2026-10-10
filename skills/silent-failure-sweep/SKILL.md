---
name: silent-failure-sweep
description: Find features that look configured but never run - workers whose query can never match, gates that cancel each other, handlers nothing calls, checks that report success without doing anything. Use for bug hunts, audits, "why does X never happen" questions, and before claiming a feature works.
---

The most common real defect in a mature codebase is not a crash. It is a feature that is wired, configured and
documented, yet inert: no error, no log, no alert. Instances found in practice:
- a reaper's inner join excluded the rows it was meant to reap, so runs stayed "running" for weeks;
- an expiry checker ran every minute, but no producer ever set the expiry column (fix: default it in the
  constructor, not at each call site);
- a security scan job ran only on `push`, so on its schedule it scanned nothing and reported green;
- a cache-cleanup cron deleted an old path after a framework upgrade moved the cache; the disk filled;
- an event was enabled at one gate on purpose, then dropped by a second filter that read a field with a
  different meaning for that event.

## Sweep
1. For each worker, scheduler, reaper or notifier: read its selection query and ask "can a real row ever match?"
   Then measure it on real data: `count(*)` of rows matching, and of rows that should match.
2. For each column a worker filters on: who writes it? `grep` for setters. A column read but never written is
   inert.
3. For each delivery path: list every predicate that must be true (feature flag, event-type gate, severity
   gate, permission, module). Were they designed together? Does one field carry two meanings?
4. For each route, job, and handler: is it registered and called? Unregistered handlers, routes no UI calls,
   and UI actions with empty handlers are the same class.
5. For each CI gate and script: can it fail? Does it read the env vars the job actually sets? Did it ever
   report a skip count, and is that count sane?
6. For each cron or cleanup: compare its log before and after a run. Identical numbers mean it did nothing.

## Fixing
- Fix at the single source (constructor, shared query, one gate), not at every call site.
- If the promised feature cannot exist (no key to join on), retract the promise in code and docs instead of
  building something speculative.
- Add a test that drives the real path end to end and asserts the effect (the row changes, the event fires).
- Add a metric or log line for "matched 0 rows N times in a row" where silence would hide the next regression.
