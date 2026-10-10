# Security policy

## Reporting a vulnerability

Please report security issues privately to **security@openctem.io**. Do not open a public issue for a
vulnerability. Include the affected file or command, steps to reproduce, and the impact you expect.
We aim to acknowledge reports within three working days.

## Scope

In scope: the hooks (`hooks/scripts/*`), `bin/octl`, `bin/consult`, `init.sh`, the permission templates and the
agent and skill instructions in this repository - for example a guard bypass that lets a destructive command
through, secrets leaking into transcripts, logs or council payloads, shell injection through configuration, or a
council provider receiving files it should not.

Out of scope: vulnerabilities in Claude Code itself or in third-party CLIs and MCP servers you configure
(report those to their maintainers), and issues that need an already-compromised machine or account.

## Design notes

- The guard hooks are a safety net, not a sandbox. Keep the deny/ask permission rules and human approval for
  outward actions.
- No secrets are stored by the kit. Alerts and council providers read credentials from environment variables
  named in `octl.json`; `octl` reads only the named keys from an env file.
- Configured shell commands (`live.*`) run with the user's privileges; values substituted into them are quoted
  and commit ids are validated.
