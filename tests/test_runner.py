#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The protocol's edges, the grading, the report and the command line.

Each misbehaviour an adapter can show is played by a small fake written to
a temporary directory: silence past the timeout, a wrapper whose child
outlives it, output that is not JSON, a refusal to support an operation, a
crash, an answer outside the vocabulary, a reliance boolean that disagrees
with its conclusion, two builds that differ, a build that alters what it
was given. Every one of them must come out as the result PROTOCOL.md says,
and none of them may come out as PASS.

Run: python3 tests/test_runner.py
"""

import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    cases as catalogue, report, runner, spec as specs)
from arcs_conformance.cases import Case  # noqa: E402

FAKE = r'''
import json, sys, time
CHILD = ("import os, signal, sys, time; "
         "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
         "fh = open(sys.argv[1], 'w'); fh.write(str(os.getpid())); "
         "fh.close(); time.sleep(30)")
mode = sys.argv[1]
request = json.loads(sys.stdin.read())
if mode == "sleep":
    time.sleep(30)
elif mode == "garbage":
    sys.stdout.write("this is not json")
elif mode == "array":
    sys.stdout.write("[]")
elif mode == "unsupported":
    sys.exit(3)
elif mode == "crash":
    sys.stderr.write("Traceback: something broke\n")
    sys.exit(1)
elif mode == "echo":
    sys.stdout.write(json.dumps({"seen": request}))
elif mode == "clocked-build":
    sys.stdout.write(json.dumps({"document": json.dumps(
        {"record_id": "AHD-x", "built": time.time()})}))
elif mode in ("wrapper", "escaping-wrapper"):
    # A launcher whose child holds standard output open, as a shell or npm
    # wrapper around a real verifier would. The child ignores SIGTERM, as
    # a verifier busy in native code can, so only SIGKILL stops it; it
    # records its pid once it is deaf to SIGTERM.
    import subprocess
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, sys.argv[2]],
        start_new_session=(mode == "escaping-wrapper"))
    child.wait()
    sys.stdout.write("{}")
else:
    sys.stdout.write(sys.argv[2])
'''


def _gone(pid, within=5.0):
    """True once no process `pid` exists, waiting up to `within` seconds."""
    deadline = time.time() + within
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.05)
    return False


def _read_pid(path, within=5.0):
    deadline = time.time() + within
    while time.time() < deadline:
        try:
            with open(path) as fh:
                text = fh.read().strip()
            if text:
                return int(text)
        except (IOError, OSError, ValueError):
            pass
        time.sleep(0.05)
    raise AssertionError("the fake wrapper never recorded its child")


def verify_case(expect=("current",)):
    case = Case("c10-fake", "C10", "§11", "must", "verify_record",
                {"document": "{}", "anchor": "{}",
                 "at": "2026-10-01T00:00:00Z"},
                {"conclusion": list(expect)}, "a fake case")
    case.vocabulary = specs.load().conclusions + ("refused",)
    return case


class Fakes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.fake = os.path.join(cls.tmp, "fake_adapter.py")
        with io.open(cls.fake, "w", encoding="utf-8") as fh:
            fh.write(FAKE)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def run_fake(self, case, mode, answer=None, timeout=10.0):
        argv = [sys.executable, self.fake, mode]
        if isinstance(answer, str):
            argv.append(answer)
        elif answer is not None:
            argv.append(json.dumps(answer))
        return runner.run_case(argv, case, timeout)

    def test_silence_past_the_timeout_is_an_error(self):
        outcome = self.run_fake(verify_case(), "sleep", timeout=0.5)
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertIn("no answer within", outcome.detail)

    @unittest.skipUnless(os.name == "posix", "process groups are POSIX")
    def test_a_timeout_kills_the_wrappers_child_too(self):
        # Killing only the wrapper leaves its child holding the pipes, and
        # a child that ignores SIGTERM outlives any signal but SIGKILL.
        pidfile = os.path.join(self.tmp, "child.pid")
        outcome = self.run_fake(verify_case(), "wrapper", pidfile,
                                timeout=2.0)
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertIn("no answer within", outcome.detail)
        child = _read_pid(pidfile)
        try:
            self.assertTrue(_gone(child), "the adapter's child outlived it")
        finally:
            try:
                os.kill(child, signal.SIGKILL)
            except OSError:
                pass

    @unittest.skipUnless(os.name == "posix", "process groups are POSIX")
    def test_a_child_that_escapes_the_group_is_not_waited_for(self):
        # A child in a session of its own survives the group kill and holds
        # the pipes; the suite gives up on it after its grace period.
        pidfile = os.path.join(self.tmp, "escaped.pid")
        grace = runner._GRACE
        runner._GRACE = 0.5
        started = time.time()
        try:
            outcome = self.run_fake(verify_case(), "escaping-wrapper",
                                    pidfile, timeout=2.0)
        finally:
            runner._GRACE = grace
            try:
                os.kill(_read_pid(pidfile), signal.SIGKILL)
            except OSError:
                pass
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertLess(time.time() - started, 10.0)

    def test_output_that_is_not_json_is_an_error(self):
        for mode in ("garbage", "array"):
            outcome = self.run_fake(verify_case(), mode)
            self.assertEqual(outcome.result, runner.ERROR, mode)
            self.assertIn("not one JSON object", outcome.detail)

    def test_unsupported_is_an_error_not_a_pass(self):
        outcome = self.run_fake(verify_case(), "unsupported")
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertIn("does not support verify_record", outcome.detail)

    def test_a_crash_is_an_error_and_keeps_stderr(self):
        outcome = self.run_fake(verify_case(), "crash")
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertIn("exit status 1", outcome.detail)
        self.assertIn("something broke", outcome.stderr)

    def test_a_command_that_does_not_exist_is_an_error(self):
        outcome = runner.run_case([os.path.join(self.tmp, "absent")],
                                  verify_case(), 5)
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertIn("did not start", outcome.detail)

    def test_the_request_envelope(self):
        case = verify_case()
        outcome = self.run_fake(case, "echo")
        # The echo is not a verify answer, so the case is an ERROR; what it
        # echoed is the request exactly as PROTOCOL.md describes it.
        self.assertEqual(outcome.result, runner.ERROR)
        seen = outcome.responses[0]["seen"]
        self.assertEqual(seen["protocol"], runner.PROTOCOL)
        self.assertEqual(seen["op"], "verify_record")
        self.assertEqual(seen["case"], case.id)
        self.assertEqual(seen["at"], "2026-10-01T00:00:00Z")

    def test_a_conclusion_outside_the_vocabulary_fails(self):
        outcome = self.run_fake(verify_case(), "answer",
                                {"conclusion": "valid", "relied": True})
        self.assertEqual(outcome.result, runner.FAIL)
        self.assertIn("none of the section 11 conclusions", outcome.detail)

    def test_every_boolean_on_every_conclusion_is_charged_to_c12(self):
        # Every answer in the vocabulary, `refused` among them, with both
        # booleans: an exemption for any one conclusion would let a verifier
        # tell a caller who reads only the boolean to rely on it.
        vocabulary = verify_case().vocabulary
        self.assertIn(catalogue.REFUSED, vocabulary)
        for conclusion in vocabulary:
            for relied in (True, False):
                wrong = relied != (conclusion == "current")
                outcome = self.run_fake(verify_case([conclusion]), "answer",
                                        {"conclusion": conclusion,
                                         "relied": relied})
                label = "%s with relied %s" % (conclusion, relied)
                # The conclusion is the one the clause allows, so the case
                # passes; the boolean is judged apart and charged to C12.
                self.assertEqual(outcome.result, runner.PASS, label)
                self.assertEqual(
                    [(c.criterion, c.result) for c in outcome.charges],
                    [("C12", runner.FAIL if wrong else runner.PASS)], label)
                if wrong:
                    self.assertIn("true for current and nothing else",
                                  outcome.charges[0].detail)

    def test_a_wrong_conclusion_with_a_right_boolean_is_the_cases(self):
        outcome = self.run_fake(verify_case(["withdrawn"]), "answer",
                                {"conclusion": "current", "relied": True})
        self.assertEqual(outcome.result, runner.FAIL)
        self.assertEqual([c.result for c in outcome.charges], [runner.PASS])

    def test_a_missing_boolean_is_an_error(self):
        # Not a verify_record response at all: an ERROR against the case,
        # as PROTOCOL.md says, with nothing for C12 to judge.
        outcome = self.run_fake(verify_case(), "answer",
                                {"conclusion": "current"})
        self.assertEqual(outcome.result, runner.ERROR)
        self.assertIn("carries no relied", outcome.detail)
        self.assertEqual(outcome.charges, [])

    def test_a_right_answer_passes(self):
        outcome = self.run_fake(verify_case(["withdrawn"]), "answer",
                                {"conclusion": "withdrawn", "relied": False})
        self.assertEqual(outcome.result, runner.PASS)

    def test_two_builds_that_differ_fail(self):
        case = Case("c15-fake", "C15", "C15", "criterion", "build_record",
                    {"fields": "{}"},
                    {"record_id": "AHD-x", "fields": {}}, "fake", repeat=2)
        outcome = self.run_fake(case, "clocked-build")
        self.assertEqual(outcome.result, runner.FAIL)
        self.assertIn("different bytes", outcome.detail)


class Grading(unittest.TestCase):
    def canon_case(self, expect):
        return Case("c1-fake", "C1", "§3", "must", "canonicalise",
                    {"value": "{}"}, expect, "fake")

    def test_wrong_bytes_fail(self):
        case = self.canon_case({"canonical_hex": b"{}".hex()})
        result, _ = runner.grade(case, [{"canonical_hex": b"{ }".hex()}])
        self.assertEqual(result, runner.FAIL)

    def test_a_refusal_where_bytes_are_owed_fails(self):
        case = self.canon_case({"canonical_hex": b"{}".hex()})
        result, _ = runner.grade(case, [{"refused": True}])
        self.assertEqual(result, runner.FAIL)

    def test_bytes_where_a_refusal_is_owed_fail(self):
        case = self.canon_case({"refused": True})
        result, _ = runner.grade(case, [{"canonical_hex": b"{}".hex()}])
        self.assertEqual(result, runner.FAIL)

    def build_case(self, fields):
        return Case("c15-fake", "C15", "C15", "must", "build_record",
                    {"fields": json.dumps(fields)},
                    {"record_id": "AHD-x", "fields": fields}, "fake")

    def test_a_builder_that_adds_a_field_fails(self):
        case = self.build_case({})
        built = json.dumps({"record_id": "AHD-x", "issued_at": "now"})
        result, detail = runner.grade(case, [{"document": built}])
        self.assertEqual(result, runner.FAIL)
        self.assertIn("issued_at", detail)

    def test_a_builder_that_changes_or_drops_a_given_field_fails(self):
        # The identifier is the one the given fields derive; what was built
        # beside it is not what was given.
        given = {"customer": "Example Aerospace GmbH", "runtime": "0.1.0"}
        case = self.build_case(given)
        changed = dict(given, customer="Example Aerospace AG",
                       record_id="AHD-x")
        dropped = {"runtime": "0.1.0", "record_id": "AHD-x"}
        for built in (changed, dropped):
            result, detail = runner.grade(case,
                                          [{"document": json.dumps(built)}])
            self.assertEqual(result, runner.FAIL, built)
            self.assertIn("changed or dropped customer", detail)

    def test_a_builder_that_keeps_every_field_passes(self):
        given = {"customer": "Example Aerospace GmbH", "runtime": "0.1.0"}
        built = dict(given, record_id="AHD-x")
        result, _ = runner.grade(self.build_case(given),
                                 [{"document": json.dumps(built)}])
        self.assertEqual(result, runner.PASS)

    def test_the_command_line_is_split_for_posix_and_kept_for_windows(self):
        self.assertEqual(
            runner.command("python3 'my adapter.py' --fast", windows=False),
            ["python3", "my adapter.py", "--fast"])
        text = r'"C:\Program Files\impl\adapter.exe" --fast'
        self.assertEqual(runner.command(text, windows=True), text)
        for empty in ("", "   "):
            for windows in (False, True):
                with self.assertRaises(ValueError):
                    runner.command(empty, windows=windows)


class Reporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = catalogue.catalogue(cls.spec)

    def outcomes(self, overrides):
        return [runner.Outcome(c, overrides.get(c.id, runner.PASS), "fake")
                for c in self.cases]

    def test_all_pass(self):
        outcomes = self.outcomes({})
        self.assertEqual(report.exit_status(outcomes), 0)
        self.assertIn("hold: C1-C15", report.closing(
            report.criteria(outcomes, self.spec)))

    def test_an_error_is_not_shown_and_not_a_pass(self):
        outcomes = self.outcomes({"c8-forged-key-refused": runner.ERROR})
        rows = dict((r["criterion"], r) for r in
                    report.criteria(outcomes, self.spec))
        self.assertEqual(rows["C8"]["verdict"], "not shown")
        self.assertEqual(report.exit_status(outcomes), 2)
        self.assertNotIn("Every criterion", report.closing(rows.values()))

    def test_a_fail_outranks_an_error(self):
        outcomes = self.outcomes({"c8-forged-key-refused": runner.ERROR,
                                  "c9-empty-anchor": runner.FAIL})
        self.assertEqual(report.exit_status(outcomes), 1)
        closing = report.closing(report.criteria(outcomes, self.spec))
        self.assertIn("fail: C9", closing)
        self.assertIn("not shown: C8", closing)

    def test_a_charge_fails_its_criterion_and_nothing_else(self):
        outcomes = self.outcomes({})
        wrong = runner.Charge("C12", runner.FAIL, "fake")
        for o in outcomes:
            if o.case.id == "c8-forged-key-refused":
                o.charges = [wrong]
        rows = dict((r["criterion"], r) for r in
                    report.criteria(outcomes, self.spec))
        self.assertEqual(rows["C12"]["verdict"], "fails")
        self.assertEqual(rows["C12"]["answers_fail"], 1)
        self.assertEqual(rows["C8"]["verdict"], "holds")
        self.assertEqual(report.exit_status(outcomes), 1)
        text = report.text(outcomes, self.spec, "fake", None)
        self.assertIn("C12 FAIL: fake", text)

    def test_a_charge_on_a_reading_counts_towards_nothing(self):
        outcomes = self.outcomes({})
        for o in outcomes:
            if o.case.id == "c10-reading-no-status-list":
                o.charges = [runner.Charge("C12", runner.FAIL, "fake")]
        self.assertEqual(report.exit_status(outcomes), 0)
        rows = dict((r["criterion"], r) for r in
                    report.criteria(outcomes, self.spec))
        self.assertEqual(rows["C12"]["verdict"], "holds")
        self.assertEqual(rows["C12"]["answers_fail"], 0)
        self.assertIn("counted towards nothing",
                      report.text(outcomes, self.spec, "fake", None))

    def test_a_charge_alone_cannot_make_a_criterion_hold(self):
        # Only C8's cases run: C12 has charged answers that pass and none of
        # its own cases, so it is not run rather than holding.
        outcomes = [o for o in self.outcomes({})
                    if o.case.criterion == "C8"]
        for o in outcomes:
            o.charges = [runner.Charge("C12", runner.PASS, "fake")]
        rows = dict((r["criterion"], r) for r in
                    report.criteria(outcomes, self.spec))
        self.assertEqual(rows["C12"]["verdict"], "not run")

    def test_a_failed_charge_fails_a_criterion_none_of_whose_cases_ran(self):
        # Only C10's cases run, and one answer carries a wrong boolean: C12
        # fails, though none of its own cases was selected, and the closing
        # line says so.
        outcomes = [o for o in self.outcomes({})
                    if o.case.criterion == "C10"]
        for o in outcomes:
            o.charges = [runner.Charge("C12", runner.PASS, "fake")]
            if o.case.id == "c10-withdrawn":
                o.charges = [runner.Charge("C12", runner.FAIL, "fake")]
        rows = report.criteria(outcomes, self.spec)
        verdicts = dict((r["criterion"], r["verdict"]) for r in rows)
        self.assertEqual(verdicts["C12"], "fails")
        self.assertEqual(verdicts["C10"], "holds")
        closing = report.closing(rows)
        self.assertIn("fail: C12; hold: C10;", closing)
        self.assertIn("does not conform", closing)
        self.assertEqual(report.exit_status(outcomes), 1)

    def test_the_header_says_whether_the_text_is_pinned(self):
        text = report.text(self.outcomes({}), self.spec, "fake", None)
        self.assertIn("the published text this suite pins", text)
        self.assertNotIn("NOT a published text", text)

    def test_a_reading_changes_no_verdict(self):
        outcomes = self.outcomes({"c10-reading-no-status-list": runner.FAIL})
        self.assertEqual(report.exit_status(outcomes), 0)
        text = report.text(outcomes, self.spec, "fake", None)
        self.assertIn("differs from the suite's reading", text)

    def test_the_text_report_carries_the_breakdown(self):
        text = report.text(self.outcomes({}), self.spec, "fake", None)
        table = text.split("Criteria (")[1].split("\n\n")[0]
        for criterion, title in self.spec.criteria.items():
            self.assertIn("%s " % criterion, table)
            self.assertIn(title, table)
        self.assertLess(text.index("Criteria ("), text.index("Result:"))


class CommandLine(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "arcs_conformance"] + list(args),
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)

    def test_a_subset_against_the_minimal_adapter(self):
        done = self.cli("--impl", "%s reference/adapter.py" % sys.executable,
                        "--only", "C12")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Result: hold: C12; not run: C1-C11, C13-C15.",
                      done.stdout)

    def test_a_wrong_boolean_fails_c12_when_only_another_criterion_runs(self):
        broken = os.path.join(ROOT, "tests", "broken_adapter.py")
        done = self.cli("--impl", "%s %s relied-means-checked"
                        % (sys.executable, broken), "--only", "C10")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("Result: fail: C12; hold: C10; not run: C1-C9, C11, "
                      "C13-C15.", done.stdout)

    def test_arguments_it_cannot_use(self):
        self.assertEqual(self.cli("--only", "C99", "--list").returncode, 3)
        self.assertEqual(self.cli("--no-such-flag").returncode, 3)
        self.assertEqual(self.cli("--only", "C1").returncode, 3)

    def test_a_damaged_specification_stops_the_run(self):
        tmp = tempfile.mkdtemp()
        try:
            copy = os.path.join(tmp, "spec")
            shutil.copytree(specs.DEFAULT_DIR, copy)
            with open(os.path.join(copy, "ARCS-1.md"), "ab") as fh:
                fh.write(b"\n")
            done = self.cli("--spec", copy, "--list")
            self.assertEqual(done.returncode, 3)
            self.assertIn("does not match SHA256SUMS", done.stderr)
        finally:
            shutil.rmtree(tmp)

    def test_list_and_dump(self):
        listed = self.cli("--list")
        self.assertEqual(listed.returncode, 0)
        total = len(catalogue.catalogue(specs.load()))
        self.assertIn("%d cases:" % total, listed.stdout)
        tmp = tempfile.mkdtemp()
        try:
            done = self.cli("--dump", tmp, "--only", "C9")
            self.assertEqual(done.returncode, 0, done.stderr)
            names = sorted(os.listdir(tmp))
            self.assertEqual(len(names), sum(
                1 for c in catalogue.catalogue(specs.load())
                if c.criterion == "C9"))
            with io.open(os.path.join(tmp, names[0]), encoding="utf-8") as fh:
                dumped = json.load(fh)
            self.assertEqual(dumped["request"]["protocol"], runner.PROTOCOL)
            self.assertIn("expect", dumped)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
