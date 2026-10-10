import contextlib
import io
import json
import os
import unittest
from unittest import mock

from helpers import load, project

octl = load("bin/octl", "octl")


def use(cfg=None):
    d, path = project(cfg)
    octl.CFG.clear()
    octl.CFG.update(octl.load_config(path))
    return d, path


def out(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a, **k)
    return buf.getvalue()


class ConfigTest(unittest.TestCase):
    def test_defaults_and_root(self):
        d, path = project({"repo": "acme/app"})
        cfg = octl.load_config(path)
        self.assertEqual(cfg["root"], d)
        self.assertEqual(cfg["base_branch"], "main")
        self.assertEqual(cfg.path("state_dir"), os.path.join(d, ".octl/state"))

    def test_unknown_key_rejected(self):
        _, path = project({"repo": "acme/app", "repoo": "typo"})
        with self.assertRaises(SystemExit):
            octl.load_config(path)

    def test_bad_repo_and_agents(self):
        for bad in ({"repo": "no-slash"}, {"repo": "a/b; rm -rf /"}, {"repo": "a/b", "max_agents": 0}):
            _, path = project(bad)
            with self.assertRaises(SystemExit):
                octl.load_config(path)

    def test_migrations_need_dir_and_pattern(self):
        _, path = project({"repo": "a/b", "migrations": {"dir": "db"}})
        with self.assertRaises(SystemExit):
            octl.load_config(path)

    def test_transcripts_dir_derivation(self):
        self.assertTrue(octl.transcripts_dir_for("/home/u/my.proj").endswith("/.claude/projects/-home-u-my-proj"))

    def test_find_config_walks_up(self):
        d, path = project()
        sub = os.path.join(d, "a", "b")
        os.makedirs(sub)
        self.assertEqual(octl.find_config([], env={}, cwd=sub), path)
        argv = ["--config", "/x/octl.json", "status"]
        self.assertEqual(octl.find_config(argv, env={}), "/x/octl.json")
        self.assertEqual(argv, ["status"])


class StackOrderTest(unittest.TestCase):
    def test_contained_pr_goes_after(self):
        prs = [{"number": 10, "headRefOid": "c"}, {"number": 11, "headRefOid": "a"}, {"number": 12, "headRefOid": "b"}]
        # c contains b contains a
        rel = {("c", "b"), ("c", "a"), ("b", "a")}
        order, deps = octl.stack_order(prs, lambda x, y: (x, y) in rel)
        self.assertEqual(order, [11, 12, 10])
        self.assertEqual(deps[10], {11, 12})

    def test_independent_by_number_and_cycle_safe(self):
        prs = [{"number": 5, "headRefOid": "x"}, {"number": 3, "headRefOid": "x"}]
        order, _ = octl.stack_order(prs, lambda a, b: True)  # identical heads contain each other
        self.assertEqual(sorted(order), [3, 5])


class MigrationTest(unittest.TestCase):
    def test_next_block_leaves_gap(self):
        self.assertEqual(octl.next_block([137, 120], 2), 140)
        self.assertEqual(octl.next_block([140], 1), 150)
        self.assertEqual(octl.next_block([], 1), 10)
        with self.assertRaises(ValueError):
            octl.next_block([1], 0)

    def test_mig_number_only_in_dir(self):
        use({"repo": "a/b", "migrations": {"dir": "db/migrations", "pattern": r"^(\d+)_.+\.up\.sql$"}})
        self.assertEqual(octl.mig_number("db/migrations/000123_x.up.sql"), 123)
        self.assertIsNone(octl.mig_number("db/migrations/000123_x.down.sql"))
        self.assertIsNone(octl.mig_number("other/000123_x.up.sql"))
        prs = [{"files": [{"path": "db/migrations/000200_a.up.sql"}, {"path": "README.md"}]}]
        self.assertEqual(octl.open_pr_max(prs), 200)

    def test_reserve_uses_everything_in_use(self):
        use({"repo": "a/b", "migrations": {"dir": "db/migrations", "pattern": r"^(\d+)_.+\.up\.sql$"}})
        with mock.patch.object(octl, "base_max", return_value=130), mock.patch.object(octl, "open_pr_max", return_value=145):
            out(octl.cmd_mig, ["reserve", "T001", "2"])
            out(octl.cmd_mig, ["reserve", "T002"])
        nums = [(r[0], r[1]) for r in octl.ledger()]
        self.assertEqual(nums, [("000150", "T001"), ("000151", "T001"), ("000160", "T002")])


class RouteTest(unittest.TestCase):
    def setUp(self):
        use()

    def test_defaults(self):
        r = octl.route
        self.assertEqual(r("lookup")["model"], "haiku")
        self.assertEqual(r("lookup")["agent"], "scout")
        self.assertEqual(r("rebase")["agent"], "rebaser")
        self.assertEqual(r("docs", size="L")["model"], "sonnet")  # no-code kinds never raise
        self.assertEqual(r("change", size="S")["model"], "sonnet")
        self.assertEqual(r("change", risk="high")["model"], "opus")
        self.assertEqual(r("change", risk="high")["effort"], "xhigh")
        self.assertEqual(r("feature")["agent"], "implementer")
        self.assertEqual(r("review", risk="low")["agent"], "reviewer")
        self.assertEqual(r("security", size="S")["model"], "opus")

    def test_escalation_after_two_failures(self):
        self.assertEqual(octl.route("ci", fails=1)["model"], "sonnet")
        esc = octl.route("ci", fails=2)
        self.assertEqual((esc["model"], esc["agent"]), ("opus", "implementer"))
        self.assertEqual(octl.route("lookup", fails=2)["agent"], "fixer")
        self.assertEqual(octl.route("feature", fails=6)["model"], "opus")  # capped

    def test_budgets(self):
        self.assertEqual(octl.route("change", size="S")["max_turns"], 30)
        self.assertEqual(octl.route("lookup", size="L")["max_turns"], 20)
        self.assertEqual(octl.route("lookup", size="L")["budget_m"], 15)

    def test_invalid_inputs(self):
        with self.assertRaises(SystemExit):
            octl.route("change", risk="extreme")
        with self.assertRaises(SystemExit):
            octl.route("change", size="XL")

    def test_config_override(self):
        use({"repo": "a/b", "routing": {"kind_tier": {"docs": "haiku"}, "budget_m": {"S": 5}}})
        r = octl.route("docs", size="S")
        self.assertEqual((r["model"], r["budget_m"]), ("haiku", 5))
        self.assertEqual(octl.route("change")["budget_m"], 40)  # other sizes keep defaults


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.d, _ = use({"repo": "a/b", "max_agents": 2})

    def test_add_start_cap_and_stages(self):
        out(octl.cmd_task, ["add", "P1", "feature", "Add", "SSO", "--risk", "high"])
        out(octl.cmd_task, ["add", "P2", "docs", "Fix", "typo", "--size", "S"])
        out(octl.cmd_task, ["add", "P3", "change", "Small"])
        t = {r["id"]: r for r in octl.tasks()}
        self.assertEqual(t["T001"]["title"], "Add SSO")
        self.assertEqual((t["T001"]["model"], t["T001"]["stage"]), ("opus", "intake"))
        out(octl.cmd_task, ["start", "T001", "a1"])
        out(octl.cmd_task, ["start", "T002", "a2"])
        with self.assertRaises(SystemExit):  # max_agents 2
            octl.cmd_task(["start", "T003", "a3"])
        t = {r["id"]: r for r in octl.tasks()}
        self.assertEqual(t["T001"]["stage"], "plan")       # opus tasks plan first
        self.assertEqual(t["T002"]["stage"], "implement")  # others skip plan

    def test_gates(self):
        out(octl.cmd_task, ["add", "P1", "feature", "X"])
        out(octl.cmd_task, ["start", "T001", "a"])
        with self.assertRaises(SystemExit) as e:
            octl.cmd_task(["advance", "T001"])
        self.assertIn("design note", str(e.exception))
        os.makedirs(os.path.dirname(octl.note_path("T001")), exist_ok=True)
        open(octl.note_path("T001"), "w").write("note")
        out(octl.cmd_task, ["advance", "T001"])
        with self.assertRaises(SystemExit) as e:  # implement -> verify needs a PR
            octl.cmd_task(["advance", "T001"])
        self.assertIn("no PR", str(e.exception))
        out(octl.cmd_task, ["pr", "T001", "42"])
        out(octl.cmd_task, ["advance", "T001"])  # verify
        out(octl.cmd_task, ["advance", "T001"])  # review
        out(octl.cmd_task, ["advance", "T001"])  # ci
        with mock.patch.object(octl, "gh_json", return_value={"mergeStateStatus": "BLOCKED", "isDraft": False}):
            with self.assertRaises(SystemExit) as e:
                octl.cmd_task(["advance", "T001"])
        self.assertIn("BLOCKED", str(e.exception))
        with mock.patch.object(octl, "gh_json", return_value={"mergeStateStatus": "CLEAN", "isDraft": False}), \
                mock.patch.object(octl, "unresolved_threads", return_value=1):
            with self.assertRaises(SystemExit) as e:
                octl.cmd_task(["advance", "T001"])
        self.assertIn("unresolved", str(e.exception))
        with mock.patch.object(octl, "gh_json", return_value={"mergeStateStatus": "CLEAN", "isDraft": False}), \
                mock.patch.object(octl, "unresolved_threads", return_value=0):
            out(octl.cmd_task, ["advance", "T001"])
        self.assertEqual(octl.tasks()[0]["stage"], "queue")
        with mock.patch.object(octl, "gh_json", return_value={"state": "MERGED"}):
            out(octl.cmd_task, ["advance", "T001"])  # no live config: deploy skipped
        self.assertEqual(octl.tasks()[0]["stage"], "handoff")
        out(octl.cmd_task, ["advance", "T001"])
        self.assertEqual((octl.tasks()[0]["stage"], octl.tasks()[0]["status"]), ("done", "done"))

    def test_fail_escalates(self):
        out(octl.cmd_task, ["add", "P1", "rebase", "Merge base into #9"])
        out(octl.cmd_task, ["fail", "T001", "conflict"])
        self.assertEqual(octl.tasks()[0]["model"], "sonnet")
        msg = out(octl.cmd_task, ["fail", "T001", "again"])
        self.assertIn("escalated sonnet -> opus", msg)
        self.assertEqual(octl.tasks()[0]["agent"], "implementer")
        self.assertEqual(octl.tasks()[0]["status"], "todo")

    def test_tabs_in_title_cannot_break_columns(self):
        out(octl.cmd_task, ["add", "P1", "docs", "a\tb\nc"])
        self.assertEqual(octl.tasks()[0]["title"], "a b c")

    def test_brief_contains_routing_and_stop_rules(self):
        out(octl.cmd_task, ["add", "P1", "feature", "X", "--risk", "high"])
        b = out(octl.cmd_brief, "T001")
        self.assertTrue(b.startswith("[agent: implementer  model: opus  effort: xhigh"))
        self.assertIn("Stop and report", b)
        self.assertIn("design note", b)

    def test_spawn_prints_command(self):
        out(octl.cmd_task, ["add", "P1", "ci", "Fix lint on #4"])
        s = out(octl.cmd_spawn, ["T001"])
        self.assertIn("--agent orchestrator-kit:rebaser --model sonnet --effort medium", s)
        self.assertEqual(octl.tasks()[0]["status"], "todo")  # printing does not start anything


class PortsTest(unittest.TestCase):
    def test_pick_skips_taken_and_busy(self):
        got = octl.pick_ports(2, 100, 110, {100}, free_fn=lambda p: p != 101)
        self.assertEqual(got, [102, 103])
        with self.assertRaises(SystemExit):
            octl.pick_ports(5, 1, 3, set(), free_fn=lambda p: True)

    def test_reserve_and_release(self):
        use({"repo": "a/b", "ports": {"min": 40100, "max": 40199}})
        with mock.patch.object(octl, "port_free", return_value=True):
            out(octl.cmd_port, ["reserve", "T001", "2"])
            out(octl.cmd_port, ["reserve", "T002", "1"])
        self.assertEqual([r[0] for r in octl.port_ledger()], ["40100", "40101", "40102"])
        out(octl.cmd_release, "T001")
        self.assertEqual([r[1] for r in octl.port_ledger()], ["T002"])


class TokensTest(unittest.TestCase):
    def test_usage_dedup_and_task_attribution(self):
        d, _ = use({"repo": "a/b", "ctx_warn": 1000})
        tdir = os.path.join(d, "transcripts")
        os.makedirs(os.path.join(tdir, "sess", "subagents"))
        now = octl.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        u = {"input_tokens": 10, "cache_read_input_tokens": 3_000_000, "cache_creation_input_tokens": 5, "output_tokens": 7}
        lines = [{"type": "user", "message": {"role": "user", "content": "[agent: x] Task T007 (ci): Fix"}},
                 {"type": "assistant", "timestamp": now, "message": {"id": "m1", "usage": u}},
                 {"type": "assistant", "timestamp": now, "message": {"id": "m1", "usage": u}},  # duplicate
                 {"type": "assistant", "timestamp": now, "message": {"id": "m2", "usage": u}},
                 {"type": "assistant", "timestamp": "2000-01-01T00:00:00Z", "message": {"id": "old", "usage": u}}]
        p = os.path.join(tdir, "sess", "subagents", "agent-1.jsonl")
        with open(p, "w") as fh:
            fh.write("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
        turns, c, ctx = octl.transcript_usage(p, octl.now().timestamp() - 3600)
        self.assertEqual((turns, c["cache_read_input_tokens"], ctx), (2, 6_000_000, 3_000_015))
        self.assertEqual(octl.transcript_task(p), "T007")
        rows, _ = octl.token_rows(1, tdir)
        self.assertEqual(octl.task_usage(rows), {"T007": (6_000_000, 2, 1)})
        board = [{"id": "T007", "budget_m": "5"}]
        self.assertEqual(octl.over_budget(rows, board), [("T007", 6.0, 5.0)])


class AlertsTest(unittest.TestCase):
    def test_diff_alerts(self):
        self.assertEqual(octl.diff_alerts({"a": "x"}, {"a": "x", "b": "y"}), ["y"])
        self.assertEqual(octl.diff_alerts({"a": "x"}, {}), ["resolved: x"])
        self.assertEqual(octl.diff_alerts({"a": "x"}, {"a": "z"}), ["z"])

    def test_env_file_reads_only_named_keys(self):
        d, _ = use()
        p = os.path.join(d, ".env")
        open(p, "w").write("A=1\nSECRET=nope\n# B=2\nC='3'\n")
        self.assertEqual(octl.read_env_file(p, ["A", "C", "B"]), {"A": "1", "C": "3"})


class DeployTest(unittest.TestCase):
    def test_apply_requires_rehearsal_of_same_commit(self):
        use({"repo": "a/b", "live": {"checkout": ".", "rehearse": "true", "apply": "true", "version": "echo 5"}})
        sha = "a" * 40
        with mock.patch.object(octl, "run", return_value=sha), mock.patch.object(octl, "base_ci", return_value=("green", "a" * 9)):
            with self.assertRaises(SystemExit) as e:
                octl.cmd_deploy(["apply", sha])
            self.assertIn("rehearse", str(e.exception))

    def test_shell_substitution_is_quoted(self):
        use()
        rc, outp = octl.run_shell("echo {sha}", sha="x; echo injected")
        self.assertEqual(outp, "x; echo injected")


if __name__ == "__main__":
    unittest.main()
