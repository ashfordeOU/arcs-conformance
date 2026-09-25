#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Named defects fail named cases, and nothing else.

A suite that passes a broken verifier has shown nothing, and a suite that
fails it on cases unrelated to the defect has shown something other than
what it claims. So each defect in tests/broken_adapter.py is run alone
against the whole catalogue, and then in combination, and three things are
pinned exactly: the cases it fails, the answers whose reliance boolean it
gets wrong (charged to C12, runner.reliance), and the criteria the report
then says fail. The third is the one a reader quotes, so it is the one a
misattributed failure would corrupt.

The pins also hold the controls to what their notes say. A control whose
artefacts were swapped for a plain sound record's would still expect the
same answer and still get it from the minimal adapter, and every other test
would stay green. The defect pinned against that control would stop failing
it, and its pin would go red.

Run: python3 tests/test_broken.py
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    cases as catalogue, report, runner, spec as specs)

BROKEN = os.path.join(ROOT, "tests", "broken_adapter.py")

# defect -> (the cases it must fail, the answers it must get C12 wrong on)
EXPECTED = {
    "utf16-key-order": ({"c1-keys-sort-by-code-point"}, set()),
    "lenient-json": ({
        "c1-float-refused", "c1-integral-float-refused",
        "c1-duplicate-key-refused", "c1-record-with-float-refused",
        "c1-record-with-duplicate-key-refused"}, set()),
    "normalises-instants": ({
        "c2-offset-refused", "c2-fractional-second-refused",
        "c2-lowercase-refused", "c2-status-list-instant-refused",
        "c2-builder-refuses-offset"}, set()),
    "ignores-undefined-fields": ({"c3-undefined-field-refused"}, set()),
    "no-numbers-in-records": ({
        "c1-control-record-with-integer-current",
        "c3-control-every-optional-field-current",
        "c4-binding-count-changed-after-signing",
        "c4-figure-changed-after-signing", "c5-specimen-verifies"}, set()),
    "binding-integrity-undefined": ({
        "c3-control-every-optional-field-current",
        "c4-binding-count-changed-after-signing",
        "c4-figure-changed-after-signing", "c5-specimen-verifies"}, set()),
    "escaped-identifiers": ({
        "c4-control-non-ascii-record-current", "c4-provenance-covered",
        "c4-serial-over-escaped-json", "c4-specimen-identifier",
        "c5-specimen-verifies"}, set()),
    "specimen-flag-only": ({
        "c5-flag-dropped-and-reissued", "c5-customer-unmarked"}, set()),
    "trust-embedded-key": ({
        "c8-forged-key-refused", "c9-empty-anchor",
        "c9-anchor-without-schema", "c9-anchor-of-another-kind"}, set()),
    # The published specimen is signed by its anchor's second key.
    "first-anchored-key-only": ({
        "c5-specimen-verifies", "c8-control-second-anchored-key-current",
        "c13-another-issuers-list",
        "c13-control-own-issuers-list-withdraws"}, set()),
    "lists-under-first-key-only": ({
        "c8-control-second-anchored-key-current",
        "c13-control-own-issuers-list-withdraws"}, set()),
    "doubt-launders-findings": ({
        "c11-withdrawal-outlives-next-update",
        "c11-unsigned-withdrawal-honoured"}, set()),
    "relies-on-stale": ({"c12-relied-on-stale"}, {
        "c11-stale", "c11-stale-before-expiry",
        "c15-control-past-record-read-after-its-list"}),
    # Right conclusions, a wrong boolean on every one that is neither
    # current nor a failure to check: C12 fails and every other criterion
    # holds, which is the whole point of charging the boolean to C12.
    "relied-means-checked": (set(), {
        "c2-status-list-instant-refused", "c5-specimen-verifies",
        "c6-expired", "c6-not-yet-valid", "c7-record-offered-as-status-list",
        "c7-status-list-of-another-kind",
        "c8-status-list-edited-after-signing",
        "c8-status-list-from-untrusted-key", "c10-finding-at-the-instant",
        "c10-superseded", "c10-withdrawal-not-an-expiry", "c10-withdrawn",
        "c11-finding-state-undefined", "c11-reason-over-200", "c11-stale",
        "c11-stale-before-expiry", "c11-status-list-identifier-unsound",
        "c11-status-list-window-empty",
        "c11-supersession-without-successor", "c11-unsigned-record",
        "c11-unsigned-status-list", "c11-unsigned-withdrawal-honoured",
        "c11-withdrawal-outlives-next-update",
        "c12-control-withdrawn-is-not-relied-on", "c13-another-issuers-list",
        "c13-control-own-issuers-list-withdraws", "c13-out-of-scope-finding",
        "c13-record-issued-after-cut", "c13-status-list-of-another-scope",
        "c15-control-past-record-read-after-its-list"}),
    "drops-findings-quietly": ({"c14-omitted-refused"}, set()),
    "clock": ({"c15-resolved-in-the-past", "c15-resolved-in-the-future"},
              set()),
}
# The clock defect runs against C15 alone: which other cases it fails
# depends on the day the tests run.
SCOPE = {"clock": ("C15",)}
# A control whose artefacts differ from a plain sound record, and the defect
# that, under the control's criterion, only that control catches. Without
# the control the criterion would hold for the defect.
GUARDS = {
    "c1-control-record-with-integer-current": "no-numbers-in-records",
    "c3-control-every-optional-field-current": "binding-integrity-undefined",
    "c8-control-second-anchored-key-current": "first-anchored-key-only",
    "c13-control-own-issuers-list-withdraws": "lists-under-first-key-only",
}
# Together, defects compound: a conclusion one of them changes can carry a
# boolean another gets wrong, so a combined run pins the failing cases
# exactly and the charged answers only from below. relied-means-checked
# would charge nearly every answer another defect moves, and is left out.
COMBINED = sorted(d for d in EXPECTED
                  if d not in SCOPE and d != "relied-means-checked")
# A defect that skips a check hides every defect inside that check: beside
# trust-embedded-key, which never reads the anchor, a narrower reading of
# the anchor changes nothing, and beside ignores-undefined-fields a shorter
# table of fields changes nothing. So the combined run is made twice, once
# without the hidden defects and once without those that hide them.
MASKS = {
    "trust-embedded-key": ("first-anchored-key-only",
                           "lists-under-first-key-only"),
    "ignores-undefined-fields": ("binding-integrity-undefined",),
}
MASKED = set(d for hidden in MASKS.values() for d in hidden)
GROUPS = ([d for d in COMBINED if d not in MASKED],
          [d for d in COMBINED if d not in MASKS])
# Defects checked by a property rather than a pinned list: they break too
# much for a list of cases to say anything a reader could check by eye.
BY_PROPERTY = ("hashes-the-text",)


def run(defects, cases):
    argv = [sys.executable, BROKEN, ",".join(defects)]
    return runner.run(argv, cases, timeout=60, jobs=8)


class NamedDefectsFailNamedCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = catalogue.catalogue(cls.spec)

    def judge(self, outcomes):
        """(failing normative cases, answers charged a C12 FAIL, verdicts)."""
        errors = ["%s: %s" % (o.case.id, o.detail) for o in outcomes
                  if o.result == runner.ERROR]
        self.assertEqual(errors, [])
        readings = [o.case.id for o in outcomes
                    if not o.case.normative and o.result != runner.PASS]
        self.assertEqual(readings, [], "a defect moved a reading")
        failing = set(o.case.id for o in outcomes
                      if o.case.normative and o.result == runner.FAIL)
        charged = set(o.case.id for o in outcomes if o.case.normative
                      for c in o.charges if c.result == runner.FAIL)
        verdicts = dict((r["criterion"], r["verdict"]) for r in
                        report.criteria(outcomes, self.spec))
        return failing, charged, verdicts

    def criteria_of(self, failing, charged):
        blamed = set(c.criterion for c in self.cases if c.id in failing)
        if charged:
            blamed.add(catalogue.RELIANCE_CRITERION)
        return blamed

    def test_each_defect_alone(self):
        for defect, (cases, answers) in sorted(EXPECTED.items()):
            scope = SCOPE.get(defect)
            chosen = [c for c in self.cases
                      if scope is None or c.criterion in scope]
            with self.subTest(defect=defect):
                failing, charged, verdicts = self.judge(run([defect],
                                                            chosen))
                self.assertEqual(failing, cases)
                self.assertEqual(charged, answers)
                blamed = self.criteria_of(cases, answers)
                self.assertEqual(
                    set(k for k, v in verdicts.items() if v == "fails"),
                    blamed)
                ran = set(c.criterion for c in chosen)
                self.assertEqual(
                    set(k for k, v in verdicts.items() if v == "holds"),
                    ran - blamed)

    def test_a_wrong_boolean_fails_c12_and_nothing_else(self):
        outcomes = run(["relied-means-checked"], self.cases)
        rows = report.criteria(outcomes, self.spec)
        self.assertEqual([r["criterion"] for r in rows
                          if r["verdict"] != "holds"], ["C12"])
        c12 = [r for r in rows if r["criterion"] == "C12"][0]
        self.assertEqual(c12["fail"], 0)
        self.assertEqual(c12["answers_fail"],
                         len(EXPECTED["relied-means-checked"][1]))
        self.assertEqual(report.exit_status(outcomes), 1)

    def test_the_defects_together(self):
        for group in GROUPS:
            with self.subTest(group=",".join(group)):
                outcomes = run(group, self.cases)
                cases, answers = set(), set()
                for defect in group:
                    cases |= EXPECTED[defect][0]
                    answers |= EXPECTED[defect][1]
                failing, charged, verdicts = self.judge(outcomes)
                self.assertEqual(failing, cases)
                self.assertLessEqual(answers, charged)
                self.assertEqual(report.exit_status(outcomes), 1)
                self.assertEqual(
                    set(k for k, v in verdicts.items() if v == "fails"),
                    self.criteria_of(cases, charged))

    def test_every_combinable_defect_runs_in_a_group(self):
        self.assertEqual(set(d for g in GROUPS for d in g), set(COMBINED))
        for masker, hidden in MASKS.items():
            for group in GROUPS:
                self.assertFalse(masker in group and set(hidden) & set(group),
                                 masker)

    def test_each_guarded_control_is_its_defects_only_catch(self):
        # From the pins, without a run: under the control's criterion the
        # defect fails the control and nothing else, so without the control
        # that criterion would hold for it.
        criterion = dict((c.id, c.criterion) for c in self.cases)
        for control, defect in sorted(GUARDS.items()):
            self.assertIn("-control-", control)
            caught = set(cid for cid in EXPECTED[defect][0]
                         if criterion[cid] == criterion[control])
            self.assertEqual(caught, {control}, defect)

    def test_hashing_the_text_never_reaches_current(self):
        # PROTOCOL.md section 2: the suite never hands over canonical text,
        # so an implementation that hashes what it was given, rather than
        # CANON of what it says, fails every case that asks for current.
        outcomes = run(["hashes-the-text"], self.cases)
        current = [o for o in outcomes if o.case.normative and
                   o.case.op == "verify_record" and
                   o.case.expect["conclusion"] == ["current"]]
        self.assertTrue(current)
        self.assertEqual([o.case.id for o in current
                          if o.result != runner.FAIL], [])
        rows = report.criteria(outcomes, self.spec)
        self.assertEqual(set(r["verdict"] for r in rows), {"fails"})

    def test_every_defect_is_tested(self):
        sys.path.insert(0, os.path.join(ROOT, "tests"))
        import broken_adapter
        self.assertEqual(sorted(broken_adapter.DEFECTS),
                         sorted(list(EXPECTED) + list(BY_PROPERTY)))

    def test_no_defect_is_a_reading(self):
        readings = set(c.id for c in self.cases if not c.normative)
        for cases, answers in EXPECTED.values():
            self.assertFalse((cases | answers) & readings)


if __name__ == "__main__":
    unittest.main()
