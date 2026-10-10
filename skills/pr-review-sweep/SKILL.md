---
name: pr-review-sweep
description: Resolve every review thread on a pull request, from humans and bots alike - fix at the root, reply with what changed, resolve. Use before marking a PR ready, before enqueueing it, or when asked to address review comments.
argument-hint: "<pr-number>"
---

A PR is ready only when it is CLEAN, green and has 0 unresolved threads. Bot threads (code scanning, secret
scanners, AI reviewers) count: PRs called "ready" with unaddressed bot findings had to be pulled back.

1. List unresolved threads. `gh pr view` does not show resolution state; use GraphQL:
   ```
   gh api graphql -F o=OWNER -F r=REPO -F n=$ARGUMENTS -f query='
     query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
       reviewThreads(first:100){nodes{id isResolved path line comments(first:1){nodes{author{login} body}}}}}}}' \
     --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved | not)'
   ```
2. For each thread decide: real issue or false positive.
   - Real: fix the cause, not the symptom. Do not silence a scanner with an ignore comment when the code can
     be made safe. If the same pattern appears elsewhere in the diff, fix it there too.
   - False positive: say why in the reply, with evidence (the guard, the test that proves it).
3. Push the fixes. Reply on each thread with what changed (commit sha or one sentence), then resolve it:
   `gh api graphql -F t=<thread-id> -f query='mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}'`
4. Re-run step 1: the count must be 0. Bots can add threads after your push; sweep once more when CI settles.
5. Never resolve a thread without a fix or a reasoned reply, and never dismiss a human reviewer's request
   yourself.

Report: threads fixed, threads answered as false positives (one line each), remaining count.
