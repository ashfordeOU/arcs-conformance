#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""No criterion holds for a program that answers without looking.

A criterion whose cases all ask for a refusal is passed by a program that
refuses everything, and its `holds` would then be a green nobody earned.
The catalogue answers that with controls (cases.py), and these tests hold
it to the rule in its strongest form: for every criterion and every
operation the criterion uses, no constant answer to that operation passes
all of the criterion's normative cases of that operation. Then the whole
suite is run, through the real protocol, against a program that checks
nothing, and every criterion must fail.

Run: python3 tests/test_blind.py
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    cases as catalogue, report, runner, spec as specs)

# (criterion, operation) pairs a constant may pass, and why. Each is a
# place where ARCS-1 states only one side of a rule, so the suite has only
# that side to ask about.
EXEMPT = {
    ("C5", "matches"): "section 9 defines only the false side of the "
                       "corpus-matching function (PROTOCOL.md, question 11)",
}

NOTHING = r'''
import json, sys
request = json.loads(sys.stdin.read())
op = request["op"]
if op == "verify_record":
    answer = {"conclusion": "unknown", "relied": False}
elif op == "reliance":
    answer = {"relied": request["conclusion"] == "current"}
elif op == "matches":
    answer = {"matches": False}
elif op == "check_successor":
    answer = {"accepted": False}
else:
    answer = {"refused": True}
sys.stdout.write(json.dumps(answer))
'''


def constants(case):
    """Every constant answer worth trying for the case's operation."""
    op = case.op
    if op == "verify_record":
        return [{"conclusion": c, "relied": c == "current"}
                for c in case.vocabulary]
    if op == "canonicalise":
        return [{"refused": True}, {"canonical_hex": b"{}".hex()}]
    if op == "derive_id":
        return [{"refused": True},
                {"id": "AHD-00000000-00000000-00000000"}]
    if op == "reliance":
        return [{"relied": True}, {"relied": False}]
    if op == "matches":
        return [{"matches": True}, {"matches": False}]
    if op == "check_successor":
        return [{"accepted": True}, {"accepted": False}]
    if op == "build_record":
        return [{"refused": True}, {"document": "{}"}]
    raise AssertionError("no constants for %s" % op)


class NoConstantEarnsACriterion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = [c for c in catalogue.catalogue(cls.spec) if c.normative]

    def test_every_criterion_and_operation(self):
        pairs = sorted(set((c.criterion, c.op) for c in self.cases))
        blind = []
        for criterion, op in pairs:
            if (criterion, op) in EXEMPT:
                continue
            mine = [c for c in self.cases
                    if c.criterion == criterion and c.op == op]
            for answer in constants(mine[0]):
                results = [runner.grade(c, [answer] * c.repeat)[0]
                           for c in mine]
                if all(r == runner.PASS for r in results):
                    blind.append("%s %s answering %s" % (
                        criterion, op, json.dumps(answer, sort_keys=True)))
        self.assertEqual(blind, [])

    def test_every_exemption_is_still_needed(self):
        # An exemption the catalogue has outgrown is a hole left open.
        for criterion, op in EXEMPT:
            mine = [c for c in self.cases
                    if c.criterion == criterion and c.op == op]
            self.assertTrue(mine, (criterion, op))
            passing = [a for a in constants(mine[0])
                       if all(runner.grade(c, [a] * c.repeat)[0] ==
                              runner.PASS for c in mine)]
            self.assertTrue(passing, (criterion, op))


class AProgramThatChecksNothing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.tmp = tempfile.mkdtemp()
        cls.adapter = os.path.join(cls.tmp, "nothing.py")
        with io.open(cls.adapter, "w", encoding="utf-8") as fh:
            fh.write(NOTHING)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_fails_every_criterion(self):
        outcomes = runner.run([sys.executable, self.adapter],
                              catalogue.catalogue(self.spec), timeout=60,
                              jobs=8)
        self.assertEqual([o.case.id for o in outcomes
                          if o.result == runner.ERROR], [])
        rows = report.criteria(outcomes, self.spec)
        self.assertEqual(set(r["verdict"] for r in rows), {"fails"})
        self.assertEqual(report.exit_status(outcomes), 1)

    def test_holds_nothing_on_the_criteria_that_used_to_hold_for_it(self):
        done = subprocess.run(
            [sys.executable, "-m", "arcs_conformance", "--impl",
             "%s %s" % (sys.executable, self.adapter),
             "--only", "C2,C3,C7,C8,C9,C12,C13", "--jobs", "8"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=300)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        result = [line for line in done.stdout.splitlines()
                  if line.startswith("Result:")][0]
        self.assertIn("fail: C2-C3, C7-C9, C12-C13;", result)
        self.assertNotIn("hold:", result)


if __name__ == "__main__":
    unittest.main()
