---
name: measure-then-decide
description: Answer a "should we redesign X" question with numbers from the running system first, then options, a recommendation and owner decisions. Use for research notes, design questions and complaints like "this creates too many runs/alerts/jobs".
---

1. Measure the current behaviour on the real system, read only, aggregates only. On a production database
   that means a read-only transaction and no row data in the report. Get 3 to 5 numbers that frame the
   problem (counts per day, sizes, ratios, streaks).
2. Find the mechanism behind the numbers in the code (file:line), not just the symptom. Often it is a
   small cause, such as jitter that splits batches or a refusal scored as a failure, not a missing big
   abstraction.
3. Options: the small fix, the structural change, and the presentation-only change. For each give
   trade-offs: retries, partial failure, fairness, audit, UI, and how much code moves.
4. Recommend the smallest change that fixes the measured cause. Put the bigger design behind a measurable
   trigger ("if more than N per day remain after 7 days").
5. Write decisions D1..Dn the owner can accept one by one. Mark the ones that need a real choice.
6. Add a threat model and the tests that must exist, and a date to re-measure.

Then implement P0 in small PRs. Keep follow-ups in the task list, not in the note alone.
