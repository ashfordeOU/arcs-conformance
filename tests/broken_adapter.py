#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The minimal adapter with named defects, for the suite's own tests.

WHY IT EXISTS
-------------
A suite every implementation passes has shown nothing. Each defect below is
one a real verifier could plausibly ship, most of them the very mistake a
paragraph of ARCS-1 names, and tests/test_broken.py pins exactly which cases
each one fails, alone and in combination. The exception is hashes-the-text,
which breaks nearly everything; for it the test pins the one property
PROTOCOL.md states, that it never reaches `current`.

Five of them exist for the controls. Each of no-numbers-in-records,
binding-integrity-undefined, escaped-identifiers, first-anchored-key-only
and lists-under-first-key-only mishandles something a control carries and
a plain sound record does not, so its pin is what holds that control to its
note. A case no defect here fails is not proven to have teeth by this file:
tests/test_expectations.py pins what each case accepts, and
tests/test_blind.py that no constant answer passes a criterion.

Usage: broken_adapter.py DEFECT[,DEFECT...]    (the request on stdin)
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "reference"))
import adapter as ref  # noqa: E402

DEFECTS = {}


def defect(name):
    def register(patch):
        DEFECTS[name] = patch
        return patch
    return register


@defect("hashes-the-text")
def _hashes_the_text():
    """Hashes a document as it arrived, not CANON of what it says."""
    def canon(value):
        return json.dumps(value, ensure_ascii=False,
                          indent=2).encode("utf-8")
    ref.canon = canon


@defect("utf16-key-order")
def _utf16_key_order():
    """Keys sorted by UTF-16 code unit, as a JavaScript sort would."""
    def reorder(value):
        if isinstance(value, dict):
            return dict((k, reorder(value[k])) for k in
                        sorted(value, key=lambda k: k.encode("utf-16-be")))
        if isinstance(value, list):
            return [reorder(item) for item in value]
        return value

    def canon(value):
        try:
            return json.dumps(reorder(value), separators=(",", ":"),
                              ensure_ascii=False,
                              allow_nan=False).encode("utf-8")
        except (ValueError, UnicodeEncodeError) as exc:
            raise ref.Refused("no canonical form: %s" % exc)
    ref.canon = canon


@defect("escaped-identifiers")
def _escaped_identifiers():
    """Derives identifiers with json.dumps's default, non-ASCII escaped."""
    def derive_id(doc):
        is_list = doc.get("context") == ref.LIST_CONTEXT
        field = "list_id" if is_list else "record_id"
        payload = dict((k, v) for k, v in doc.items()
                       if k not in (field, "attestation"))
        digest = ref.sha(json.dumps(payload, sort_keys=True,
                                    separators=(",", ":")).encode("ascii"))
        if is_list:
            prefix = "AHS"
        else:
            prefix = "SPECIMEN" if doc.get("specimen") is True else "AHD"
        return "%s-%s-%s-%s" % (prefix, digest[0:8], digest[8:16],
                                digest[16:24])
    ref.derive_id = derive_id


@defect("lenient-json")
def _lenient_json():
    """A permissive decoder: floats accepted, the last duplicate wins."""
    def parse(text):
        try:
            return json.loads(text)
        except ValueError as exc:
            raise ref.Refused("not JSON: %s" % exc)
    ref.parse = parse


@defect("normalises-instants")
def _normalises_instants():
    """Repairs an instant instead of refusing it."""
    strict = ref.instant

    def instant(value):
        if isinstance(value, str):
            value = value.upper().replace("+00:00", "Z")
            value = re.sub(r"\.[0-9]+Z\Z", "Z", value)
        return strict(value)
    ref.instant = instant


@defect("ignores-undefined-fields")
def _ignores_undefined_fields():
    """Reads the fields it knows and skips the rest."""
    def fields(doc, table, what):
        return ["%s lacks %r" % (what, name)
                for name, required in sorted(table.items())
                if required and name not in doc]
    ref._fields = fields


@defect("no-numbers-in-records")
def _no_numbers_in_records():
    """Reads section 3's ban on floating point as a ban on every number."""
    strict = ref.record_problems

    def numbers(value):
        if isinstance(value, dict):
            return any(numbers(v) for v in value.values())
        if isinstance(value, list):
            return any(numbers(v) for v in value)
        return ref._is_int(value)

    def record_problems(rec):
        problems = strict(rec)
        if numbers(rec):
            problems.append("the record carries a number")
        return problems
    ref.record_problems = record_problems


@defect("binding-integrity-undefined")
def _binding_integrity_undefined():
    """Works from a table of section 5 that lacks binding_integrity."""
    table = dict(ref.RECORD_FIELDS)
    del table["binding_integrity"]
    ref.RECORD_FIELDS = table


@defect("specimen-flag-only")
def _specimen_flag_only():
    """Checks the flag against the serial and never reads the customer."""
    strict = ref.record_problems

    def record_problems(rec):
        problems = [p for p in strict(rec)
                    if not p.startswith("the three specimen marks")]
        if isinstance(rec, dict) and isinstance(rec.get("record_id"), str) \
                and (rec.get("specimen") is True) != \
                rec["record_id"].startswith("SPECIMEN-"):
            problems.append("flag and serial disagree")
        return problems
    ref.record_problems = record_problems


@defect("trust-embedded-key")
def _trust_embedded_key():
    """Verifies under the key the record carries; the anchor is ignored."""
    def load_anchor(text):
        return {}

    def authenticate(doc, trusted):
        att = doc.get("attestation")
        if att is None:
            return "unsigned", None, None
        body = dict((k, v) for k, v in doc.items() if k != "attestation")
        if "sha256:" + ref.sha(ref.canon(body)) != att["body_digest"]:
            return "failed", None, "the body does not hash to body_digest"
        signed = ref.canon({"context": ref.ATTESTATION_CONTEXT,
                            "body_digest": att["body_digest"]})
        if not ref.ed25519.verify(bytes.fromhex(att["public_key"]), signed,
                                  bytes.fromhex(att["signature"])):
            return "failed", None, "the signature does not verify"
        return "authentic", att["key_id"], None
    ref.load_anchor = load_anchor
    ref.authenticate = authenticate


@defect("first-anchored-key-only")
def _first_anchored_key_only():
    """Trusts the first key an anchor lists and reads no further."""
    strict = ref.load_anchor

    def load_anchor(text):
        return dict(list(strict(text).items())[:1])
    ref.load_anchor = load_anchor


@defect("lists-under-first-key-only")
def _lists_under_first_key_only():
    """Reads a record under the anchor and a list under its first key only.

    The mistake of an implementation that keeps one configured key for the
    issuer's lists beside the anchor it checks records against.
    """
    strict = ref.standing

    def standing(rec, record_key, signed, open_, at, trusted, list_text):
        first = dict(list(trusted.items())[:1])
        return strict(rec, record_key, signed, open_, at, first, list_text)
    ref.standing = standing


@defect("doubt-launders-findings")
def _doubt_launders_findings():
    """Asks whether it could check before asking what the list says."""
    def standing(rec, record_key, signed, open_, at, trusted, list_text):
        try:
            lst = ref.parse(list_text)
        except ref.Refused as exc:
            return "unknown", exc.problems
        if ref.list_problems(lst):
            return "unknown", []
        list_signed, list_key, _ = ref.authenticate(lst, trusted)
        if lst["covers_context"] != rec["context"] or record_key != list_key:
            return "unknown", []
        if signed != "authentic" or list_signed != "authentic":
            return "unauthenticated", []
        if ref.instant(rec["issued_at"]) > ref.instant(lst["as_of"]):
            return "unknown", []
        if at > ref.instant(lst["next_update"]):
            return "stale", []
        finding = lst["entries"].get(rec["record_id"])
        if finding is not None and ref.instant(finding["at"]) <= at:
            return finding["state"], []
        return (open_ if open_ != "valid" else "current"), []
    ref.standing = standing


@defect("relies-on-stale")
def _relies_on_stale():
    """Treats a stale answer as good enough to act on."""
    ref.relied = lambda conclusion: conclusion in ("current", "stale")


@defect("relied-means-checked")
def _relied_means_checked():
    """Sets the verifier's boolean when the document checked out.

    The reliance operation still answers correctly, so C12's own nine
    questions pass; only the boolean on a verify_record answer is wrong.
    """
    strict = ref.answer

    def answer(req):
        response = strict(req)
        if req.get("op") == "verify_record" and response is not None:
            response["relied"] = response["conclusion"] not in (
                "refused", "unsound_id", "unauthenticated")
        return response
    ref.answer = answer


@defect("drops-findings-quietly")
def _drops_findings_quietly():
    """Accepts a successor that no longer mentions a finding."""
    strict = ref.check_successor

    def check_successor(req):
        accepted, problems = strict(req)
        problems = [p for p in problems if not p.endswith("is dropped")]
        return not problems, problems
    ref.check_successor = check_successor


@defect("clock")
def _clock():
    """Answers about now, whatever instant it was asked about."""
    strict = ref.verify_record

    def verify_record(req):
        now = datetime.datetime.now(datetime.timezone.utc)
        req = dict(req, at=now.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return strict(req)
    ref.verify_record = verify_record


def main(argv):
    names = [n for n in (argv[1] if len(argv) > 1 else "").split(",") if n]
    unknown = [n for n in names if n not in DEFECTS]
    if not names or unknown:
        sys.stderr.write("usage: broken_adapter.py DEFECT[,DEFECT...]; "
                         "known: %s\n" % ", ".join(sorted(DEFECTS)))
        return 2
    for name in names:
        DEFECTS[name]()
    return ref.main()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
