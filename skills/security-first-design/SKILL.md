---
name: security-first-design
description: Security bar for research, designs and code in a multi-tenant system - threat model, tenant isolation, authorization on every route, abuse-case tests, and a human for anything outward-facing. Use when designing a feature, writing an RFC, adding a route, query, integration or background job, or reviewing such a change.
---

Every change states its threat model and its authorization and tenant-isolation impact, and ships tests for
them. "Security later" items never came back; isolation bugs found in audits were all in code that skipped this.

## Design
- Threat model in a few lines: assets, actors (other tenant, low-privilege member, compromised worker,
  malicious input file), abuse cases, and what stops each.
- Mutual distrust between components: a worker or agent does not trust the server's job blindly (signed jobs,
  local policy), and the server treats every result as hostile input (size limits, schema validation).
- Outbound requests go through an SSRF-safe client (deny private and metadata ranges, re-check after DNS).
- Pick the simplest design that keeps the boundary. Say what you deliberately did not build.

## Code
- **Tenant from the authenticated principal**, never from the body, query or an uploaded file. Every query on
  a tenant table carries `tenant_id = $n`, including updates and deletes.
- **Per-tenant credentials** for every integration; never a shared global client.
- **Gate every new route** with the least-privilege permission; a coverage test should fail on an ungated
  route. Object-level checks are separate from route gates. The UI check is never the boundary.
- **Data scope:** a member with no scope row sees nothing. Never add a fail-open "no row means everything".
- Feature or module toggles are product gates, not security boundaries.
- No secrets in logs, responses, tickets or error messages; generic auth errors (no user enumeration);
  constant-time comparison for tokens; client IP only from a trusted-proxy helper, never a raw header.

## Tests
- Cross-tenant negative: tenant B cannot read, list, update or delete tenant A's object (expect 404, not 403).
- Out-of-scope negative: a member without the permission or data scope is refused.
- Abuse input: oversized, malformed, path traversal, private-IP URLs.

## Needs a human
Agents never do these on their own: anything outward (email, posts, publishing, inviting people), merges into
repositories the owner merges by hand, destructive or irreversible data changes beyond a reviewed migration,
anything needing the owner's credentials or second factor, spending money, opening a service to a network.
