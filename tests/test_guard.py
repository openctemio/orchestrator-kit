import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import KIT, tmpdir, load

guard = load("hooks/scripts/guard-bash.py", "guard_bash")
mcp = os.path.join(KIT, "hooks/scripts/guard-mcp.py")


class GuardBashTest(unittest.TestCase):
    def setUp(self):
        self.cwd = tmpdir("guard-")
        self.roots = [os.path.realpath(self.cwd)]

    def why(self, cmd):
        return guard.check_command(cmd, self.cwd, self.roots)

    def test_denied(self):
        cases = [
            "rm -rf $DIR", "rm -rf \"${WORK}/x\"", "rm -rf /", "rm -rf ~", "rm -fr /etc/x", "rm -r ../outside",
            "sudo rm -rf /var/lib", "nice -n 15 rm -rf /opt/x", "bash -c 'rm -rf $HOME/x'", "echo ok && rm -rf /tmp/../etc",
            "pkill -f server", "pkill -9f node", "killall node",
            "docker system prune -af", "docker volume prune", "docker image prune -a", "docker container prune -f",
            "git push --force origin main", "git push -f origin develop", "git push origin +main",
            "git push --force-with-lease origin HEAD:main", "git -C /x push -f origin master",
            "cat .env", "grep TOKEN ./config/.env.production", "source .env", "head -5 secrets/id_rsa",
            "python3 -c 'print(1)' < .env", "echo $(cat .env)",
        ]
        for c in cases:
            with self.subTest(c=c):
                self.assertIsNotNone(self.why(c), c)

    def test_allowed(self):
        cases = [
            "rm -rf ./build", "rm -rf build node_modules", "rm file.txt", "rm -f ./tmp.log",
            "pkill -P 1234", "kill 1234", "docker rm -f t001-pg", "docker ps",
            "git push origin feat/x", "git push -u origin HEAD:refs/heads/feat/y", "git push --force origin feat/x",
            "cat .env.example", "cat README.md", "grep -n foo src/app.go", "ls -la", "go test ./...",
            "echo 'rm -rf / is dangerous'",
        ]
        for c in cases:
            with self.subTest(c=c):
                self.assertIsNone(self.why(c), c)

    def test_force_push_current_protected_branch(self):
        subprocess.run(["git", "init", "-q", "-b", "main", self.cwd], check=True)
        self.assertIsNotNone(self.why("git push --force"))
        self.assertIsNotNone(self.why("git push -f origin HEAD"))

    def test_hook_protocol(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "killall x"}, "cwd": self.cwd}
        r = subprocess.run([sys.executable, os.path.join(KIT, "hooks/scripts/guard-bash.py")],
                           input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual((out["hookEventName"], out["permissionDecision"]), ("PreToolUse", "deny"))
        ok = subprocess.run([sys.executable, os.path.join(KIT, "hooks/scripts/guard-bash.py")],
                            input=json.dumps({**payload, "tool_input": {"command": "ls"}}), capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout), (0, ""))
        bad = subprocess.run([sys.executable, os.path.join(KIT, "hooks/scripts/guard-bash.py")],
                             input="not json", capture_output=True, text=True)
        self.assertEqual(bad.returncode, 0)

    def test_protected_branches_env(self):
        os.environ["GUARD_PROTECTED_BRANCHES"] = "release"
        try:
            self.assertIsNotNone(self.why("git push -f origin release"))
            self.assertIsNone(self.why("git push -f origin main"))
        finally:
            del os.environ["GUARD_PROTECTED_BRANCHES"]


class GuardMcpTest(unittest.TestCase):
    def decide(self, tool):
        r = subprocess.run([sys.executable, mcp], input=json.dumps({"tool_name": tool}), capture_output=True, text=True)
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout else None

    def test_reads_pass_writes_ask(self):
        self.assertIsNone(self.decide("mcp__github__get_pull_request"))
        self.assertIsNone(self.decide("mcp__github__list_issues"))
        self.assertIsNone(self.decide("mcp__scratch-db__query"))
        self.assertEqual(self.decide("mcp__github__merge_pull_request"), "ask")
        self.assertEqual(self.decide("mcp__github__create_issue"), "ask")
        self.assertIsNone(self.decide("Bash"))


class StatuslineTest(unittest.TestCase):
    def test_render(self):
        sl = load("statusline/statusline.py", "statusline")
        self.assertEqual(sl.render({"model": {"display_name": "Opus"},
                                    "context_window": {"total_input_tokens": 120000, "used_percentage": 12}}, 400000),
                         "[Opus] ctx 120k (12%)")
        self.assertIn("BIG CONTEXT", sl.render({"context_window": {"total_input_tokens": 500000}}, 400000))
        self.assertIn("BIG CONTEXT", sl.render({"context_window": {"total_input_tokens": 1, "used_percentage": 85}}, 400000))
        self.assertEqual(sl.render({}, 400000), "[?] ctx 0k")


if __name__ == "__main__":
    unittest.main()
