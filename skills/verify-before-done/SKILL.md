---
name: verify-before-done
description: Prove a change works before calling it done - build, touched tests, a test that fails without the change, a real functional check, then CI green after push. Use before every commit, push, "ready for review" or "done" report.
---

"It compiles" is not done. Changes that built and passed a narrow test run have still broken shared branches:
a merge silently reverted working code, a stricter validation broke tests in another package, and a gate script
that exited 0 on every failure let red tests ship as green.

Before committing:
1. Build and static checks for the touched area: compiler, vet or typecheck, and the project's pinned linter
   (limited to new code if the project gates that way).
2. Tests of the packages you touched, output to a file, print only failures. When you changed shared code
   (a validation, a service many callers use), run that whole package suite, not one test.
3. A test that fails without your change and passes with it. Name it in the report.
4. A real functional check, matched to the change:
   - API: script it (log in, call the endpoint, assert status and body), plus one negative (other tenant,
     missing permission).
   - UI: load the real page in a headless browser at phone and desktop width; check console errors.
   - Job, worker or scan: run it once and watch the data arrive where it should.
   - Formula or ranking: compare old and new output on real-shaped data.
5. After merging the base branch into yours, rerun the touched package tests. Git calls a semantic conflict
   clean (both sides bumping the same constant, two PRs mounting the same route).

After pushing:
6. Run ONE background `gh pr checks <n> --watch --fail-fast | tail -5` and act once when it exits. Do not poll.
7. Fix every red check at the root. A check that is red on the base branch too (a new toolchain CVE, an image
   registry outage) still goes in the report, with the evidence that it is not your change.
8. Make sure your gate scripts can fail: a verify script that always exits 0 is worse than none.

Report: what you ran, the fail-before/pass-after test, the functional check result, CI state.
