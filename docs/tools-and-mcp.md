# Tools, permissions, hooks and MCP

## Per-agent tool lists

| Agent | Tools | Denied |
|---|---|---|
| scout (haiku) | Read, Grep, Glob, Bash | Edit, Write, NotebookEdit, WebFetch, WebSearch, Agent |
| rebaser (sonnet) | Read, Grep, Glob, Bash, Edit, Write | WebFetch, WebSearch, Agent |
| fixer (sonnet) | Read, Grep, Glob, Bash, Edit, Write, WebFetch | - |
| implementer (opus) | Read, Grep, Glob, Bash, Edit, Write, WebFetch, WebSearch, Agent | - |
| reviewer (sonnet) | Read, Grep, Glob, Bash | Edit, Write, NotebookEdit, WebSearch, Agent |

On Linux and macOS, Claude Code searches through Bash (`grep`, `find`) and leaves Grep/Glob out of the default
tool set; listing them is harmless. **Bash can still write**: "read-only" agents are read-only by instruction
plus the guard hook, not by sandbox. For a hard guarantee run them with permission rules that deny writes, or in
a sandbox. Plugin-shipped agents ignore `permissionMode`, `hooks` and `mcpServers` in their frontmatter; copy an
agent into `.claude/agents/` if you need those.

## Project permissions (`templates/settings.json`)

Rules are evaluated deny, then ask, then allow.

- **allow** (no prompt churn): git status/diff/log/show/branch/fetch, `gh pr view|list|diff|checks`,
  `gh run list|view`, read-only `octl` subcommands, build/test/lint commands.
- **ask** (outward or shared state): `gh pr merge`, `gh release`, `gh repo`, `gh api -X/--method`, `gh secret`,
  `gh workflow run`, `npm publish`, `docker push`, `git tag`, `octl deploy`, `octl spawn`.
- **deny**: reading `.env` files and `~/.ssh`, `~/.aws`, `~/.config/gh`; force pushes; `git reset --hard origin/*`;
  `docker * prune`; `sudo`.

`claude -p` cannot answer prompts, so an `ask` rule denies the call in headless runs. That is intended for
the outward actions above; agents push branches and open PRs without prompts.

## Hooks

| Hook | Script | Does |
|---|---|---|
| PreToolUse `Bash` | `guard-bash.py` | denies rm -r/-f on variables or outside the project, `pkill -f`/`killall`, `docker * prune`, force push (or `+refspec`) to `main`/`master`/`develop` (`GUARD_PROTECTED_BRANCHES`), and reading `.env`/key files; looks inside `bash -c`, `eval`, `$(...)` and wrappers like `sudo`, `nice`, `timeout` |
| PreToolUse `mcp__.*` | `guard-mcp.py` | returns "ask" for any MCP tool whose name does not start with a read prefix (`get_`, `list_`, `search_`, `read_`, `query`...; `GUARD_MCP_READ_PREFIXES`) |
| SessionStart | `session-status.sh` | injects a 5-line local `octl status --short` (no network) |

PreToolUse decisions never bypass deny or ask rules. The guard is a safety net, not a sandbox: a determined
command can evade pattern checks, so keep the deny rules and human approval for outward actions.

## MCP or CLI?

Every MCP server adds its tool definitions to the context of every turn, and its results arrive unfiltered
(default cap 25,000 tokens per result). A CLI call (`gh`, `psql`) costs nothing until used and its output can
be filtered (`| jq`, `| head`). Prefer the CLI for anything the CLI does well (`gh pr view --json ...`);
use MCP when no CLI exists, or when structured access saves many CLI turns.

`templates/mcp.json` (scaffolded as `.mcp.json.example`, opt-in) contains two least-privilege examples:

- `github`: the GitHub MCP server in read-only mode, token from `GITHUB_MCP_TOKEN` (use a fine-grained,
  read-only token scoped to one repository).
- `scratch-db`: a Postgres MCP server for **scratch** databases only, URL from `SCRATCH_DATABASE_URL`. Point it at
  a read-only role. Never at production.

Values use `${VAR}` expansion; nothing secret is written to the file. Project servers need approval
(`enabledMcpjsonServers` in settings, or the prompt in interactive sessions). The package names in the example
were not run during this release; check them before enabling.

## Token-cheap tool patterns

- Filter every command: `| tail -n 40`, `| grep -n`, `| jq '.[] | {number,title}'`, `| head`.
- Tests: output to a file, print failures only.
- Read with `offset`/`limit`; never cat a large file.
- Put independent tool calls in one turn (they run in parallel).
- Delegate searches to the scout agent (haiku, fresh small context) and use its conclusion.
- One background `gh pr checks N --watch --fail-fast | tail -5`, then act once; never poll in turns.
