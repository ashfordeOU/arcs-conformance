#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The copy of ARCS-1 the suite grades against, and what it reads from it.

The suite takes its vectors, criteria, conclusions and specimen from the
document at run time and types only the section 7 strings, so these tests
hold those strings to the document and prove that a damaged or
self-contradicting copy is refused before any case is graded, and that a
copy rewritten with fresh sums is graded but never passed off as the
published text.

Run: python3 tests/test_spec.py
"""

import copy
import hashlib
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    build, cases as catalogue, ed25519, report, runner, spec as specs)


class TheCopy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()

    def test_reads_what_the_document_states(self):
        self.assertRegex(self.spec.edition, r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
        self.assertEqual(sorted(self.spec.criteria, key=lambda c: int(c[1:])),
                         ["C%d" % n for n in range(1, 16)])
        self.assertEqual(len(self.spec.conclusions), 9)
        self.assertIn("current", self.spec.conclusions)
        self.assertEqual(self.spec.quoted("C3"), ["note"])
        self.assertEqual(len(self.spec.quoted("C2")), 3)

    def test_typed_strings_are_the_documents(self):
        vectors = self.spec.vectors
        self.assertEqual(build.RECORD_CONTEXT,
                         vectors["minimal-record"]["record"]["context"])
        self.assertEqual(build.LIST_CONTEXT,
                         vectors["status-list"]["listing"]["context"])
        self.assertIn('"context":"%s"' % build.ATTESTATION_CONTEXT,
                      vectors["attestation-payload"]["signed_bytes"])
        self.assertEqual(build.ANCHOR_SCHEMA,
                         self.spec.specimen_anchor["schema"])
        self.assertTrue(self.spec.specimen["customer"].startswith(
            build.SPECIMEN_CUSTOMER))
        for text in (build.RECORD_CONTEXT, build.LIST_CONTEXT,
                     build.ATTESTATION_CONTEXT, build.ANCHOR_SCHEMA,
                     build.SPECIMEN_CUSTOMER):
            self.assertIn("`%s`" % text, self.spec.document)

    def test_the_copy_is_the_published_text(self):
        self.assertTrue(self.spec.pinned)
        self.assertEqual(specs.PUBLISHED[self.spec.sha256], self.spec.edition)

    def test_the_reliance_criterion_is_the_one_about_reliance(self):
        title = self.spec.criteria[catalogue.RELIANCE_CRITERION]
        self.assertIn("reliance", title)

    def test_vectors_agree_with_each_other(self):
        self.assertEqual(specs.check_vectors(self.spec.vectors), [])

    def test_a_vector_that_disagrees_is_found(self):
        vectors = copy.deepcopy(self.spec.vectors)
        vectors["minimal-record"]["record"]["customer"] += "."
        problems = specs.check_vectors(vectors)
        self.assertTrue(any("minimal-record" in p for p in problems))

    def test_the_specimen_verifies_under_its_anchor(self):
        record = self.spec.specimen
        self.assertEqual(build.derive_id(record), record["record_id"])
        att = record["attestation"]
        body_digest = "sha256:" + build.sha(build.canon(
            build.unsigned(record)))
        self.assertEqual(att["body_digest"], body_digest)
        anchored = [k for k in self.spec.specimen_anchor["keys"]
                    if k["key_id"] == att["key_id"]]
        self.assertEqual(len(anchored), 1)
        signed = build.canon({"context": build.ATTESTATION_CONTEXT,
                              "body_digest": body_digest})
        public = bytes.fromhex(anchored[0]["public_key"])
        self.assertTrue(ed25519.verify(public, signed,
                                       bytes.fromhex(att["signature"])))


class ADamagedCopyIsRefused(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.copy = os.path.join(self.tmp, "spec")
        shutil.copytree(specs.DEFAULT_DIR, self.copy)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _rewrite(self, name, old, new):
        path = os.path.join(self.copy, name)
        with open(path, "rb") as fh:
            data = fh.read()
        self.assertIn(old, data)
        with open(path, "wb") as fh:
            fh.write(data.replace(old, new, 1))

    def test_an_intact_copy_loads(self):
        self.assertEqual(specs.load(self.copy).sha256,
                         specs.load().sha256)

    def test_one_byte_changed(self):
        self._rewrite("ARCS-1.md", b"Canonical serialisation",
                      b"Canonical serialization")
        with self.assertRaisesRegex(specs.SpecError, "does not match"):
            specs.load(self.copy)

    def test_a_file_missing(self):
        os.remove(os.path.join(self.copy, "specimen",
                               "specimen-trust-anchor.json"))
        with self.assertRaisesRegex(specs.SpecError, "missing"):
            specs.load(self.copy)

    def test_a_file_the_sums_do_not_cover(self):
        self._rewrite("SHA256SUMS", b"  specimen/specimen-trust-anchor.json\n",
                      b"  specimen/specimen-trust-anchor.json.bak\n")
        os.rename(os.path.join(self.copy, "specimen",
                               "specimen-trust-anchor.json"),
                  os.path.join(self.copy, "specimen",
                               "specimen-trust-anchor.json.bak"))
        with self.assertRaisesRegex(specs.SpecError, "does not cover"):
            specs.load(self.copy)

    def test_a_rewritten_copy_with_fresh_sums_is_not_pinned(self):
        # SHA256SUMS regenerated over an edited text: intact by its own
        # sums, so it loads, and not the published text, so it says so.
        path = os.path.join(self.copy, "ARCS-1.md")
        with open(path, "ab") as fh:
            fh.write(b"\n")
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        sums = os.path.join(self.copy, "SHA256SUMS")
        with open(sums, "rb") as fh:
            lines = fh.read().splitlines(True)
        with open(sums, "wb") as fh:
            for line in lines:
                if line.rstrip().endswith(b"  ARCS-1.md"):
                    line = digest.encode("ascii") + b"  ARCS-1.md\n"
                fh.write(line)
        spec = specs.load(self.copy)
        self.assertFalse(spec.pinned)
        outcomes = [runner.Outcome(c, runner.PASS, "fake")
                    for c in catalogue.catalogue(spec)]
        text = report.text(outcomes, spec, "fake", None)
        self.assertIn("NOT a published text this suite pins", text)
        self.assertIn("none of this is a result against ARCS-1 as "
                      "published", text)
        self.assertFalse(report.as_json(outcomes, spec, "fake",
                                        None)["specification"]["pinned"])

    def test_a_path_outside_the_directory(self):
        self._rewrite("SHA256SUMS", b"  LICENSE\n", b"  ../LICENSE\n")
        with self.assertRaisesRegex(specs.SpecError, "outside"):
            specs.load(self.copy)


if __name__ == "__main__":
    unittest.main()
