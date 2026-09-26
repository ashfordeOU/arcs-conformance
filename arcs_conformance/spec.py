# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The specification, read from the document rather than retyped.

WHY THE SUITE READS ARCS-1 INSTEAD OF QUOTING IT
------------------------------------------------
Every expected value the suite takes from ARCS-1 is read from a copy of the
published specification directory at run time: the four vectors of section
13, the fifteen criterion titles of section 12, the nine conclusions of
section 11, the edition, and the specimen with its anchor. A figure retyped
into a test is a second copy, and the day the two disagree the suite is
testing its author's memory instead of the document.

A copy of the directory that fails its own SHA256SUMS is refused before a
single case runs. Section 16 says that file is what tells an intact copy
from any other, and a suite that graded against a damaged copy would be
grading against a specification nobody published.

SHA256SUMS shows only that a copy agrees with itself: rewrite the text,
regenerate the sums, and the copy is intact again. So the suite also pins
the digest of each published text it was written against (PUBLISHED). A
copy that is not one of them still runs, because a draft of the next
edition is worth testing against, but the report says in its header and in
its closing line that the result is about that copy and not about ARCS-1 as
published.

WHAT IS CHECKED ON LOADING
--------------------------
The sums, and then the vectors against each other: the canonical bytes
against their digest, the minimal record against its identifier, the
attestation payload against the record, the status list against its
identifier. A copy that disagrees with itself is refused as well. That is a
finding about the copy, or about the specification, and never a reason to
grade an implementation against whichever half the suite happened to read.
"""

import hashlib
import io
import json
import os
import re

from . import build

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "spec")

DOCUMENT = "ARCS-1.md"
SPECIMEN = "specimen/aero-capability-dossier.json"
SPECIMEN_ANCHOR = "specimen/specimen-trust-anchor.json"
REQUIRED = (DOCUMENT, SPECIMEN, SPECIMEN_ANCHOR)
VECTORS = ("canonical-ordering", "minimal-record", "attestation-payload",
           "status-list")

# SHA-256 of ARCS-1.md -> the edition it states, for every published text
# this catalogue was written against.
PUBLISHED = {
    "10e0a328fb3a489f3c65678a708b68fc06bef1c9cdf9e5dc67dbe9c8dfc6d1d8":
        "2026-09-24",
    "6d68f8d5d9ea2ec130dacb9c9d2af50cae67008f3a2b77911e5b66f58d05ccec":
        "2026-09-26",
}


class SpecError(Exception):
    """The specification copy cannot be graded against."""


class Spec(object):
    """One intact copy of the published ARCS-1 directory."""

    def __init__(self, directory, document, sums):
        self.directory = directory
        self.document = document
        self.sha256 = sums[DOCUMENT]
        self.edition = _edition(document)
        self.pinned = PUBLISHED.get(self.sha256) == self.edition
        self.criteria = _criteria(document)
        self.conclusions = _conclusions(document)
        self.vectors = _vectors(document)
        self.specimen_text = _read(directory, SPECIMEN)
        self.specimen_anchor_text = _read(directory, SPECIMEN_ANCHOR)
        self.specimen = json.loads(self.specimen_text)
        self.specimen_anchor = json.loads(self.specimen_anchor_text)

    def quoted(self, criterion):
        """The `code` spans of one criterion's section 12 text, in order.

        Where a criterion's own test names a value (the three instants of
        C2, the field of C3), the case uses the value as printed.
        """
        match = re.search(r"^### %s — [^\n]*\n(.*?)(?=^### |^---|\Z)"
                          % re.escape(criterion), self.document, re.M | re.S)
        if not match:
            raise SpecError("section 12 has no criterion %s" % criterion)
        return re.findall(r"`([^`]+)`", match.group(1))


def load(directory=None):
    """Load and check a copy of the specification directory."""
    directory = os.path.abspath(directory or DEFAULT_DIR)
    sums = check_sums(directory)
    spec = Spec(directory, _read(directory, DOCUMENT), sums)
    problems = check_vectors(spec.vectors)
    if problems:
        raise SpecError("the copy of ARCS-1 in %s disagrees with itself: %s"
                        % (directory, "; ".join(problems)))
    return spec


def _read(directory, name):
    path = os.path.join(directory, *name.split("/"))
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()
    except (IOError, OSError) as exc:
        raise SpecError("cannot read %s: %s" % (name, exc))


def check_sums(directory):
    """{name: sha256} for every file SHA256SUMS lists, all of them intact."""
    listing = _read(directory, "SHA256SUMS")
    sums = {}
    for number, line in enumerate(listing.splitlines(), 1):
        if not line.strip():
            continue
        match = re.match(r"\A([0-9a-f]{64}) [ *](\S.*)\Z", line)
        if not match:
            raise SpecError("SHA256SUMS line %d is not in the format "
                            "`shasum -a 256 -c` reads" % number)
        digest, name = match.group(1), match.group(2)
        if name.startswith("/") or ".." in name.split("/"):
            raise SpecError("SHA256SUMS names %r, which is outside the "
                            "directory" % name)
        path = os.path.join(directory, *name.split("/"))
        try:
            with open(path, "rb") as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
        except (IOError, OSError):
            raise SpecError("SHA256SUMS lists %s, which is missing" % name)
        if actual != digest:
            raise SpecError("%s does not match SHA256SUMS: this is not an "
                            "intact copy of the published directory" % name)
        sums[name] = digest
    missing = [name for name in REQUIRED if name not in sums]
    if missing:
        raise SpecError("SHA256SUMS does not cover %s" % ", ".join(missing))
    return sums


def _edition(document):
    match = re.search(r"^ARCS-1 · edition ([0-9]{4}-[0-9]{2}-[0-9]{2})",
                      document, re.M)
    if not match:
        raise SpecError("ARCS-1.md states no edition")
    return match.group(1)


def _criteria(document):
    found = re.findall(r"^### (C[0-9]+) — (.+?)\s*$", document, re.M)
    criteria = dict(found)
    expected = ["C%d" % n for n in range(1, len(found) + 1)]
    if not found or [c for c, _ in found] != expected:
        raise SpecError("section 12 does not number its criteria C1..Cn")
    return criteria


def _conclusions(document):
    match = re.search(r"The conclusions are exactly:\n\n((?: {4}.*\n)+)",
                      document)
    if not match:
        raise SpecError("section 11 lists no conclusions")
    return tuple(match.group(1).split())


def _vectors(document):
    vectors = {}
    for block in re.findall(r"```json\n(.*?)\n```", document, re.S):
        try:
            value = json.loads(block)
        except ValueError:
            raise SpecError("a JSON block in section 13 does not parse")
        if isinstance(value, dict) and "vector" in value:
            vectors[value["vector"]] = value
    missing = [name for name in VECTORS if name not in vectors]
    if missing:
        raise SpecError("section 13 lacks the vector(s) %s"
                        % ", ".join(missing))
    return vectors


def check_vectors(vectors):
    """Every disagreement between the section 13 vectors, as sentences."""
    problems = []
    ordering = vectors["canonical-ordering"]
    raw = build.canon(ordering["value"])
    if raw.decode("utf-8") != ordering["canonical"]:
        problems.append("canonical-ordering: the value does not serialise "
                        "to the bytes given")
    if build.sha(ordering["canonical"].encode("utf-8")) != \
            ordering["canonical_sha256"]:
        problems.append("canonical-ordering: the bytes do not hash to the "
                        "digest given")

    minimal = vectors["minimal-record"]
    record = minimal["record"]
    payload = dict((k, v) for k, v in record.items()
                   if k not in ("record_id", "attestation"))
    if build.sha(build.canon(payload)) != minimal["payload_sha256"]:
        problems.append("minimal-record: the payload does not hash to the "
                        "digest given")
    if build.derive_id(record) != minimal["record_id"] or \
            record.get("record_id") != minimal["record_id"]:
        problems.append("minimal-record: the identifier does not derive")

    attestation = vectors["attestation-payload"]
    body_digest = "sha256:" + build.sha(build.canon(record))
    if attestation["body_digest"] != body_digest:
        problems.append("attestation-payload: body_digest is not the digest "
                        "of the minimal record")
    signed = build.canon({"context": build.ATTESTATION_CONTEXT,
                          "body_digest": attestation["body_digest"]})
    if signed.decode("utf-8") != attestation["signed_bytes"]:
        problems.append("attestation-payload: the signed bytes are not "
                        "CANON of the context and the digest")
    if build.sha(attestation["signed_bytes"].encode("utf-8")) != \
            attestation["signed_bytes_sha256"]:
        problems.append("attestation-payload: the signed bytes do not hash "
                        "to the digest given")

    listing = vectors["status-list"]
    if build.derive_id(listing["listing"]) != listing["list_id"] or \
            listing["listing"].get("list_id") != listing["list_id"]:
        problems.append("status-list: the identifier does not derive")
    return problems
