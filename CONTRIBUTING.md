# Contributing

Thanks for helping. Keep changes small and focused; one concern per pull request.

## Ground rules

- **Stdlib only.** `bin/octl`, `bin/consult`, the hooks and the status line use Python 3.10+ standard library
  and bash. No package installs.
- **Verify Claude Code fields.** Use only settings, hook, agent, skill and plugin fields that are documented at
  https://code.claude.com/docs or confirmed with the installed CLI (`claude --help`, `claude plugin validate`).
  When unsure, leave the feature out and note it in the README "Not included" list.
- **Security first.** Every change states its threat model. Hooks fail open only for input they cannot parse;
  add a test case for every guard rule (denied and allowed).
- **Token cost matters.** Skills and agent prompts load into context: keep them short and imperative.
  Check the always-on cost with `claude --plugin-dir . plugin details orchestrator-kit`.
- No secrets, personal data or internal hostnames in examples (the OpenCTEM example is the documented exception).

## Before opening a pull request

```bash
python3 -m unittest discover -s tests -p "test_*.py"
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/marketplace.json
bash -n init.sh hooks/scripts/session-status.sh
```

Pull requests target `main`. A maintainer merges. By contributing you agree that your contribution is
licensed under the Apache License 2.0 (see `LICENSE`).
