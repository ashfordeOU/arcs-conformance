#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""What every case accepts, pinned case by case.

The reference adapter shows that each case can be passed, and the broken
one that some can be failed. Neither shows that a case asks for what its
note says: loosen c10-withdrawn from `withdrawn` to any refusal and the
reference adapter still passes it, and no defect notices. So the answer set
of every case is written out here a second time, by hand and on purpose,
and the catalogue is held to it. Then every answer an implementation could
give is put to the grader, and it must pass exactly the pinned ones.

A change to what a case accepts is a change to the suite, and it is made
twice: once in cases.py and once here, where a reviewer sees it.

Run: python3 tests/test_expectations.py
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    cases as catalogue, runner, spec as specs)

REFUSED = "refused"
# Spelled out, not read from the catalogue: the nine conclusions of section
# 11 without `current`, and the protocol's `refused`.
ANY_REFUSAL = {"unsound_id", "unknown", "withdrawn", "superseded",
               "unauthenticated", "stale", "not_yet_valid", "expired",
               "refused"}
# C3's own test: refused although the identifier is sound.
ANY_REFUSAL_BUT_UNSOUND_ID = ANY_REFUSAL - {"unsound_id"}

# id -> (basis, operation, what it accepts). For verify_record, the
# conclusions; for canonicalise, the canonical text or REFUSED; for
# derive_id, the identifier; for build_record, the record_id or REFUSED; for
# the three boolean operations, the boolean.
PINNED = {
    "c1-vector-canonical-ordering":
        ("criterion", "canonicalise",
         "{\"a\":{\"b\":[true,false,null],\"\u00e9\":\"caf\u00e9\"},"
         "\"n\":10,\"z\":1}"),
    "c1-escaped-input-emitted-literally":
        ("must", "canonicalise",
         "{\"name\":\"caf\u00e9 \u5b87\u5b99\",\"z\":\"\u00e9\"}"),
    "c1-keys-sort-by-code-point":
        ("must", "canonicalise", "{\"a\":1,\"\uff21\":2,\"\U0001f600\":3}"),
    "c1-whitespace-removed-order-kept":
        ("must", "canonicalise",
         "{\"a\":{},\"b\":[{\"x\":1,\"y\":2},[3,2,1]],\"c\":[]}"),
    "c1-integers": ("must", "canonicalise", "{\"n\":[0,-1,10,1234567890123]}"),
    "c1-float-refused": ("must", "canonicalise", REFUSED),
    "c1-integral-float-refused": ("must", "canonicalise", REFUSED),
    "c1-nan-refused": ("must", "canonicalise", REFUSED),
    "c1-duplicate-key-refused": ("must", "canonicalise", REFUSED),
    "c1-record-with-float-refused": ("must", "verify_record", ANY_REFUSAL),
    "c1-record-with-duplicate-key-refused":
        ("must", "verify_record", ANY_REFUSAL),
    "c1-control-record-with-integer-current":
        ("must", "verify_record", {"current"}),
    "c1-reading-string-escapes":
        ("reading", "canonicalise",
         "{\"s\":\"a\\nb\\tc\\\"d\\\\e\\u001ff/g\u007fh\u2028i\"}"),
    "c2-offset-refused": ("criterion", "verify_record", ANY_REFUSAL),
    "c2-fractional-second-refused":
        ("criterion", "verify_record", ANY_REFUSAL),
    "c2-lowercase-refused": ("criterion", "verify_record", ANY_REFUSAL),
    "c2-impossible-date-refused": ("must", "verify_record", ANY_REFUSAL),
    "c2-status-list-instant-refused": ("must", "verify_record", ANY_REFUSAL),
    "c2-builder-refuses-offset": ("must", "build_record", REFUSED),
    "c2-control-exact-instants-current":
        ("must", "verify_record", {"current"}),
    "c2-control-builder-keeps-exact-instants":
        ("must", "build_record", "AHD-86446bd1-3e0f8893-b6b56d24"),
    "c3-undefined-field-refused":
        ("criterion", "verify_record", ANY_REFUSAL_BUT_UNSOUND_ID),
    "c3-required-field-missing": ("must", "verify_record", ANY_REFUSAL),
    "c3-customer-empty": ("must", "verify_record", ANY_REFUSAL),
    "c3-corpora-empty": ("must", "verify_record", ANY_REFUSAL),
    "c3-corpus-digest-uppercase": ("must", "verify_record", ANY_REFUSAL),
    "c3-corpus-digest-short": ("must", "verify_record", ANY_REFUSAL),
    "c3-spec-other": ("must", "verify_record", ANY_REFUSAL),
    "c3-claim-other": ("must", "verify_record", ANY_REFUSAL),
    "c3-binding-not-ok": ("must", "verify_record", ANY_REFUSAL),
    "c3-binding-count-not-integer": ("must", "verify_record", ANY_REFUSAL),
    "c3-provenance-not-object": ("must", "verify_record", ANY_REFUSAL),
    "c3-control-every-optional-field-current":
        ("must", "verify_record", {"current"}),
    "c4-vector-minimal-record":
        ("criterion", "derive_id", "AHD-86446bd1-3e0f8893-b6b56d24"),
    "c4-one-character-moves-the-identifier":
        ("criterion", "derive_id", "AHD-1ce2b004-f336ee5d-2025ad66"),
    "c4-edited-customer-is-unsound":
        ("criterion", "verify_record", {"unsound_id"}),
    "c4-vector-status-list":
        ("must", "derive_id", "AHS-d48d5c2b-9b3f768b-493ca350"),
    "c4-specimen-identifier":
        ("must", "derive_id", "SPECIMEN-ba5b0cb7-80977e7c-fa5a2958"),
    "c4-attestation-excluded":
        ("must", "derive_id", "AHD-86446bd1-3e0f8893-b6b56d24"),
    "c4-provenance-covered":
        ("must", "derive_id", "SPECIMEN-1188e2f8-a3172242-a6bad464"),
    "c4-figure-changed-after-signing":
        ("must", "verify_record", {"unsound_id"}),
    "c4-binding-count-changed-after-signing":
        ("must", "verify_record", {"unsound_id"}),
    "c4-serial-copied-from-another-record":
        ("must", "verify_record", {"unsound_id"}),
    "c4-serial-in-uppercase": ("must", "verify_record", ANY_REFUSAL),
    "c4-serial-over-spaced-json": ("must", "verify_record", {"unsound_id"}),
    "c4-serial-over-escaped-json": ("must", "verify_record", {"unsound_id"}),
    "c4-control-non-ascii-record-current":
        ("must", "verify_record", {"current"}),
    "c5-specimen-verifies": ("must", "verify_record", {"current", "unknown"}),
    "c5-specimen-flag-deleted": ("criterion", "verify_record", ANY_REFUSAL),
    "c5-flag-dropped-and-reissued": ("must", "verify_record", ANY_REFUSAL),
    "c5-customer-unmarked": ("must", "verify_record", ANY_REFUSAL),
    "c5-control-unmarked-record-current":
        ("must", "verify_record", {"current"}),
    "c5-specimen-false": ("must", "verify_record", ANY_REFUSAL),
    "c5-specimen-never-matches": ("must", "matches", False),
    "c5-builder-marks-specimen":
        ("must", "build_record", "SPECIMEN-dbb83462-de93cf3b-581e3fe1"),
    "c5-reading-marked-specimen-verifies":
        ("reading", "verify_record", {"current"}),
    "c5-reading-record-matches-its-corpora": ("reading", "matches", True),
    "c6-empty-window-refused": ("criterion", "verify_record", ANY_REFUSAL),
    "c6-window-opens-before-issue": ("must", "verify_record", ANY_REFUSAL),
    "c6-window-inverted": ("must", "verify_record", ANY_REFUSAL),
    "c6-builder-refuses-empty-window": ("must", "build_record", REFUSED),
    "c6-control-builder-keeps-a-one-second-window":
        ("must", "build_record", "AHD-4b2f054a-c942ad5e-74722701"),
    "c6-not-yet-valid": ("must", "verify_record", {"not_yet_valid"}),
    "c6-expired": ("must", "verify_record", {"expired"}),
    "c7-status-list-offered-as-record":
        ("criterion", "verify_record", ANY_REFUSAL),
    "c7-earlier-record-shape": ("must", "verify_record", ANY_REFUSAL),
    "c7-attestation-for-another-purpose":
        ("must", "verify_record", ANY_REFUSAL),
    "c7-signature-made-for-another-purpose":
        ("must", "verify_record", ANY_REFUSAL),
    "c7-record-offered-as-status-list": ("must", "verify_record", ANY_REFUSAL),
    "c7-status-list-of-another-kind": ("must", "verify_record", ANY_REFUSAL),
    "c7-control-each-document-in-its-place-current":
        ("must", "verify_record", {"current"}),
    "c8-forged-key-refused": ("criterion", "verify_record", ANY_REFUSAL),
    "c8-embedded-key-disagrees": ("must", "verify_record", ANY_REFUSAL),
    "c8-key-id-relabelled": ("must", "verify_record", ANY_REFUSAL),
    "c8-signature-truncated": ("must", "verify_record", ANY_REFUSAL),
    "c8-signature-bit-flipped": ("must", "verify_record", ANY_REFUSAL),
    "c8-signature-malleated": ("must", "verify_record", ANY_REFUSAL),
    "c8-body-edited-identifier-rederived":
        ("must", "verify_record", ANY_REFUSAL),
    "c8-body-digest-rewritten": ("must", "verify_record", ANY_REFUSAL),
    "c8-body-digest-over-escaped-json": ("must", "verify_record", ANY_REFUSAL),
    "c8-attestation-field-undefined": ("must", "verify_record", ANY_REFUSAL),
    "c8-algorithm-other": ("must", "verify_record", ANY_REFUSAL),
    "c8-status-list-edited-after-signing":
        ("must", "verify_record", ANY_REFUSAL),
    "c8-status-list-from-untrusted-key":
        ("must", "verify_record", ANY_REFUSAL),
    "c8-specimen-against-another-anchor":
        ("must", "verify_record", ANY_REFUSAL),
    "c8-control-anchored-key-current": ("must", "verify_record", {"current"}),
    "c8-control-second-anchored-key-current":
        ("must", "verify_record", {"current"}),
    "c9-empty-anchor": ("criterion", "verify_record", ANY_REFUSAL),
    "c9-empty-anchor-specimen": ("criterion", "verify_record", ANY_REFUSAL),
    "c9-anchor-without-schema": ("must", "verify_record", ANY_REFUSAL),
    "c9-anchor-of-another-kind": ("must", "verify_record", ANY_REFUSAL),
    "c9-control-anchored-record-current":
        ("must", "verify_record", {"current"}),
    "c10-good-standing": ("criterion", "verify_record", {"current"}),
    "c10-withdrawn": ("criterion", "verify_record", {"withdrawn"}),
    "c10-superseded": ("must", "verify_record", {"superseded"}),
    "c10-finding-not-yet-in-effect": ("must", "verify_record", {"current"}),
    "c10-finding-at-the-instant": ("must", "verify_record", {"withdrawn"}),
    "c10-withdrawal-not-an-expiry": ("must", "verify_record", {"withdrawn"}),
    "c10-finding-against-another-record":
        ("must", "verify_record", {"current"}),
    "c10-reading-no-status-list": ("reading", "verify_record", ANY_REFUSAL),
    "c11-withdrawal-outlives-next-update":
        ("criterion", "verify_record", {"withdrawn"}),
    "c11-unsigned-withdrawal-honoured":
        ("criterion", "verify_record", {"withdrawn"}),
    "c11-stale": ("must", "verify_record", {"stale"}),
    "c11-stale-before-expiry": ("must", "verify_record", {"stale"}),
    "c11-unsigned-status-list":
        ("must", "verify_record", {"unauthenticated", "unknown"}),
    "c11-unsigned-record":
        ("must", "verify_record", {"unauthenticated", "unknown"}),
    "c11-unsigned-both": ("must", "verify_record", {"unauthenticated"}),
    "c11-supersession-without-successor":
        ("must", "verify_record", ANY_REFUSAL),
    "c11-reason-over-200": ("must", "verify_record", ANY_REFUSAL),
    "c11-finding-state-undefined": ("must", "verify_record", ANY_REFUSAL),
    "c11-status-list-identifier-unsound":
        ("must", "verify_record", ANY_REFUSAL),
    "c11-status-list-window-empty": ("must", "verify_record", ANY_REFUSAL),
    "c11-reading-unsigned-list-against-signed-record":
        ("reading", "verify_record", {"unknown"}),
    "c12-relied-on-unsound-id": ("criterion", "reliance", False),
    "c12-relied-on-unknown": ("criterion", "reliance", False),
    "c12-relied-on-withdrawn": ("criterion", "reliance", False),
    "c12-relied-on-superseded": ("criterion", "reliance", False),
    "c12-relied-on-unauthenticated": ("criterion", "reliance", False),
    "c12-relied-on-stale": ("criterion", "reliance", False),
    "c12-relied-on-not-yet-valid": ("criterion", "reliance", False),
    "c12-relied-on-expired": ("criterion", "reliance", False),
    "c12-relied-on-current": ("criterion", "reliance", True),
    "c12-control-current-is-relied-on": ("must", "verify_record", {"current"}),
    "c12-control-withdrawn-is-not-relied-on":
        ("must", "verify_record", {"withdrawn"}),
    "c13-status-list-of-another-scope":
        ("criterion", "verify_record", {"unknown"}),
    "c13-record-issued-after-cut": ("criterion", "verify_record", {"unknown"}),
    "c13-out-of-scope-finding": ("must", "verify_record", {"unknown"}),
    "c13-another-issuers-list": ("must", "verify_record", {"unknown"}),
    "c13-control-list-in-scope-current":
        ("must", "verify_record", {"current"}),
    "c13-control-own-issuers-list-withdraws":
        ("must", "verify_record", {"withdrawn"}),
    "c14-successor-accepted": ("must", "check_successor", True),
    "c14-softened-refused": ("criterion", "check_successor", False),
    "c14-omitted-refused": ("criterion", "check_successor", False),
    "c14-escalation-accepted": ("must", "check_successor", True),
    "c14-chain-digest-without-attestation": ("must", "check_successor", False),
    "c14-sequence-skipped": ("must", "check_successor", False),
    "c14-reading-finding-postponed": ("reading", "check_successor", False),
    "c15-build-twice":
        ("criterion", "build_record", "AHD-86446bd1-3e0f8893-b6b56d24"),
    "c15-resolved-in-the-past": ("criterion", "verify_record", {"current"}),
    "c15-resolved-in-the-future": ("must", "verify_record", {"current"}),
    "c15-control-past-record-read-after-its-list":
        ("must", "verify_record", {"stale"}),
}


def _hex(text):
    return text.encode("utf-8").hex()


class EveryCaseAcceptsWhatItsNoteSays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = catalogue.catalogue(cls.spec)

    def test_the_pinned_cases_are_the_catalogue(self):
        self.assertEqual([c.id for c in self.cases], list(PINNED))

    def test_basis_and_operation(self):
        for case in self.cases:
            basis, op, _ = PINNED[case.id]
            self.assertEqual((case.basis, case.op), (basis, op), case.id)

    def test_what_each_case_expects(self):
        for case in self.cases:
            pinned = PINNED[case.id][2]
            expect = case.expect
            with self.subTest(case=case.id):
                if case.op == "verify_record":
                    self.assertEqual(set(expect["conclusion"]), pinned)
                elif case.op == "canonicalise":
                    if pinned == REFUSED:
                        self.assertEqual(expect, {"refused": True})
                    else:
                        self.assertEqual(expect,
                                         {"canonical_hex": _hex(pinned)})
                elif case.op == "derive_id":
                    self.assertEqual(expect, {"id": pinned})
                elif case.op == "build_record":
                    if pinned == REFUSED:
                        self.assertEqual(expect, {"refused": True})
                    else:
                        self.assertEqual(expect["record_id"], pinned)
                else:
                    field = {"reliance": "relied", "matches": "matches",
                             "check_successor": "accepted"}[case.op]
                    self.assertEqual(expect, {field: pinned})

    def test_the_grader_passes_exactly_the_pinned_answers(self):
        for case in self.cases:
            pinned = PINNED[case.id][2]
            for answer, allowed in self.answers(case, pinned):
                result, detail = runner.grade(case, [answer] * case.repeat)
                self.assertEqual(result == runner.PASS, allowed,
                                 "%s answering %s: %s %s" % (
                                     case.id, json.dumps(answer), result,
                                     detail))

    def answers(self, case, pinned):
        """(an answer, whether the case may pass it), every kind there is."""
        if case.op == "verify_record":
            return [({"conclusion": c, "relied": c == "current"},
                     c in pinned) for c in case.vocabulary]
        if case.op == "canonicalise":
            if pinned == REFUSED:
                return [({"refused": True}, True),
                        ({"canonical_hex": _hex("{}")}, False)]
            return [({"canonical_hex": _hex(pinned)}, True),
                    ({"canonical_hex": _hex(pinned + " ")}, False),
                    ({"refused": True}, False)]
        if case.op == "derive_id":
            return [({"id": pinned}, True),
                    ({"id": pinned[:-1] + ("0" if pinned[-1] != "0"
                                           else "1")}, False),
                    ({"refused": True}, False)]
        if case.op == "build_record":
            if pinned == REFUSED:
                return [({"refused": True}, True),
                        ({"document": "{}"}, False)]
            built = dict(case.expect["fields"], record_id=pinned)
            return [({"document": json.dumps(built)}, True),
                    ({"refused": True}, False)]
        field = {"reliance": "relied", "matches": "matches",
                 "check_successor": "accepted"}[case.op]
        return [({field: pinned}, True), ({field: not pinned}, False)]


if __name__ == "__main__":
    unittest.main()
