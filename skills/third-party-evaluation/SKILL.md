---
name: third-party-evaluation
description: Decide whether to adopt an outside tool, library or framework - verify claims against its code, assess supply chain and security record, measure fit against real pain points, and prefer borrowing one idea over adopting the whole thing. Use when someone asks "should we use X".
---

Read only. Never install, clone-and-run or `npx` the candidate during evaluation.

1. Scope: ask, or infer, which part of the system it would serve (the developer harness or the product).
   The answers differ.
2. What it really does: read the source for each headline feature. Mark each one as implemented, partly
   wired, or claimed only. Check benchmark claims against what they actually measure.
3. Security and supply chain:
   - advisories and CVEs;
   - what it installs or auto-allows (permissions, hooks, MCP tools that run shell commands);
   - postinstall scripts;
   - dependency count and version pinning;
   - telemetry and network calls;
   - where it stores data (plaintext logs of commands and outputs are a secret leak);
   - release cadence and bus factor.
4. Multi-tenant fit (for product use):
   - tenant isolation of its memory and learning state (optional filters and global shared state fail);
   - provider choice and data residency;
   - audit and replay;
   - human approval;
   - air-gapped operation.
5. Fit: go through the team's real problems one by one. Does it help, hurt, or not touch each? Compare the
   cost against the current budget rules.
6. Alternatives: features already available and underused, and the one or two ideas worth rebuilding
   in-house.

Deliverable: a note with a verdict (adopt, borrow, reject), a scoring table, and the reasons with sources
(issue numbers, file:line). For any idea worth borrowing, add a minimal sketch.
