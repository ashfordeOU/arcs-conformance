# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Making artefacts, correct and deliberately wrong.

WHY THE SUITE HAS ITS OWN WORKSHOP
----------------------------------
A negative case is only worth running if it is wrong in exactly one way. A
record with a changed figure that also fails its signature tests the
signature, not the figure. So every mutated artefact here is rebuilt around
its one defect: the identifier re-derived where the defect is not the
identifier, the signature re-made where the defect is not the signature, and
a fresh, signed status list supplied where the question is not standing. An
implementation that lacks the one check a case is about is then the only
kind that can answer `current` to it.

This module is not a verifier, and nothing in it decides a case. It is how
the suite makes the documents it hands over. The reference adapter in
reference/ shares none of it.

THE KEYS ARE TEST KEYS
----------------------
Each private key is the SHA-256 of a published label, so anyone can
regenerate every artefact in the suite byte for byte. That makes the keys
worthless for anything else, which is the point: a key whose private half
can be computed from a README protects nothing, and must never be listed in
an anchor anybody relies on.
"""

import copy
import hashlib
import json

from . import ed25519

# The four strings ARCS-1 section 7 defines, and the section 9 customer
# mark. Typed once, here; tests/test_spec.py holds each to the document.
RECORD_CONTEXT = "aeroskills-harness-dossier/v3"
LIST_CONTEXT = "aeroskills-harness-status-list/v1"
ATTESTATION_CONTEXT = "aero-harness-dossier-attestation/v1"
ANCHOR_SCHEMA = "aero-dossier-trust-anchor/v1"
SPECIMEN_CUSTOMER = "SPECIMEN (not issued to a customer): "

TEST_KEY_LABEL = "ARCS-1 conformance suite test key: "
TEST_ISSUER = "arcs-conformance test key (private half published)"


def canon(value):
    """CANON of ARCS-1 section 3, refusing what that section forbids.

    A float raises ValueError here, as NaN does inside json.dumps: an
    artefact the suite builds correctly carries neither, and a case that
    needs one builds it through loose() so that the choice is visible.
    """
    _integers_only(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _integers_only(value):
    if isinstance(value, float):
        raise ValueError("section 3: no floating-point number appears in "
                         "any artefact")
    if isinstance(value, dict):
        for item in value.values():
            _integers_only(item)
    elif isinstance(value, list):
        for item in value:
            _integers_only(item)


def loose(value, **overrides):
    """A serialisation that is wrong in a chosen way, for negative cases.

    With no overrides it differs from canon() only in letting NaN and the
    infinities through. The overrides are json.dumps keywords.
    """
    options = dict(sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=True)
    options.update(overrides)
    return json.dumps(value, **options).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def id_field(doc):
    return "list_id" if doc.get("context") == LIST_CONTEXT else "record_id"


def prefix_of(doc):
    if doc.get("context") == LIST_CONTEXT:
        return "AHS"
    return "SPECIMEN" if doc.get("specimen") is True else "AHD"


def derive_id(doc, prefix=None, field=None, encode=canon):
    """The section 6 identifier of `doc`, whatever it currently carries."""
    field = field or id_field(doc)
    payload = dict((k, v) for k, v in doc.items()
                   if k not in (field, "attestation"))
    digest = sha(encode(payload))
    return "%s-%s-%s-%s" % (prefix or prefix_of(doc), digest[0:8],
                            digest[8:16], digest[16:24])


def with_id(doc, **derive):
    """A copy of `doc` carrying the identifier its own payload derives."""
    out = copy.deepcopy(doc)
    out.pop("attestation", None)
    field = derive.get("field") or id_field(out)
    out[field] = derive_id(out, **derive)
    return out


class Key(object):
    """An Ed25519 test key regenerated from its label."""

    def __init__(self, label):
        self.label = label
        self.private = hashlib.sha256(
            (TEST_KEY_LABEL + label).encode("utf-8")).digest()
        self.public = ed25519.public_key(self.private)
        self.key_id = "k_" + sha(self.public)[:16]

    def entry(self):
        return {"key_id": self.key_id, "public_key": self.public.hex(),
                "algorithm": "ed25519", "issuer": TEST_ISSUER,
                "note": "test key %r: its private half is the SHA-256 of a "
                        "published label" % self.label}


def attest(doc, key, payload_context=ATTESTATION_CONTEXT,
           attestation_context=ATTESTATION_CONTEXT, encode=canon):
    """A copy of `doc` signed by `key` as section 8 describes.

    The two contexts and the encoder are parameters so that a case can sign
    over the wrong bytes on purpose; with the defaults this is section 8.
    """
    out = copy.deepcopy(doc)
    out.pop("attestation", None)
    body_digest = "sha256:" + sha(encode(out))
    signed = canon({"context": payload_context, "body_digest": body_digest})
    out["attestation"] = {
        "algorithm": "ed25519",
        "context": attestation_context,
        "key_id": key.key_id,
        "public_key": key.public.hex(),
        "issuer": TEST_ISSUER,
        "body_digest": body_digest,
        "signature": ed25519.sign(key.private, signed).hex(),
    }
    return out


def unsigned(doc):
    out = copy.deepcopy(doc)
    out.pop("attestation", None)
    return out


def anchor_text(keys, schema=ANCHOR_SCHEMA):
    """A trust anchor in the shape the published specimen anchor has.

    `schema=None` leaves the field out altogether.
    """
    doc = {}
    if schema is not None:
        doc["schema"] = schema
    doc["scope"] = "conformance-suite test keys; they protect nothing"
    doc["keys"] = [k.entry() for k in keys]
    return json.dumps(doc, ensure_ascii=False, indent=2)


def text(doc):
    """The JSON text a case hands over for `doc`.

    Indented, with the top-level keys in reverse order, so that the text is
    never the canonical form. An implementation that hashes the bytes it was
    handed, rather than CANON of what they say, never reaches `current` on
    a document built here, so it fails every case that asks for `current`.
    """
    reordered = dict(reversed(list(doc.items())))
    return json.dumps(reordered, ensure_ascii=False, indent=2)
