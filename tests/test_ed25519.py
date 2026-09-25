#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The vendored Ed25519, held to RFC 8032 and to its published original.

The suite signs every artefact it hands over and the minimal adapter
verifies them with the same module, so a fault here could make the two
agree on something wrong. These tests hold the module to the RFC's own
vectors, to the negative cases a verifier of untrusted input must refuse
without raising, and to the digest of the file it was copied from, so that
an edit made here is seen rather than inherited.

Run: python3 tests/test_ed25519.py
"""

import hashlib
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import ed25519  # noqa: E402

# SHA-256 of tools/evidence/ed25519.py as Aero Agent Skills publishes it.
ORIGINAL_SHA256 = \
    "7ac927c76ddf04bee4de730c3b982f0b10c9b2fa767ac9e93aa7173decadc0ef"
HEADER_LINES = 11

# RFC 8032 section 7.1, tests 1 to 3: (secret, public, message, signature).
VECTORS = [
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8"
     "821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085a"
     "c1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff"
     "9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]


def h(text):
    return bytes.fromhex(text)


class RFC8032(unittest.TestCase):
    def test_public_keys_derive(self):
        for secret, public, _, _ in VECTORS:
            self.assertEqual(ed25519.public_key(h(secret)).hex(), public)

    def test_signatures_match(self):
        for secret, _, message, signature in VECTORS:
            self.assertEqual(ed25519.sign(h(secret), h(message)).hex(),
                             signature)

    def test_signatures_verify(self):
        for _, public, message, signature in VECTORS:
            self.assertTrue(ed25519.verify(h(public), h(message),
                                           h(signature)))


class RefusesWithoutRaising(unittest.TestCase):
    """What an attacker can hand a verifier, each refused as False."""

    def setUp(self):
        secret, public, message, signature = VECTORS[2]
        self.public, self.message = h(public), h(message)
        self.signature = h(signature)

    def test_flipped_bit(self):
        bad = bytearray(self.signature)
        bad[10] ^= 0x04
        self.assertFalse(ed25519.verify(self.public, self.message, bytes(bad)))

    def test_truncated_signature(self):
        self.assertFalse(ed25519.verify(self.public, self.message,
                                        self.signature[:-1]))

    def test_wrong_key(self):
        other = h(VECTORS[0][1])
        self.assertFalse(ed25519.verify(other, self.message, self.signature))

    def test_tampered_message(self):
        self.assertFalse(ed25519.verify(self.public, self.message + b"\x00",
                                        self.signature))

    def test_scalar_at_or_above_the_order(self):
        order = 2 ** 252 + 27742317777372353535851937790883648493
        s = int.from_bytes(self.signature[32:], "little") + order
        malleated = self.signature[:32] + s.to_bytes(32, "little")
        self.assertFalse(ed25519.verify(self.public, self.message, malleated))

    def test_not_bytes(self):
        self.assertFalse(ed25519.verify("not bytes", self.message,
                                        self.signature))


class VendoredUnmodified(unittest.TestCase):
    def test_body_matches_the_published_original(self):
        path = os.path.join(ROOT, "arcs_conformance", "ed25519.py")
        with open(path, "rb") as fh:
            lines = fh.read().split(b"\n")
        body = b"\n".join(lines[HEADER_LINES:])
        self.assertEqual(hashlib.sha256(body).hexdigest(), ORIGINAL_SHA256)


if __name__ == "__main__":
    unittest.main()
