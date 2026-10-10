"""End-to-end dry-run scenario: scaffold a repo, route and brief sample tasks, dry-run a council.
Also lints the kit's own agents, skills and JSON against the fields verified in the Claude Code docs."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import KIT, tmpdir

AGENT_FIELDS = {"name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns", "skills",
                "mcpServers", "hooks", "memory", "background", "omitClaudeMd", "effort", "isolation", "color",
                "initialPrompt", "experimental"}
PLUGIN_AGENT_IGNORED = {"hooks", "mcpServers", "permissionMode"}
SKILL_FIELDS = {"name", "description", "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
                "user-invocable", "allowed-tools", "disallowed-tools", "model", "effort", "context", "agent",
                "background", "hooks", "paths", "shell", "metadata", "license", "compatibility"}
SAMPLE_TASKS = [  # (kind, risk, size, expected agent, expected model)
    ("lookup", "low", "S", "scout", "haiku"),
    ("rebase", "med", "M", "rebaser", "sonnet"),
    ("docs", "low", "L", "fixer", "sonnet"),
    ("change", "med", "S", "fixer", "sonnet"),
    ("change", "high", "M", "implementer", "opus"),
    ("security", "med", "S", "implementer", "opus"),
    ("review", "med", "M", "reviewer", "sonnet"),
    ("ui", "med", "M", "implementer", "opus"),
]


def frontmatter(path):
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path}: no frontmatter"
    return {line.split(":", 1)[0].strip() for line in m.group(1).splitlines() if re.match(r"^[A-Za-z_-]+:", line)}


def sh(args, cwd=None, inp=None):
    r = subprocess.run(args, cwd=cwd, input=inp, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


class LintTest(unittest.TestCase):
    def test_agents(self):
        for f in sorted(os.listdir(os.path.join(KIT, "agents"))):
            keys = frontmatter(os.path.join(KIT, "agents", f))
            self.assertLessEqual(keys, AGENT_FIELDS, f)
            self.assertFalse(keys & PLUGIN_AGENT_IGNORED, f"{f}: field ignored for plugin agents")
            self.assertIn("model", keys, f)

    def test_skills(self):
        for d in sorted(os.listdir(os.path.join(KIT, "skills"))):
            keys = frontmatter(os.path.join(KIT, "skills", d, "SKILL.md"))
            self.assertLessEqual(keys, SKILL_FIELDS, d)
            self.assertIn("description", keys, d)

    def test_json_files_parse(self):
        for rel in (".claude-plugin/plugin.json", "hooks/hooks.json", "templates/settings.json", "templates/mcp.json",
                    "templates/octl.json", "examples/openctem/octl.json", "examples/council-providers.json"):
            with open(os.path.join(KIT, rel)) as fh:
                json.load(fh)

    def test_routed_agents_exist(self):
        octl = os.path.join(KIT, "bin/octl")
        for kind, risk, size, agent, model in SAMPLE_TASKS:
            self.assertTrue(os.path.exists(os.path.join(KIT, "agents", agent + ".md")), agent)

    def test_no_secrets_committed(self):
        pat = re.compile(r"(sk-ant-[A-Za-z0-9]|ghp_[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY)")
        for root, dirs, files in os.walk(KIT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for f in files:
                if f.startswith("test_"):
                    continue  # tests contain fake secrets on purpose
                with open(os.path.join(root, f), errors="ignore") as fh:
                    self.assertIsNone(pat.search(fh.read()), os.path.join(root, f))


class ScenarioTest(unittest.TestCase):
    def test_scaffold_route_brief_council(self):
        repo = tmpdir("kit-scenario-")
        rc, out = sh(["bash", os.path.join(KIT, "init.sh"), repo])
        self.assertEqual(rc, 0, out)
        for rel in (".claude/settings.json", ".claude/bin/octl", ".claude/agents/reviewer.md",
                    ".claude/skills/dispatch/SKILL.md", ".claude/hooks/scripts/guard-bash.py", "CLAUDE.md", "octl.json"):
            self.assertTrue(os.path.exists(os.path.join(repo, rel)), rel)
        self.assertIn("`./.claude/bin/octl status --short`", open(os.path.join(repo, ".claude/skills/dispatch/SKILL.md")).read())
        rc, again = sh(["bash", os.path.join(KIT, "init.sh"), repo])
        self.assertIn("0 written", again)  # idempotent
        octl = [sys.executable, os.path.join(repo, ".claude/bin/octl")]
        for i, (kind, risk, size, agent, model) in enumerate(SAMPLE_TASKS, 1):
            rc, out = sh(octl + ["task", "add", "P2", kind, f"sample {kind}", "--risk", risk, "--size", size], cwd=repo)
            self.assertEqual(rc, 0, out)
            self.assertIn(f"agent={agent} model={model}", out, (kind, risk, size))
        rc, out = sh(octl + ["task", "next"], cwd=repo)
        self.assertIn("4 slot(s) free", out)
        self.assertEqual(out.count("  start "), 4)
        rc, brief = sh(octl + ["brief", "T005"], cwd=repo)
        self.assertTrue(brief.startswith("[agent: implementer  model: opus  effort: xhigh  maxTurns: 60]"), brief)
        self.assertIn(os.path.join(repo, ".claude/BRIEF-common.md"), brief)
        rc, spawn = sh(octl + ["spawn", "T002"], cwd=repo)
        self.assertIn("--agent rebaser --model sonnet", spawn)  # template mode: no plugin prefix
        rc, short = sh(octl + ["status", "--short"], cwd=repo)
        self.assertIn("todo 8", short)
        # SessionStart hook output is valid hook JSON
        env = dict(os.environ, CLAUDE_PROJECT_DIR=repo)
        r = subprocess.run(["bash", os.path.join(repo, ".claude/hooks/scripts/session-status.sh")], env=env,
                           capture_output=True, text=True)
        ctx = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(ctx["hookEventName"], "SessionStart")
        self.assertIn("tasks:", ctx["additionalContext"])
        # council dry run: no model is called
        open(os.path.join(repo, "note.md"), "w").write("Queue choice: A or B. password=supersecret123")
        consult = [sys.executable, os.path.join(repo, ".claude/bin/consult")]
        rc, out = sh(consult + ["Which queue?", "-c", "note.md", "--dry-run"], cwd=repo)
        self.assertEqual(rc, 0, out)
        self.assertIn("3 advisors x 1 round(s)", out)
        rc, out = sh(consult + ["Which queue?", "-c", ".env", "--dry-run"], cwd=repo)
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
