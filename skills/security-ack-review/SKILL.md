---
name: security-ack-review
description: Review the security-relevant change on a PR whose security approval label dropped after a push, then re-approve or report a finding - never a blind re-ack. Use when acting as the security-ack reviewer, or when a security gate fails because the approval no longer matches the head.
---

A security gate that carries an approval only across clean base merges drops it whenever sensitive code
changes. The drop is the signal: someone has to read what changed since the last approval.

1. Find the last approved head (the timeline event that added the label, or the gate's comment).
2. Diff from that head to the current one, limited to the paths the gate treats as sensitive.
   - A base merge with no conflicts counts as already reviewed.
   - A base merge with conflicts: review the resolution itself (`git show --remerge-diff <merge>`, or
     redo the merge and diff the trees). Hand-resolved hunks are where regressions hide.
   - Write file-list scripts in bash. zsh does not word-split `$files`, so a filter over an unquoted list
     silently compares against nothing and every check comes back clean.
3. Check the code:
   - authorization on every route, and no role widened (compare the new permission against the old gate,
     and list which built-in roles hold it);
   - tenant isolation: every statement on tenant data filters on the tenant at the top-level WHERE. A
     tenant check inside a subquery does not count, and a lint that accepts it is wrong;
   - injection, SSRF, secrets in code or logs, error details leaking, weakened validation, crypto,
     audit on privileged actions, encrypted columns registered for key rotation.
4. Workflow and CI files:
   - no new or broader permissions or secrets;
   - no pull_request_target or workflow_run that checks out PR code;
   - fork PRs stay on hosted runners;
   - no event text (titles, bodies, branch names) interpolated into `run:`;
   - third-party actions pinned by SHA;
   - no conflict markers.
5. Changes to the approval machinery itself (the gate script, its path list, the label or comment
   handler) go to the owner. A reviewer must not approve a loosening of its own gate.

Clean: add the label and post a short comment saying what was checked.
Any finding: no label. Post the finding with file:line and the fix, and report it.
Non-blocking improvements go in the comment and a follow-up, not as a blocker.

Also report files that are sensitive but outside the gate's path list. The gate kept an old approval for them.
