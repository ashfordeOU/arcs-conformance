#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The catalogue's own discipline: citations, expectations, reproducibility.

A case that cites no clause is an opinion, a case that expects `current`
from a refusing set is a typo that passes every implementation, and a
catalogue that differs between two builds cannot be the same suite on two
machines. These tests hold the catalogue to all three without running any
implementation.

Run: python3 tests/test_catalogue.py
"""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    cases as catalogue, ed25519, spec as specs)

INSTANT = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
                     r"[0-9]{2}Z\Z")


class Discipline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = catalogue.catalogue(cls.spec)

    def test_every_criterion_carries_its_own_section_12_test(self):
        for criterion in self.spec.criteria:
            own = [c for c in self.cases if c.criterion == criterion and
                   c.basis == "criterion"]
            self.assertTrue(own, "%s has no case built from its own test"
                            % criterion)

    def test_every_case_cites_a_clause_and_says_why(self):
        for case in self.cases:
            self.assertIn(case.criterion, self.spec.criteria, case.id)
            self.assertTrue(re.search(r"§[0-9]+|\bC[0-9]+\b", case.clause),
                            case.id)
            self.assertTrue(case.note.strip(), case.id)
            self.assertTrue(case.id.startswith(case.criterion.lower() + "-"),
                            case.id)
            self.assertEqual("-reading-" in case.id, not case.normative,
                             case.id)

    def test_verify_expectations_are_answers_the_protocol_has(self):
        for case in self.cases:
            if case.op != "verify_record":
                continue
            allowed = case.expect["conclusion"]
            self.assertTrue(allowed, case.id)
            self.assertLessEqual(set(allowed), set(case.vocabulary), case.id)
            if len(allowed) > 1 and "current" in allowed:
                # Only where ARCS-1 leaves open whether a record with no
                # status list can be current (PROTOCOL.md, question 2).
                self.assertNotIn("status_list", case.request, case.id)

    def test_current_alone_is_expected_only_with_a_status_list(self):
        for case in self.cases:
            if case.op == "verify_record" and \
                    case.expect["conclusion"] == ["current"]:
                self.assertIn("status_list", case.request, case.id)

    def test_requests_carry_artefacts_as_text(self):
        for case in self.cases:
            request = case.request
            for name in ("document", "anchor", "status_list", "previous",
                         "successor", "fields", "value"):
                if name in request:
                    self.assertIsInstance(request[name], str, case.id)
            if "at" in request:
                self.assertRegex(request["at"], INSTANT)

    def test_exactly_one_shape_of_expectation_per_operation(self):
        shapes = {
            "canonicalise": ({"canonical_hex"}, {"refused"}),
            "derive_id": ({"id"},),
            "verify_record": ({"conclusion"},),
            "reliance": ({"relied"},),
            "matches": ({"matches"},),
            "check_successor": ({"accepted"},),
            "build_record": ({"record_id", "fields"}, {"refused"}),
        }
        for case in self.cases:
            self.assertIn(set(case.expect), shapes[case.op], case.id)

    def test_the_catalogue_is_reproducible(self):
        again = catalogue.catalogue(specs.load())
        self.assertEqual(json.dumps([c.to_dict() for c in self.cases]),
                         json.dumps([c.to_dict() for c in again]))

    def test_signed_cases_are_built_from_the_attestation_vector(self):
        # The minimal record every signed case starts from carries exactly
        # the body digest of the section 13 vector, and its signature is
        # over exactly the vector's signed bytes.
        kit = catalogue._Kit(self.spec)
        vector = self.spec.vectors["attestation-payload"]
        att = kit.record["attestation"]
        self.assertEqual(att["body_digest"], vector["body_digest"])
        self.assertTrue(ed25519.verify(kit.issuer.public,
                                       vector["signed_bytes"].encode("utf-8"),
                                       bytes.fromhex(att["signature"])))

    def test_a_control_asks_for_one_named_answer(self):
        # A control is the twin that must be accepted, so it is normative
        # and names exactly one answer: never a set of refusals.
        controls = [c for c in self.cases if "-control-" in c.id]
        self.assertTrue(controls)
        for case in controls:
            self.assertEqual(case.basis, "must", case.id)
            if case.op == "verify_record":
                self.assertEqual(len(case.expect["conclusion"]), 1, case.id)
            else:
                self.assertEqual(case.op, "build_record", case.id)
                self.assertIn("record_id", case.expect, case.id)

    def test_the_specimen_is_asked_about_inside_its_own_window(self):
        # Read from the specimen, never typed: a re-issued specimen with
        # another window must move the instant with it.
        kit = catalogue._Kit(self.spec)
        start = self.spec.specimen["not_before"]
        end = self.spec.specimen["not_after"]
        self.assertEqual(kit.in_specimen_window,
                         catalogue._midpoint(start, end))
        self.assertLess(start, kit.in_specimen_window)
        self.assertLess(kit.in_specimen_window, end)
        self.assertEqual(catalogue._midpoint("2026-01-01T00:00:00Z",
                                             "2026-01-01T00:00:03Z"),
                         "2026-01-01T00:00:01Z")

    def test_every_operation_is_exercised(self):
        self.assertEqual(sorted(set(c.op for c in self.cases)),
                         sorted(catalogue.OPERATIONS))


if __name__ == "__main__":
    unittest.main()
