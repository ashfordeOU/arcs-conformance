#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The minimal adapter passes every case: the suite can be passed.

If a case in the catalogue cannot be passed by an implementation written
from the specification alone, the fault is in the case or in ARCS-1, and
either way the suite would be grading something other than conformance.
This runs the whole catalogue through the real protocol, one process per
call, and requires PASS on every normative case and agreement on every
reading.

Run: python3 tests/test_reference.py
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    cases as catalogue, report, runner, spec as specs)

ADAPTER = [sys.executable, os.path.join(ROOT, "reference", "adapter.py")]


class TheMinimalAdapterPasses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.outcomes = runner.run(ADAPTER, catalogue.catalogue(cls.spec),
                                  timeout=60, jobs=8)

    def test_every_case_passes(self):
        failing = ["%s %s: %s" % (o.result, o.case.id, o.detail)
                   for o in self.outcomes if o.result != runner.PASS]
        self.assertEqual(failing, [])

    def test_every_criterion_holds(self):
        rows = report.criteria(self.outcomes, self.spec)
        self.assertEqual(set(r["verdict"] for r in rows), {"holds"})
        self.assertEqual(report.exit_status(self.outcomes), 0)

    def test_it_describes_itself(self):
        self.assertEqual(runner.describe(ADAPTER),
                         "arcs-minimal-adapter 1.0.0")


if __name__ == "__main__":
    unittest.main()
