import contextlib
import io
import json
import os
import unittest
from unittest import mock

from helpers import load, project

consult = load("bin/consult", "consult")

GOOD = {"position": "Use A", "reasons": ["simple"], "risks": ["lock-in"], "change_my_mind": "benchmarks",
        "confidence": 0.7}


def cfg_for(council=None):
    d, path = project({"repo": "a/b", "council": council or {}})
    return d, consult.load_config(path)


class Proc:
    def __init__(self, stdout, rc=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, rc, stderr


class SchemaTest(unittest.TestCase):
    def test_valid_and_invalid(self):
        self.assertEqual(consult.validate(GOOD, consult.ADVICE_SCHEMA), [])
        bad = dict(GOOD, confidence=1.5, extra=1)
        del bad["risks"]
        errs = consult.validate(bad, consult.ADVICE_SCHEMA)
        self.assertTrue(any("missing risks" in e for e in errs))
        self.assertTrue(any("above 1" in e for e in errs))
        self.assertTrue(any("unexpected extra" in e for e in errs))
        self.assertTrue(consult.validate(dict(GOOD, confidence=True), consult.ADVICE_SCHEMA))
        self.assertTrue(consult.validate(dict(GOOD, reasons=[1]), consult.ADVICE_SCHEMA))

    def test_extract_json(self):
        self.assertEqual(consult.extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(consult.extract_json('Sure! {"a": 2} hope that helps'), {"a": 2})


class EgressTest(unittest.TestCase):
    def test_redaction(self):
        text = ("key = sk-ant-api03-abcdefghijklmnopqrstuvwxyz\nAWS AKIAABCDEFGHIJKLMNOP\n"
                "DB_PASSWORD=hunter2hunter2\npostgres://user:pa55word@db/x\n"
                "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----\nghp_" + "a" * 36)
        red, counts = consult.redact(text)
        for secret in ("sk-ant-api03", "AKIAABCDEFGHIJKLMNOP", "hunter2", "pa55word", "MIIabc", "ghp_aaaa"):
            self.assertNotIn(secret, red)
        self.assertIn("DB_PASSWORD=[REDACTED]", red)
        self.assertGreaterEqual(sum(counts.values()), 6)

    def test_context_blocks_secret_files_outside_and_oversize(self):
        d, cfg = cfg_for({"max_file_kb": 1})
        ok = os.path.join(d, "design.md")
        open(ok, "w").write("token: ghp_" + "b" * 36)
        ctx = consult.load_context([ok], cfg)
        self.assertEqual(ctx[0]["path"], "design.md")
        self.assertNotIn("ghp_", ctx[0]["body"])
        for name in (".env", "prod.pem", "id_rsa", ".env.local"):
            p = os.path.join(d, name)
            open(p, "w").write("x")
            with self.assertRaises(consult.Refused):
                consult.load_context([p], cfg)
        big = os.path.join(d, "big.txt")
        open(big, "w").write("x" * 2048)
        with self.assertRaises(consult.Refused):
            consult.load_context([big], cfg)
        with self.assertRaises(consult.Refused):
            consult.load_context(["/etc/hostname"], cfg)


class ProviderTest(unittest.TestCase):
    def test_selection_and_policy(self):
        _, cfg = cfg_for({"providers": {
            "local": {"type": "openai-compatible", "enabled": True, "base_url": "http://127.0.0.1:8000/v1"},
            "remote": {"type": "openai-compatible", "enabled": True, "base_url": "https://api.example.com/v1",
                       "key_env": "REMOTE_KEY_FOR_TEST"},
            "remote-ok": {"type": "openai-compatible", "enabled": True, "allow_external": True,
                          "base_url": "https://api.example.com/v1"},
            "plain-http": {"type": "openai-compatible", "enabled": True, "allow_external": True,
                           "base_url": "http://api.example.com/v1"},
            "cli": {"type": "agent-cli", "enabled": True, "cmd": ["x"]}}})
        self.assertEqual(consult.check_provider("claude-cli", cfg, False)["type"], "claude-cli")
        self.assertFalse(consult.is_external(cfg["providers"]["local"]))
        with self.assertRaises(consult.Refused):  # disabled by default
            consult.check_provider("anthropic-api", cfg, False)
        with self.assertRaises(consult.Refused):  # external without opt-in
            consult.check_provider("remote", cfg, True)
        with self.assertRaises(consult.Refused):  # config opt-in but no flag
            consult.check_provider("remote-ok", cfg, False)
        self.assertTrue(consult.check_provider("remote-ok", cfg, True))
        with self.assertRaises(consult.Refused):  # external must be https
            consult.check_provider("plain-http", cfg, True)
        with self.assertRaises(consult.Refused):  # agent CLIs are external by default
            consult.check_provider("cli", cfg, True)
        with self.assertRaises(consult.Refused):
            consult.check_provider("missing", cfg, False)

    def test_unknown_type_rejected(self):
        _, path = project({"council": {"providers": {"x": {"type": "telepathy"}}}})
        with self.assertRaises(SystemExit):
            consult.load_config(path)

    def test_cli_command_is_read_only_and_capped(self):
        _, cfg = cfg_for()
        cmd = consult.cli_command(cfg["providers"]["claude-cli"], "sonnet", "medium", consult.ADVICE_SCHEMA)
        self.assertIn("--no-session-persistence", cmd)
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "0.5")
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("Bash", cmd[cmd.index("--disallowedTools") + 1])
        self.assertNotIn("--allowedTools", cmd)

    def test_claude_cli_parses_structured_output(self):
        _, cfg = cfg_for()
        calls = []

        def runner(cmd, **kw):
            calls.append(kw)
            return Proc(json.dumps({"structured_output": GOOD, "total_cost_usd": 0.12}))
        data, cost = consult.run_claude_cli(cfg["providers"]["claude-cli"], "opus", "high", "PROMPT", consult.ADVICE_SCHEMA, runner)
        self.assertEqual((data, cost), (GOOD, 0.12))
        self.assertEqual(calls[0]["input"], "PROMPT")  # prompt via stdin, not argv

    def test_anthropic_api_request_shape_and_key_handling(self):
        _, cfg = cfg_for({"providers": {"anthropic-api": {"enabled": True}}})
        seen = {}

        def post(url, body, headers, timeout):
            seen.update(url=url, body=body, headers=headers)
            return {"content": [{"type": "text", "text": json.dumps(GOOD)}], "stop_reason": "end_turn"}
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            data, _ = consult.run_anthropic_api(cfg["providers"]["anthropic-api"], "sonnet", "low", "P",
                                                consult.ADVICE_SCHEMA, post)
        self.assertEqual(data, GOOD)
        self.assertTrue(seen["url"].endswith("/v1/messages"))
        self.assertEqual(seen["body"]["model"], "claude-sonnet-5-5")
        self.assertEqual(seen["body"]["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(seen["headers"]["anthropic-version"], "2023-06-01")
        self.assertNotIn("test-key", json.dumps(seen["body"]))

    def test_agent_cli_sandbox_env_and_unstructured(self):
        d, cfg = cfg_for()
        p = {"type": "agent-cli", "cmd": ["fake", "--model", "{model}", "{prompt}"], "prompt_via": "argv",
             "env_keep": ["FAKE_KEY"], "output": "text"}
        open(os.path.join(d, "a.md"), "w").write("hello")
        ctx = consult.load_context([os.path.join(d, "a.md")], cfg)
        seen = {}

        def runner(cmd, **kw):
            seen.update(cmd=cmd, **kw)
            seen["files"] = os.listdir(kw["cwd"])
            seen["writable"] = os.access(kw["cwd"], os.W_OK)
            return Proc("Here you go:\n```json\n" + json.dumps(GOOD) + "\n```")
        with mock.patch.dict(os.environ, {"FAKE_KEY": "k", "OTHER_SECRET": "s"}):
            data, _ = consult.run_agent_cli(p, "sonnet", "medium", "PROMPT", consult.ADVICE_SCHEMA, runner, ctx)
        self.assertEqual(data, GOOD)
        self.assertEqual(seen["files"], ["a.md"])
        self.assertFalse(seen["writable"])
        self.assertIn("FAKE_KEY", seen["env"])
        self.assertNotIn("OTHER_SECRET", seen["env"])
        self.assertFalse(os.path.exists(seen["cwd"]))  # sandbox removed
        self.assertEqual(seen["cmd"][:3], ["fake", "--model", "sonnet"])
        with self.assertRaises(consult.Unstructured) as u:
            consult.run_agent_cli(p, "sonnet", "medium", "P", consult.ADVICE_SCHEMA, lambda c, **k: Proc("I think A."), ctx)
        self.assertEqual(u.exception.raw, "I think A.")


class CouncilTest(unittest.TestCase):
    def test_budget_enforced_before_any_call(self):
        _, cfg = cfg_for({"max_council_usd": 1.0})
        with mock.patch.object(consult, "ask") as ask:
            with self.assertRaises(consult.Refused):
                consult.run_council("Q?", [], cfg, rounds=1, out=lambda *_: None)  # 3 x 0.5 > 1.0
            ask.assert_not_called()

    def test_high_risk_uses_five_advisors_and_dry_run_calls_nothing(self):
        _, cfg = cfg_for({"max_council_usd": 10})
        lines = []
        with mock.patch.object(consult, "ask") as ask:
            consult.run_council("Q?", [], cfg, risk="high", dry_run=True, out=lines.append)
            ask.assert_not_called()
        self.assertIn("5 advisors x 1 round(s)", lines[0])
        self.assertEqual(len(lines), 6)
        self.assertIn("claude -p --model opus --effort high", "\n".join(lines))

    def test_two_rounds_blind_then_anonymised_and_saved(self):
        d, cfg = cfg_for({"max_council_usd": 10})
        prompts = []

        def fake_ask(p, model, effort, prompt, schema, context=()):
            prompts.append(prompt)
            if "Combine these" in prompt:
                return {"agreement": ["A"], "disagreements": [{"point": "x", "strongest_for": "y",
                                                               "strongest_against": "z"}],
                        "recommendation": "Do A", "open_questions": []}, 0.1
            if "security reviewer" in prompt:
                raise consult.Unstructured("free text answer")
            return GOOD, 0.05
        with mock.patch.object(consult, "ask", side_effect=fake_ask):
            rec = consult.run_council("Pick a queue?", [], cfg, rounds=2, synth=True, out=lambda *_: None)
        r1 = [p for p in prompts[:3]]
        self.assertTrue(all("ADVISOR A" not in p for p in r1))         # round 1 is blind
        self.assertTrue(any("ADVISOR A" in p for p in prompts[3:6]))    # round 2 sees others
        self.assertTrue(all("architect" not in p.split("ADVISOR A")[-1] for p in prompts[3:6] if "ADVISOR A" in p))
        self.assertEqual(rec["synthesis"]["recommendation"], "Do A")
        self.assertEqual(sum(1 for r in rec["round1"] if "unstructured" in r), 1)
        out_dir = os.path.join(d, ".claude/council")
        md = [f for f in os.listdir(out_dir) if f.endswith(".md")]
        self.assertEqual(len(md), 1)
        body = open(os.path.join(out_dir, md[0])).read()
        self.assertIn("Recommendation: Do A", body)
        self.assertIn("UNSTRUCTURED", body)
        audit = open(os.path.join(out_dir, "audit.log")).read().splitlines()
        self.assertEqual(len(audit), 6)
        self.assertTrue(any("\tunstructured" in a for a in audit))

    def test_main_refuses_cleanly(self):
        d, path = project({"council": {"max_council_usd": 0.1}})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit) as e:
            consult.main(["Q?", "--config", path])
        self.assertIn("consult refused", str(e.exception))


if __name__ == "__main__":
    unittest.main()
