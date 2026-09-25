#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""A minimal ARCS-1 implementation, written from the specification alone.

WHY THIS EXISTS
---------------
A conformance suite nobody has seen pass is a list of opinions. This file is
the evidence that every normative case in the suite can be passed by an
implementation built from spec/ARCS-1.md and nothing else. It was written
without sight of the issuer's runtime, which is not public, and it shares no
code with the suite except the Ed25519 primitive, which ARCS-1 names and
does not define.

It is minimal on purpose. It is not the reference implementation ARCS-1
mentions, and it is not a product. That it passes shows the suite can be
passed; it says nothing about whether this file is fit to decide anything
about a real record.

HOW IT READS THE PARTS ARCS-1 LEAVES OPEN
-----------------------------------------
Where the specification does not settle a question, this adapter takes the
suite's reading, and each place is marked `reading:` below so that a reader
can see exactly which behaviour comes from the text and which from a choice.
PROTOCOL.md lists the same questions.

Run it as the suite runs any implementation:
    python3 -m arcs_conformance --impl 'python3 reference/adapter.py'
"""

import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir))
from arcs_conformance import ed25519  # noqa: E402

NAME = "arcs-minimal-adapter"
VERSION = "1.0.0"
UNSUPPORTED = 3

RECORD_CONTEXT = "aeroskills-harness-dossier/v3"
LIST_CONTEXT = "aeroskills-harness-status-list/v1"
ATTESTATION_CONTEXT = "aero-harness-dossier-attestation/v1"
ANCHOR_SCHEMA = "aero-dossier-trust-anchor/v1"
SPECIMEN_CUSTOMER = "SPECIMEN (not issued to a customer): "

# Section 5: field -> required.
RECORD_FIELDS = {
    "context": True, "customer": True, "runtime": True, "spec": True,
    "claim": True, "corpora": True, "issued_at": True, "not_before": True,
    "not_after": True, "record_id": True, "binding_integrity": False,
    "specimen": False, "provenance": False, "attestation": False,
}
# Section 10.
LIST_FIELDS = {
    "context": True, "covers_context": True, "sequence": True,
    "as_of": True, "next_update": True, "entries": True, "list_id": True,
    "previous_digest": False, "attestation": False,
}
ATTESTATION_FIELDS = ("algorithm", "context", "key_id", "public_key",
                      "issuer", "body_digest", "signature")
BINDING_FIELDS = ("roles", "bindings", "resolved", "ok")
STATES = {"superseded": 1, "withdrawn": 2}

_INSTANT = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
                      r"[0-9]{2}Z\Z")
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
_SERIAL = re.compile(r"\A(AHD|SPECIMEN)-[0-9a-f]{8}-[0-9a-f]{8}-[0-9a-f]{8}\Z")


class Refused(Exception):
    """The input cannot be read as what it claims to be."""

    def __init__(self, *problems):
        Exception.__init__(self, "; ".join(problems))
        self.problems = list(problems)


# -- section 3 -------------------------------------------------------------

def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Refused("duplicate key %r: section 3 has no serialisation "
                          "for it" % key)
        out[key] = value
    return out


def _no_float(text):
    raise Refused("floating-point number %s: section 3 allows none" % text)


def _no_constant(text):
    raise Refused("%s is not JSON" % text)


def parse(text):
    """JSON text, refusing what section 3 says no artefact contains."""
    if not isinstance(text, str):
        raise Refused("expected JSON text")
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_float=_no_float, parse_constant=_no_constant)
    except ValueError as exc:
        raise Refused("not JSON: %s" % exc)


def canon(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeEncodeError) as exc:
        raise Refused("no canonical form: %s" % exc)


def sha(data):
    return hashlib.sha256(data).hexdigest()


# -- section 4 -------------------------------------------------------------

def instant(value):
    """An instant, or Refused. Never normalised: section 4."""
    if not isinstance(value, str) or not _INSTANT.match(value):
        raise Refused("%r is not YYYY-MM-DDTHH:MM:SSZ" % (value,))
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise Refused("%r is not a date that exists" % (value,))


# -- section 6 -------------------------------------------------------------

def derive_id(doc):
    is_list = doc.get("context") == LIST_CONTEXT
    field = "list_id" if is_list else "record_id"
    payload = dict((k, v) for k, v in doc.items()
                   if k not in (field, "attestation"))
    digest = sha(canon(payload))
    if is_list:
        prefix = "AHS"
    else:
        prefix = "SPECIMEN" if doc.get("specimen") is True else "AHD"
    return "%s-%s-%s-%s" % (prefix, digest[0:8], digest[8:16], digest[16:24])


# -- shapes: sections 5, 8, 9, 10 -------------------------------------------

def _is_int(value):
    return type(value) is int


def _fields(doc, table, what):
    problems = []
    for name in sorted(set(doc) - set(table)):
        problems.append("%s carries %r, which it does not define"
                        % (what, name))
    for name, required in sorted(table.items()):
        if required and name not in doc:
            problems.append("%s lacks %r" % (what, name))
    return problems


def _instants(doc, names, problems):
    parsed = {}
    for name in names:
        if name in doc:
            try:
                parsed[name] = instant(doc[name])
            except Refused as exc:
                problems.extend("%s: %s" % (name, p) for p in exc.problems)
    return parsed


def attestation_problems(att):
    if not isinstance(att, dict):
        return ["attestation is not an object"]
    problems = []
    for name in sorted(set(att) ^ set(ATTESTATION_FIELDS)):
        problems.append("attestation %s %r" % (
            "carries undefined field" if name in att else "lacks", name))
    if att.get("algorithm") != "ed25519":
        problems.append("attestation algorithm is not ed25519")
    if att.get("context") != ATTESTATION_CONTEXT:
        problems.append("attestation context is not %s" % ATTESTATION_CONTEXT)
    if not re.match(r"\Ak_[0-9a-f]{16}\Z", str(att.get("key_id"))):
        problems.append("key_id is not k_ and 16 hex characters")
    if not re.match(r"\A[0-9a-fA-F]{64}\Z", str(att.get("public_key"))):
        problems.append("public_key is not 32 bytes of hex")
    if not isinstance(att.get("issuer"), str):
        problems.append("issuer is not a string")
    if not re.match(r"\Asha256:[0-9a-f]{64}\Z", str(att.get("body_digest"))):
        problems.append("body_digest is not sha256: and 64 hex characters")
    if not re.match(r"\A[0-9a-fA-F]{128}\Z", str(att.get("signature"))):
        problems.append("signature is not 64 bytes of hex")
    return problems


def record_problems(rec):
    """Every section 5 and section 9 problem with a record, at once."""
    if not isinstance(rec, dict):
        return ["a record is a JSON object"]
    problems = _fields(rec, RECORD_FIELDS, "the record")
    if rec.get("context") != RECORD_CONTEXT:
        problems.append("context is not %s" % RECORD_CONTEXT)
    for name in ("customer", "runtime", "record_id"):
        if name in rec and not isinstance(rec[name], str):
            problems.append("%s is not a string" % name)
    if rec.get("customer") == "":
        problems.append("customer is empty")
    if "spec" in rec and rec["spec"] != "ARCS-1":
        problems.append("spec is not ARCS-1")
    if "claim" in rec and rec["claim"] != "claim@1":
        problems.append("claim is not claim@1")
    corpora = rec.get("corpora")
    if "corpora" in rec:
        if not isinstance(corpora, dict) or not corpora:
            problems.append("corpora names no corpus")
        else:
            for name, digest in sorted(corpora.items()):
                if not name or not isinstance(digest, str) or \
                        not _HEX64.match(digest):
                    problems.append("corpus %r is not named by a lowercase "
                                    "SHA-256" % name)
    when = _instants(rec, ("issued_at", "not_before", "not_after"), problems)
    if "issued_at" in when and "not_before" in when and \
            when["not_before"] < when["issued_at"]:
        problems.append("not_before is earlier than issued_at")
    if "not_before" in when and "not_after" in when and \
            not when["not_after"] > when["not_before"]:
        problems.append("the window covers no time")
    if "binding_integrity" in rec:
        binding = rec["binding_integrity"]
        # reading: the four fields section 5 names, and no others.
        if not isinstance(binding, dict) or \
                sorted(binding) != sorted(BINDING_FIELDS):
            problems.append("binding_integrity is not roles, bindings, "
                            "resolved and ok")
        else:
            for name in ("roles", "bindings", "resolved"):
                if not _is_int(binding[name]) or binding[name] < 0:
                    problems.append("binding_integrity %s is not a count"
                                    % name)
            if binding["ok"] is not True:
                problems.append("binding_integrity ok is not true")
    if "specimen" in rec and rec["specimen"] is not True:
        problems.append("specimen is present and not true")
    if "provenance" in rec and not isinstance(rec["provenance"], dict):
        problems.append("provenance is not an object")
    if "attestation" in rec:
        problems.extend(attestation_problems(rec["attestation"]))
    if isinstance(rec.get("customer"), str) and \
            isinstance(rec.get("record_id"), str):
        marks = (rec.get("specimen") is True,
                 rec["customer"].startswith(SPECIMEN_CUSTOMER),
                 rec["record_id"].startswith("SPECIMEN-"))
        if len(set(marks)) != 1:
            problems.append("the three specimen marks disagree (flag %s, "
                            "customer %s, serial %s)" % marks)
    return problems


def finding_problems(serial, finding):
    what = "finding for %s" % serial
    if not isinstance(finding, dict):
        return [what + " is not an object"]
    allowed = ("state", "at", "reason", "superseded_by")
    problems = ["%s carries %r" % (what, n) for n in sorted(set(finding))
                if n not in allowed]
    state = finding.get("state")
    if state not in STATES:
        problems.append("%s has undefined state %r" % (what, state))
    try:
        instant(finding.get("at"))
    except Refused as exc:
        problems.extend("%s at: %s" % (what, p) for p in exc.problems)
    reason = finding.get("reason")
    if not isinstance(reason, str) or len(reason) > 200:
        problems.append("%s reason is not a string of at most 200 "
                        "characters" % what)
    successor = finding.get("superseded_by")
    if state == "superseded" and not (isinstance(successor, str) and
                                      successor):
        problems.append("%s is superseded by nothing" % what)
    if state != "superseded" and "superseded_by" in finding:
        problems.append("%s names a successor it is not superseded by" % what)
    return problems


def list_problems(lst):
    """Every section 10 problem with a status list, at once."""
    if not isinstance(lst, dict):
        return ["a status list is a JSON object"]
    problems = _fields(lst, LIST_FIELDS, "the status list")
    if lst.get("context") != LIST_CONTEXT:
        problems.append("context is not %s" % LIST_CONTEXT)
    covers = lst.get("covers_context")
    if "covers_context" in lst and not (isinstance(covers, str) and covers):
        problems.append("covers_context is not a string")
    sequence = lst.get("sequence")
    if "sequence" in lst and not (_is_int(sequence) and sequence >= 1):
        problems.append("sequence is not a positive integer")
    when = _instants(lst, ("as_of", "next_update"), problems)
    if len(when) == 2 and not when["next_update"] > when["as_of"]:
        problems.append("next_update is not later than as_of")
    entries = lst.get("entries")
    if "entries" in lst:
        if not isinstance(entries, dict):
            problems.append("entries is not an object")
        else:
            for serial, finding in sorted(entries.items()):
                # reading: an entry is keyed by a serial of section 6's form.
                if not _SERIAL.match(serial):
                    problems.append("entry %r is not a record serial" % serial)
                problems.extend(finding_problems(serial, finding))
    if "previous_digest" in lst and not (
            isinstance(lst["previous_digest"], str) and
            _HEX64.match(lst["previous_digest"])):
        problems.append("previous_digest is not a SHA-256")
    if "attestation" in lst:
        problems.extend(attestation_problems(lst["attestation"]))
    if not problems and derive_id(lst) != lst.get("list_id"):
        problems.append("list_id does not recompute")
    return problems


# -- section 8 and step 0 --------------------------------------------------

def load_anchor(text):
    """{key_id: public key bytes}. Refused unless it names its schema."""
    doc = parse(text)
    if not isinstance(doc, dict) or doc.get("schema") != ANCHOR_SCHEMA:
        raise Refused("the anchor is not an %s document" % ANCHOR_SCHEMA)
    keys = doc.get("keys")
    if not isinstance(keys, list):
        raise Refused("the anchor carries no keys array")
    trusted = {}
    for entry in keys:
        public = entry.get("public_key") if isinstance(entry, dict) else None
        if not isinstance(public, str) or \
                not re.match(r"\A[0-9a-fA-F]{64}\Z", public):
            raise Refused("an anchor entry carries no public key")
        if entry.get("algorithm", "ed25519") != "ed25519":
            raise Refused("an anchor entry is not an Ed25519 key")
        raw = bytes.fromhex(public)
        key_id = "k_" + sha(raw)[:16]
        # reading: an entry whose key_id is not its key's is not trusted,
        # and an anchor that contradicts itself is not loaded at all.
        if entry.get("key_id", key_id) != key_id:
            raise Refused("an anchor entry's key_id is not its key's")
        trusted[key_id] = raw
    return trusted


def authenticate(doc, trusted):
    """('unsigned' | 'authentic' | 'failed', key_id or None, problem)."""
    att = doc.get("attestation")
    if att is None:
        return "unsigned", None, None
    body = dict((k, v) for k, v in doc.items() if k != "attestation")
    if "sha256:" + sha(canon(body)) != att["body_digest"]:
        return "failed", None, "the body does not hash to body_digest"
    key = trusted.get(att["key_id"])
    if key is None:
        return "failed", None, "key %s is not in the anchor" % att["key_id"]
    if bytes.fromhex(att["public_key"]) != key:
        return "failed", None, "the record names a key it was not signed by"
    signed = canon({"context": ATTESTATION_CONTEXT,
                    "body_digest": att["body_digest"]})
    if not ed25519.verify(key, signed, bytes.fromhex(att["signature"])):
        return "failed", None, "the signature does not verify"
    return "authentic", att["key_id"], None


# -- section 11 ------------------------------------------------------------

def window(rec, at):
    if at < instant(rec["not_before"]):
        return "not_yet_valid"
    # reading: the window is half-open, so at not_after it has closed.
    if at >= instant(rec["not_after"]):
        return "expired"
    return "valid"


def verify_record(req):
    try:
        trusted = load_anchor(req["anchor"])                       # step 0
        at = instant(req["at"])
        rec = parse(req["document"])
    except Refused as exc:
        return "refused", exc.problems
    problems = record_problems(rec)                                # step 1
    if problems:
        return "refused", problems
    if derive_id(rec) != rec["record_id"]:                         # step 2
        return "unsound_id", ["record_id does not recompute"]
    signed, record_key, why = authenticate(rec, trusted)           # step 3
    if signed == "failed":
        return "unauthenticated", [why]
    if rec["context"] != RECORD_CONTEXT:                           # step 4
        return "refused", ["not a record"]
    open_ = window(rec, at)                                        # step 5
    if req.get("status_list") is None:
        # reading: with no list there is no assurance to grant (section 10).
        if signed == "unsigned":
            return "unauthenticated", ["the record is not signed"]
        if open_ != "valid":
            return open_, []
        return "unknown", ["no status list: standing cannot be read"]
    return standing(rec, record_key, signed, open_, at, trusted,
                    req["status_list"])


def standing(rec, record_key, signed, open_, at, trusted, list_text):
    try:                                                           # 6.1
        lst = parse(list_text)
    except Refused as exc:
        return "unknown", exc.problems
    problems = list_problems(lst)
    if problems:
        return "unknown", problems
    list_signed, list_key, why = authenticate(lst, trusted)
    if lst["covers_context"] != rec["context"]:                    # 6.2
        return "unknown", ["the list does not cover this record's context"]
    # reading: a list whose signature fails, or that is unsigned, is
    # nobody's; it governs an unsigned record and no signed one.
    if record_key != list_key:                                     # 6.3
        return "unknown", ["the record and the list are not one key's"]
    finding = lst["entries"].get(rec["record_id"])                 # 6.4
    if finding is not None and instant(finding["at"]) <= at:
        return finding["state"], [finding["reason"]]
    if signed != "authentic" or list_signed != "authentic":        # 6.5
        return "unauthenticated", [why or "the record or list is unsigned"]
    if instant(rec["issued_at"]) > instant(lst["as_of"]):
        return "unknown", ["the record postdates the list"]
    if at > instant(lst["next_update"]):
        return "stale", ["read after the list's next_update"]
    if open_ != "valid":                                           # 6.6
        return open_, []
    return "current", []


def relied(conclusion):
    return conclusion == "current"


# -- the other operations --------------------------------------------------

def matches(req):
    try:
        rec = parse(req["document"])
    except Refused:
        return False
    if record_problems(rec) or derive_id(rec) != rec["record_id"]:
        return False
    if rec.get("specimen") is True:
        return False
    # reading: digest for digest, the corpora the record names.
    corpora = req.get("corpora") or {}
    return all(corpora.get(name) == digest
               for name, digest in rec["corpora"].items())


def check_successor(req):
    try:
        previous = parse(req["previous"])
        successor = parse(req["successor"])
    except Refused as exc:
        return False, exc.problems
    problems = ["previous: " + p for p in list_problems(previous)]
    problems += ["successor: " + p for p in list_problems(successor)]
    if problems:
        return False, problems
    if successor["sequence"] != previous["sequence"] + 1:
        problems.append("the sequence does not advance by one")
    if successor["covers_context"] != previous["covers_context"]:
        problems.append("the successor covers another context")
    # reading: a successor is chained; section 10 makes the field optional
    # only because the first list has nothing to chain to.
    if successor.get("previous_digest") != sha(canon(previous)):
        problems.append("previous_digest is not the predecessor's digest")
    if instant(successor["as_of"]) < instant(previous["as_of"]):
        problems.append("the successor was cut before its predecessor")
    for serial, old in sorted(previous["entries"].items()):
        new = successor["entries"].get(serial)
        if new is None:
            problems.append("the finding for %s is dropped" % serial)
        elif STATES[new["state"]] < STATES[old["state"]]:
            problems.append("the finding for %s is softened" % serial)
        elif new["state"] == old["state"] and \
                instant(new["at"]) > instant(old["at"]):
            # reading: a later effective instant weakens the finding.
            problems.append("the finding for %s takes effect later" % serial)
    return not problems, problems


def build_record(req):
    fields = parse(req["fields"])
    if not isinstance(fields, dict):
        raise Refused("the fields are not an object")
    for name in ("record_id", "attestation"):
        if name in fields:
            raise Refused("%s is derived or added later, never supplied"
                          % name)
    rec = dict(fields)
    rec["record_id"] = derive_id(rec)
    problems = record_problems(rec)
    if problems:
        raise Refused(*problems)
    return canon(rec).decode("utf-8")


# -- the protocol ------------------------------------------------------------

def answer(req):
    op = req.get("op")
    if op == "describe":
        return {"name": NAME, "version": VERSION}
    if op == "canonicalise":
        return {"canonical_hex": canon(parse(req["value"])).hex()}
    if op == "derive_id":
        doc = parse(req["document"])
        if not isinstance(doc, dict):
            raise Refused("not an object")
        return {"id": derive_id(doc)}
    if op == "verify_record":
        conclusion, problems = verify_record(req)
        return {"conclusion": conclusion, "relied": relied(conclusion),
                "problems": problems}
    if op == "reliance":
        return {"relied": relied(req["conclusion"])}
    if op == "matches":
        return {"matches": matches(req)}
    if op == "check_successor":
        accepted, problems = check_successor(req)
        return {"accepted": accepted, "problems": problems}
    if op == "build_record":
        return {"document": build_record(req)}
    return None


def main():
    req = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    try:
        response = answer(req)
    except Refused as exc:
        response = {"refused": True, "problems": exc.problems}
    if response is None:
        sys.stderr.write("unsupported operation %r\n" % req.get("op"))
        return UNSUPPORTED
    sys.stdout.write(json.dumps(response, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
