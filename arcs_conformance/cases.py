# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The catalogue: every case, the clause it cites, and what it expects.

WHAT A CASE IS
--------------
One request to the implementation under test, the clause of ARCS-1 that
makes the request a fair question, and the set of answers that clause
allows. Where the specification names the answer, the set has one member.
Where it says only that a document is refused, the set is every refusing
answer, because naming one of them would be the suite writing the
specification rather than testing it.

THREE BASES, KEPT APART
-----------------------
`criterion`  the test section 12 itself states for the criterion.
`must`       a requirement the text states elsewhere, or a consequence it
             spells out, that the criterion's own test does not reach.
`reading`    a question ARCS-1 does not settle. The suite records what the
             implementation answered against the suite's reading, reports it
             under its own heading, and counts it towards no criterion. A
             reading is a finding about the specification, never about the
             implementation, and the day an edition settles it the case
             becomes `must` or goes.

CONTROLS, AND WHY EVERY CRITERION HAS SOMETHING TO GET RIGHT
------------------------------------------------------------
A case that asks only for a refusal is passed by a program that refuses
everything. Where every case under a criterion is of that kind, the
criterion would hold for a program that checks nothing, and a criterion's
verdict is exactly what a reader will quote. So each such criterion also
carries a control, named `-control-`: the same artefacts with the one
defect absent, which must come out `current` (or, where the negative is
about a finding, must come out as that finding). A refusal then counts only
beside an acceptance of its twin. tests/test_blind.py holds the whole
catalogue to this: for every criterion and every operation it uses, no
constant answer passes all of that criterion's cases of that operation. The
one exception is C5's corpus-matching question, where section 9 states only
the false side and the suite has nothing else to ask (PROTOCOL.md, question
11).

WHY THE ARTEFACTS ARE BUILT HERE AND NOT STORED
-----------------------------------------------
Every artefact is regenerated from the specification's own vectors and the
published test keys each time the catalogue is built, so a stored file can
never drift from the rule it was made to break. `--dump` writes them out
for anyone who wants to read them without running Python.
"""

import copy
import datetime
import json

from . import build

_DROP = object()

NORMATIVE = ("criterion", "must")
BASES = NORMATIVE + ("reading",)
OPERATIONS = ("canonicalise", "derive_id", "verify_record", "reliance",
              "matches", "check_successor", "build_record")

# The protocol's one addition to the nine conclusions of section 11: the
# answer for a document refused before any of them could be reached.
REFUSED = "refused"

# The criterion whose rule rides on every verify_record answer: the reliance
# boolean is true for `current` and nothing else. runner.reliance judges it
# on each answer and charges the judgement here.
RELIANCE_CRITERION = "C12"

# What an implementation has to show for each criterion to hold, in one
# plain sentence. The README's coverage table prints these beside the counts
# (tools/gen_readme.py). They describe the cases below and change none of
# them; tests/test_docs.py holds the keys to the criteria section 12 numbers.
SUMMARY = {
    "C1": "Serialises values to the exact bytes §3 defines, and refuses a "
          "float, a NaN or a key given twice, whether asked directly or "
          "inside a signed record.",
    "C2": "Refuses an instant with an offset, a fractional second, lower "
          "case or a date that does not exist, in a record, a status list "
          "or a build, rather than repairing it.",
    "C3": "Refuses a record that adds a field, lacks a required one or "
          "carries a malformed value, even when its identifier is sound.",
    "C4": "Derives identifiers from the document alone, and finds a record "
          "unsound when its serial does not recompute, however it was "
          "altered.",
    "C5": "Refuses a specimen whose three marks disagree, and never matches "
          "a specimen against any corpus set.",
    "C6": "Refuses a window that is empty, inverted or opens before issue, "
          "and answers not_yet_valid or expired outside a sound one.",
    "C7": "Refuses a document offered in the wrong place or signed for "
          "another purpose, however valid its signature.",
    "C8": "Trusts only the keys the verifier's anchor lists, and refuses "
          "forged, relabelled, truncated, bit-flipped and malleated "
          "signatures (a malleated signature is one rewritten, without the "
          "key, into a second form a careless verifier still accepts) and "
          "bodies edited after signing.",
    "C9": "Refuses a genuine record against an anchor with no keys, or "
          "against a document that is not an anchor.",
    "C10": "Takes standing from the status list alone: the same record is "
           "current, withdrawn or superseded as the list says, from the "
           "instant a finding takes effect.",
    "C11": "Keeps a withdrawal in force through a stale or unsigned list, "
           "and gives no assurance from a list that is stale, unsigned or "
           "malformed.",
    "C12": "Returns a reliance boolean that is true for current and false "
           "for every other conclusion, on every verify_record answer.",
    "C13": "Answers unknown, never current, when the list covers another "
           "scope, comes from another issuer or was cut before the record "
           "was issued.",
    "C14": "Accepts a successor list that keeps or escalates every finding, "
           "and refuses one that softens or drops a finding, breaks the "
           "chain or skips a sequence.",
    "C15": "Builds the same bytes twice from the same inputs, and answers "
           "about the instant it is asked about, in 2001 or 2098, whatever "
           "the clock says.",
}

AT = "2026-10-01T00:00:00Z"
AFTER_NEXT_UPDATE = "2026-11-01T00:00:00Z"
AFTER_WINDOW = "2027-01-01T00:00:00Z"
LONG_NEXT_UPDATE = "2027-01-31T00:00:00Z"
OTHER_PURPOSE = "example-licence-signature/v1"
OLDER_RECORD_CONTEXT = "aeroskills-harness-dossier/v2"


class Case(object):
    """One request, the clause behind it, and the answers it allows."""

    def __init__(self, cid, criterion, clause, basis, op, request, expect,
                 note, repeat=1):
        if basis not in BASES:
            raise ValueError("unknown basis %r" % basis)
        if op not in OPERATIONS:
            raise ValueError("unknown operation %r" % op)
        self.id = cid
        self.criterion = criterion
        self.clause = clause
        self.basis = basis
        self.op = op
        self.request = request
        self.expect = expect
        self.note = note
        self.repeat = repeat
        # Every answer a verify_record response may give at all: the nine
        # conclusions of section 11 and `refused`. Set by catalogue().
        self.vocabulary = ()

    @property
    def normative(self):
        return self.basis in NORMATIVE

    def to_dict(self):
        return {"id": self.id, "criterion": self.criterion,
                "clause": self.clause, "basis": self.basis, "op": self.op,
                "request": self.request, "expect": self.expect,
                "note": self.note, "repeat": self.repeat}


def _without(values, *removed):
    return tuple(v for v in values if v not in removed)


def _later(instant, seconds):
    """`instant` moved on by `seconds`, in the section 4 form."""
    form = "%Y-%m-%dT%H:%M:%SZ"
    moved = datetime.datetime.strptime(instant, form) + \
        datetime.timedelta(seconds=seconds)
    return moved.strftime(form)


def _midpoint(start, end):
    """The instant halfway through a window, to the second."""
    form = "%Y-%m-%dT%H:%M:%SZ"
    first = datetime.datetime.strptime(start, form)
    span = datetime.datetime.strptime(end, form) - first
    half = datetime.timedelta(seconds=int(span.total_seconds()) // 2)
    return (first + half).strftime(form)


class _Kit(object):
    """The keys, anchors and base artefacts every case is cut from."""

    def __init__(self, spec):
        self.spec = spec
        self.conclusions = spec.conclusions
        self.refusing = _without(spec.conclusions, "current") + (REFUSED,)
        self.issuer = build.Key("issuer")
        self.second = build.Key("second issuer")
        self.forger = build.Key("forger")
        self.anchor = build.anchor_text([self.issuer, self.second])
        self.minimal = copy.deepcopy(spec.vectors["minimal-record"]["record"])
        self.vector_list = copy.deepcopy(
            spec.vectors["status-list"]["listing"])
        self.record = build.attest(self.minimal, self.issuer)
        self.second_record = self.signed(customer="Example Avionics SAS")
        self.third_record = self.signed(customer="Example Propulsion AB")
        self.finding = self.vector_list["entries"][self.minimal["record_id"]]
        self.empty = self.signed_list({})
        self.empty_long = self.signed_list({}, next_update=LONG_NEXT_UPDATE)
        self.withdrawing = build.attest(self.vector_list, self.issuer)
        self.withdrawing_long = self.signed_list(
            self.vector_list["entries"], next_update=LONG_NEXT_UPDATE)
        self.specimen_marked = self.variant(
            customer=build.SPECIMEN_CUSTOMER + self.minimal["customer"],
            specimen=True)
        # Read from the specimen, never typed: a re-issued specimen with
        # another window moves this instant with it.
        self.in_specimen_window = _midpoint(spec.specimen["not_before"],
                                            spec.specimen["not_after"])

    # -- records ---------------------------------------------------------
    def variant(self, encode=build.canon, **changes):
        """The minimal record with `changes`, its identifier re-derived."""
        record = copy.deepcopy(self.minimal)
        for name, value in changes.items():
            if value is _DROP:
                record.pop(name, None)
            else:
                record[name] = value
        return build.with_id(record, encode=encode)

    def signed(self, key=None, encode=build.canon, **changes):
        return build.attest(self.variant(encode=encode, **changes),
                            key or self.issuer, encode=encode)

    def fields(self, **changes):
        """Build inputs: the minimal record without its identifier."""
        record = copy.deepcopy(self.minimal)
        record.pop("record_id")
        for name, value in changes.items():
            if value is _DROP:
                record.pop(name, None)
            else:
                record[name] = value
        return record

    # -- status lists ----------------------------------------------------
    def status(self, entries, **changes):
        listing = copy.deepcopy(self.vector_list)
        listing["entries"] = copy.deepcopy(entries)
        listing.update(changes)
        return build.with_id(listing, field="list_id", prefix="AHS")

    def signed_list(self, entries, key=None, **changes):
        return build.attest(self.status(entries, **changes),
                            key or self.issuer)


def _doc(value):
    return value if isinstance(value, str) else build.text(value)


def catalogue(spec):
    """Every case, in the order the criteria are numbered."""
    kit = _Kit(spec)
    cases = []
    for section in (_c1, _c2, _c3, _c4, _c5, _c6, _c7, _c8, _c9, _c10,
                    _c11, _c12, _c13, _c14, _c15):
        cases.extend(section(kit))
    seen = set()
    for case in cases:
        if case.id in seen:
            raise ValueError("duplicate case id %s" % case.id)
        seen.add(case.id)
        case.vocabulary = tuple(kit.conclusions) + (REFUSED,)
    return cases


# -- request helpers -------------------------------------------------------

def _verify(cid, criterion, clause, basis, note, document, anchor, at,
            status_list=None, expect=None):
    request = {"document": _doc(document), "anchor": anchor, "at": at}
    if status_list is not None:
        request["status_list"] = _doc(status_list)
    return Case(cid, criterion, clause, basis, "verify_record", request,
                {"conclusion": list(expect)}, note)


def _canon(cid, criterion, clause, basis, note, value_text, expected_hex=None):
    expect = {"refused": True} if expected_hex is None else \
        {"canonical_hex": expected_hex}
    return Case(cid, criterion, clause, basis, "canonicalise",
                {"value": value_text}, expect, note)


def _canon_hex(value_text):
    return build.canon(json.loads(value_text)).hex()


def _derive(cid, criterion, clause, basis, note, document, expected):
    return Case(cid, criterion, clause, basis, "derive_id",
                {"document": _doc(document)}, {"id": expected}, note)


def _build(cid, criterion, clause, basis, note, fields, record_id=None,
           repeat=1):
    if record_id is None:
        expect = {"refused": True}
    else:
        expect = {"record_id": record_id, "fields": fields}
    return Case(cid, criterion, clause, basis, "build_record",
                {"fields": json.dumps(fields, ensure_ascii=False, indent=2)},
                expect, note, repeat=repeat)


def _successor(cid, criterion, clause, basis, note, previous, successor,
               accepted):
    return Case(cid, criterion, clause, basis, "check_successor",
                {"previous": _doc(previous), "successor": _doc(successor)},
                {"accepted": accepted}, note)


# -- C1 --------------------------------------------------------------------

def _c1(kit):
    vector = kit.spec.vectors["canonical-ordering"]
    beyond_bmp = u'{"a": 1, "\\ud83d\\ude00": 3, "\\uff21": 2}'
    escaped = u'{"z": "\\u00e9", "name": "caf\\u00e9 \\u5b87\\u5b99"}'
    spaced = u'{\n  "b": [ {"y": 2, "x": 1}, [3, 2, 1] ],\n  "a" : { },' \
             u' "c": [ ]\n}'
    integers = u'{"n": [0, -1, 10, 1234567890123]}'
    controls = u'{"s": "a\\nb\\tc\\"d\\\\e\\u001ff/g\\u007fh\\u2028i"}'
    duplicated = build.text(kit.record).replace(
        '"customer": "Example Aerospace GmbH"',
        '"customer": "Example Aerospace GmbH",\n  '
        '"customer": "Example Aerospace GmbH"', 1)
    if duplicated == build.text(kit.record):
        raise ValueError("the duplicate-key case found no customer to repeat")
    with_float = kit.variant(encode=build.loose, provenance={"ratio": 0.5})
    with_float = build.attest(with_float, kit.issuer, encode=build.loose)
    return [
        _canon("c1-vector-canonical-ordering", "C1",
               "§3; §13 canonical-ordering", "criterion",
               "The section 13 vector, byte for byte.",
               json.dumps(vector["value"], ensure_ascii=False),
               vector["canonical"].encode("utf-8").hex()),
        _canon("c1-escaped-input-emitted-literally", "C1", "§3", "must",
               "Non-ASCII arrives escaped and must leave as literal UTF-8.",
               escaped, _canon_hex(escaped)),
        _canon("c1-keys-sort-by-code-point", "C1", "§3", "must",
               "U+FF21 sorts before U+1F600 by code point, and after it by "
               "UTF-16 code unit; section 3 names the code point.",
               beyond_bmp, _canon_hex(beyond_bmp)),
        _canon("c1-whitespace-removed-order-kept", "C1", "§3", "must",
               "Insignificant whitespace goes; array order stays; nested "
               "keys sort.", spaced, _canon_hex(spaced)),
        _canon("c1-integers", "C1", "§3", "must",
               "Integers, negative and large, in their plain form.",
               integers, _canon_hex(integers)),
        _canon("c1-float-refused", "C1", "§3", "must",
               "No floating-point number appears in any artefact.",
               u'{"ratio": 0.5}'),
        _canon("c1-integral-float-refused", "C1", "§3", "must",
               "1.0 is a floating-point number whose text form two runtimes "
               "would spell differently.", u'{"count": 1.0}'),
        _canon("c1-nan-refused", "C1", "§3", "must",
               "NaN is not JSON, whatever a permissive encoder emits.",
               u'{"x": NaN}'),
        _canon("c1-duplicate-key-refused", "C1", "§3", "must",
               "A duplicate key has no defined serialisation.",
               u'{"a": 1, "a": 1}'),
        _verify("c1-record-with-float-refused", "C1", "§3; §11 step 1",
                "must", "A signed record whose identifier and signature "
                "were computed over a float; only the float is wrong.",
                with_float, kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c1-record-with-duplicate-key-refused", "C1", "§3", "must",
                "The same key twice with the same value: every parser "
                "agrees on the value, and section 3 still has no "
                "serialisation for the object.",
                duplicated, kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c1-control-record-with-integer-current", "C1", "§3; §11",
                "must", "The twin of the two cases above: provenance carries "
                "the integer 1, no key appears twice, and the identifier and "
                "signature are over CANON. It is current, so the refusals "
                "above are the float's and the duplicate's doing.",
                kit.signed(provenance={"ratio": 1}), kit.anchor, AT,
                kit.empty, ["current"]),
        _canon("c1-reading-string-escapes", "C1", "§3", "reading",
               "Section 3 does not say how control characters are escaped. "
               "The suite reads it as the Python line in section 3 emits "
               "them, which is also the RFC 8785 form: \\n and \\t as "
               "such, other controls as lowercase \\u00XX, and / and "
               "U+2028 unescaped.", controls, _canon_hex(controls)),
    ]


# -- C2 --------------------------------------------------------------------

def _c2(kit):
    offered = kit.spec.quoted("C2")
    names = ("c2-offset-refused", "c2-fractional-second-refused",
             "c2-lowercase-refused")
    if len(offered) != len(names):
        raise ValueError("C2 in this copy of ARCS-1 offers %d instants; the "
                         "catalogue expects %d" % (len(offered), len(names)))
    cases = []
    for cid, value in zip(names, offered):
        cases.append(_verify(
            cid, "C2", "§4; C2", "criterion",
            "issued_at is %s; everything else is sound and signed." % value,
            kit.signed(issued_at=value), kit.anchor, AT, kit.empty,
            kit.refusing))
    cases.extend([
        _verify("c2-impossible-date-refused", "C2", "§4", "must",
                "The form is right and the date does not exist.",
                kit.signed(not_after="2026-11-31T00:00:00Z"), kit.anchor, AT,
                kit.empty, kit.refusing),
        _verify("c2-status-list-instant-refused", "C2", "§4; §10", "must",
                "The status list's as_of carries a fractional second.",
                kit.record, kit.anchor, AT,
                kit.signed_list({}, as_of="2026-09-22T00:00:00.000Z"),
                kit.refusing),
        _build("c2-builder-refuses-offset", "C2", "§4", "must",
               "A builder offered an offset refuses it rather than "
               "normalising it.", kit.fields(issued_at=offered[0])),
        _verify("c2-control-exact-instants-current", "C2", "§4; §11",
                "must", "The twin of the cases above: every instant in the "
                "record and the list in the one form section 4 allows, the "
                "record's issued_at the instant C2 offers in three wrong "
                "spellings. It is current.", kit.record, kit.anchor, AT,
                kit.empty, ["current"]),
        _build("c2-control-builder-keeps-exact-instants", "C2", "§4; §6",
               "must", "The twin of the builder case: the same fields with "
               "every instant in the section 4 form are built, not refused.",
               kit.fields(), kit.minimal["record_id"]),
    ])
    return cases


# -- C3 --------------------------------------------------------------------

def _c3(kit):
    field = kit.spec.quoted("C3")[0]
    two_corpora = {"roles": "b" * 64, "skills": "a" * 64}
    wrong = [
        ("c3-required-field-missing", "runtime is absent.",
         {"runtime": _DROP}),
        ("c3-customer-empty", "customer is the empty string.",
         {"customer": ""}),
        ("c3-corpora-empty", "corpora names no corpus.", {"corpora": {}}),
        ("c3-corpus-digest-uppercase", "A corpus digest in uppercase hex.",
         {"corpora": {"skills": "A" * 64}}),
        ("c3-corpus-digest-short", "A corpus digest of 63 characters.",
         {"corpora": {"skills": "a" * 63}}),
        ("c3-spec-other", "spec names another specification.",
         {"spec": "ARCS-2"}),
        ("c3-claim-other", "claim names another dialect.",
         {"claim": "claim@2"}),
        ("c3-binding-not-ok", "binding_integrity is present with ok false.",
         {"corpora": two_corpora, "binding_integrity": {
             "bindings": 10, "ok": False, "resolved": 9, "roles": 2}}),
        ("c3-binding-count-not-integer", "A binding count is a string.",
         {"corpora": two_corpora, "binding_integrity": {
             "bindings": "10", "ok": True, "resolved": 10, "roles": 2}}),
        ("c3-provenance-not-object", "provenance is a string.",
         {"provenance": "assessed in house"}),
    ]
    cases = [_verify(
        "c3-undefined-field-refused", "C3", "§5; C3", "criterion",
        "A field named %s, the identifier re-derived and the record "
        "re-signed: refused as non-conforming although its identifier is "
        "sound, so unsound_id is not an answer." % field,
        kit.signed(**{field: "added after the fact"}), kit.anchor, AT,
        kit.empty, _without(kit.refusing, "unsound_id"))]
    for cid, note, changes in wrong:
        cases.append(_verify(cid, "C3", "§5", "must",
                             note + " Re-derived and re-signed.",
                             kit.signed(**changes), kit.anchor, AT, kit.empty,
                             kit.refusing))
    cases.append(_verify(
        "c3-control-every-optional-field-current", "C3", "§5; §11", "must",
        "The twin of the cases above: two corpora, binding_integrity with its "
        "four fields and ok true, provenance an object, and no field outside "
        "section 5's table, derived and signed. It is current.",
        kit.signed(corpora=two_corpora, provenance={"assessor": "example"},
                   binding_integrity={"bindings": 10, "ok": True,
                                      "resolved": 10, "roles": 2}),
        kit.anchor, AT, kit.empty, ["current"]))
    return cases


# -- C4 --------------------------------------------------------------------

def _c4(kit):
    vector_id = kit.spec.vectors["minimal-record"]["record_id"]
    list_id = kit.spec.vectors["status-list"]["list_id"]
    customer = kit.minimal["customer"]
    one_off = copy.deepcopy(kit.minimal)
    one_off["customer"] = customer[:-1] + chr(ord(customer[-1]) + 1)
    edited = copy.deepcopy(kit.record)
    edited["customer"] = one_off["customer"]

    specimen = kit.spec.specimen
    leaves = copy.deepcopy(specimen)
    leaves["provenance"]["skills_leaves"] += 1
    roles = copy.deepcopy(specimen)
    roles["binding_integrity"]["roles"] += 1

    copied = kit.variant(customer="Example Avionics SAS")
    copied["record_id"] = vector_id
    copied = build.attest(copied, kit.issuer)
    upper = copy.deepcopy(kit.minimal)
    upper["record_id"] = "AHD-" + vector_id[4:].upper()
    upper = build.attest(upper, kit.issuer)

    def spaced(value):
        return build.loose(value, separators=(", ", ": "))

    def escaped(value):
        return build.loose(value, ensure_ascii=True)

    umlaut = u"Müller Raumfahrt GmbH"
    return [
        _derive("c4-vector-minimal-record", "C4",
                "§6; §13 minimal-record; C4", "criterion",
                "The section 13 identifier, from the record alone.",
                kit.minimal, vector_id),
        _derive("c4-one-character-moves-the-identifier", "C4", "§6; C4",
                "criterion", "One character of customer changed; the "
                "record still carries the old identifier, and the derived "
                "one must differ from it.", one_off,
                build.derive_id(one_off)),
        _verify("c4-edited-customer-is-unsound", "C4", "§6; §11 step 2; C4",
                "criterion", "The same edit to a signed record: step 2 "
                "comes before step 3, so the answer is unsound_id.",
                edited, kit.anchor, AT, kit.empty, ["unsound_id"]),
        _derive("c4-vector-status-list", "C4", "§6; §13 status-list", "must",
                "A status list derives its identifier the same way, with "
                "AHS.", kit.vector_list, list_id),
        _derive("c4-specimen-identifier", "C4", "§6; §9", "must",
                "The published specimen derives SPECIMEN-.",
                kit.spec.specimen_text, build.derive_id(specimen)),
        _derive("c4-attestation-excluded", "C4", "§6", "must",
                "Signing does not move the identifier.", kit.record,
                vector_id),
        _derive("c4-provenance-covered", "C4", "§6", "must",
                "Provenance is inside the payload: one count changed moves "
                "the identifier.", leaves, build.derive_id(leaves)),
        _verify("c4-figure-changed-after-signing", "C4", "§6; §11 step 2",
                "must", "The published specimen with skills_leaves raised "
                "by one after signing.", build.text(leaves),
                kit.spec.specimen_anchor_text, kit.in_specimen_window,
                None, ["unsound_id"]),
        _verify("c4-binding-count-changed-after-signing", "C4",
                "§6; §11 step 2", "must", "The published specimen with its "
                "roles count raised by one after signing.",
                build.text(roles), kit.spec.specimen_anchor_text,
                kit.in_specimen_window, None, ["unsound_id"]),
        _verify("c4-serial-copied-from-another-record", "C4",
                "§6; §11 step 2", "must", "A different record carrying the "
                "minimal record's serial, signed as it stands.",
                copied, kit.anchor, AT, kit.empty, ["unsound_id"]),
        _verify("c4-serial-in-uppercase", "C4", "§3; §6", "must",
                "The serial's hex groups in uppercase: SHA is lowercase "
                "hexadecimal, so the serial does not recompute. A verifier "
                "may catch the form at step 1 or the value at step 2 "
                "(PROTOCOL.md, question 23), so any refusal passes; current "
                "does not.",
                upper, kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c4-serial-over-spaced-json", "C4", "§3; §6", "must",
                "The serial was derived over JSON with spaces after , and :.",
                build.attest(kit.variant(encode=spaced), kit.issuer),
                kit.anchor, AT, kit.empty, ["unsound_id"]),
        _verify("c4-serial-over-escaped-json", "C4", "§3; §6", "must",
                "The serial was derived over JSON with non-ASCII escaped to "
                "\\uXXXX.",
                build.attest(kit.variant(encode=escaped, customer=umlaut),
                             kit.issuer),
                kit.anchor, AT, kit.empty, ["unsound_id"]),
        _verify("c4-control-non-ascii-record-current", "C4", "§3; §6",
                "must", "The twin of the case above: the same record "
                "derived and signed over literal UTF-8 is sound, and "
                "current.",
                kit.signed(customer=umlaut), kit.anchor, AT, kit.empty,
                ["current"]),
    ]


# -- C5 --------------------------------------------------------------------

def _c5(kit):
    specimen = kit.spec.specimen
    unflagged = copy.deepcopy(specimen)
    del unflagged["specimen"]
    marked = kit.specimen_marked
    flag_dropped = copy.deepcopy(marked)
    del flag_dropped["specimen"]
    customer_unmarked = copy.deepcopy(marked)
    customer_unmarked["customer"] = kit.minimal["customer"]
    marked_fields = copy.deepcopy(marked)
    del marked_fields["record_id"]
    return [
        _verify("c5-specimen-verifies", "C5", "§9; §11 steps 1-5", "must",
                "The published specimen against its published anchor, with "
                "no status list: not refused at steps 1 to 4. Whether it "
                "can then be current without a list is a reading (C10).",
                kit.spec.specimen_text, kit.spec.specimen_anchor_text,
                kit.in_specimen_window, None, ["current", "unknown"]),
        _verify("c5-specimen-flag-deleted", "C5", "§9; C5", "criterion",
                "The published specimen without its specimen field. The "
                "flag is inside the payload, so a verifier with no specimen "
                "check at all refuses this at step 2 as unsound_id and "
                "passes: C5's own test cannot tell the two apart "
                "(PROTOCOL.md, question 22). The reissued case below is the "
                "one with teeth.",
                json.dumps(unflagged, ensure_ascii=False, indent=2),
                kit.spec.specimen_anchor_text, kit.in_specimen_window, None,
                kit.refusing),
        _verify("c5-flag-dropped-and-reissued", "C5", "§9", "must",
                "A specimen with its flag dropped, re-derived as AHD- and "
                "re-signed: the customer still says SPECIMEN, and the three "
                "marks disagree.", build.attest(build.with_id(flag_dropped),
                                                kit.issuer),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c5-customer-unmarked", "C5", "§9", "must",
                "Flag and prefix say specimen; the customer does not.",
                build.attest(build.with_id(customer_unmarked), kit.issuer),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c5-control-unmarked-record-current", "C5", "§9; §11",
                "must", "The twin of the reissued cases above: an issued "
                "record with none of the three marks, the flag absent and "
                "the customer and serial plain. It is current.", kit.record,
                kit.anchor, AT, kit.empty, ["current"]),
        _verify("c5-specimen-false", "C5", "§5; §9", "must",
                "specimen is present and false; section 5 allows it present "
                "only as true.", kit.signed(specimen=False), kit.anchor, AT,
                kit.empty, kit.refusing),
        Case("c5-specimen-never-matches", "C5", "§9", "must", "matches",
             {"document": kit.spec.specimen_text,
              "corpora": copy.deepcopy(specimen["corpora"])},
             {"matches": False},
             "A specimen matches no corpus set, not even the one it names."),
        _build("c5-builder-marks-specimen", "C5", "§6; §9", "must",
               "A builder given a specimen derives the SPECIMEN prefix.",
               marked_fields, marked["record_id"]),
        _verify("c5-reading-marked-specimen-verifies", "C5", "§9; §11",
                "reading", "A specimen marked in all three places, signed, "
                "with a fresh list. The suite reads section 9 as refusing a "
                "specimen at matching and not at verification, so the "
                "answer is current.", build.attest(marked, kit.issuer),
                kit.anchor, AT, kit.empty, ["current"]),
        Case("c5-reading-record-matches-its-corpora", "C5", "§5; §9",
             "reading", "matches",
             {"document": build.text(kit.record),
              "corpora": copy.deepcopy(kit.minimal["corpora"])},
             {"matches": True},
             "ARCS-1 names a corpus-matching function and does not define "
             "it. The suite reads it as: an issued record matches the corpus "
             "set it names, digest for digest."),
    ]


# -- C6 --------------------------------------------------------------------

def _c6(kit):
    start = kit.minimal["not_before"]
    return [
        _verify("c6-empty-window-refused", "C6", "§5; C6", "criterion",
                "not_after equals not_before.",
                kit.signed(not_after=start), kit.anchor, AT, kit.empty,
                kit.refusing),
        _verify("c6-window-opens-before-issue", "C6", "§5", "must",
                "not_before is earlier than issued_at.",
                kit.signed(not_before="2026-09-20T00:00:00Z"), kit.anchor, AT,
                kit.empty, kit.refusing),
        _verify("c6-window-inverted", "C6", "§5", "must",
                "not_after is earlier than not_before.",
                kit.signed(not_after="2026-09-20T00:00:00Z"), kit.anchor, AT,
                kit.empty, kit.refusing),
        _build("c6-builder-refuses-empty-window", "C6", "§5", "must",
               "A builder refuses a window that covers no time.",
               kit.fields(not_after=start)),
        _build("c6-control-builder-keeps-a-one-second-window", "C6", "§5",
               "must", "The twin of the builder case: not_after one second "
               "after not_before covers time, and is built.",
               kit.fields(not_after=_later(start, 1)),
               kit.variant(not_after=_later(start, 1))["record_id"]),
        _verify("c6-not-yet-valid", "C6", "§11 steps 5 and 6.6", "must",
                "Asked about an instant before not_before.",
                kit.record, kit.anchor, "2026-09-20T12:00:00Z", kit.empty,
                ["not_yet_valid"]),
        _verify("c6-expired", "C6", "§11 steps 5 and 6.6", "must",
                "Asked about an instant after not_after, with a list still "
                "fresh then.", kit.record, kit.anchor, AFTER_WINDOW,
                kit.empty_long, ["expired"]),
    ]


# -- C7 --------------------------------------------------------------------

def _c7(kit):
    other_kind = kit.signed_list({}, context=build.LIST_CONTEXT[:-1] + "0")
    return [
        _verify("c7-status-list-offered-as-record", "C7",
                "§7; §11 step 4; C7", "criterion",
                "A valid signed status list where a record is expected.",
                kit.empty, kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c7-earlier-record-shape", "C7", "§7", "must",
                "A record whose context is an earlier shape, re-derived and "
                "re-signed, with a list that covers that shape.",
                kit.signed(context=OLDER_RECORD_CONTEXT), kit.anchor, AT,
                kit.signed_list({}, covers_context=OLDER_RECORD_CONTEXT),
                kit.refusing),
        _verify("c7-attestation-for-another-purpose", "C7", "§7; §8", "must",
                "Signed, correctly, under another purpose's context, and "
                "labelled with it.",
                build.attest(kit.minimal, kit.issuer,
                             payload_context=OTHER_PURPOSE,
                             attestation_context=OTHER_PURPOSE),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c7-signature-made-for-another-purpose", "C7", "§7; §8",
                "must", "Labelled with the attestation context but signed "
                "over another purpose's.",
                build.attest(kit.minimal, kit.issuer,
                             payload_context=OTHER_PURPOSE),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c7-record-offered-as-status-list", "C7", "§7", "must",
                "A signed record where the status list is expected.",
                kit.record, kit.anchor, AT, kit.second_record, kit.refusing),
        _verify("c7-status-list-of-another-kind", "C7", "§7; §10", "must",
                "A status list whose context is not the section 7 string.",
                kit.record, kit.anchor, AT, other_kind, kit.refusing),
        _verify("c7-control-each-document-in-its-place-current", "C7",
                "§7; §11", "must", "The twin of the cases above: a record "
                "where the record belongs, signed under the attestation "
                "context, and a list of the section 7 kind covering its "
                "context where the list belongs. It is current.",
                kit.record, kit.anchor, AT, kit.empty, ["current"]),
    ]


# -- C8 --------------------------------------------------------------------

def _c8(kit):
    def edit_attestation(**changes):
        record = copy.deepcopy(kit.record)
        record["attestation"].update(changes)
        return record

    signature = bytes.fromhex(kit.record["attestation"]["signature"])
    flipped = bytearray(signature)
    flipped[0] ^= 1
    order = 2 ** 252 + 27742317777372353535851937790883648493
    s = int.from_bytes(signature[32:], "little") + order
    malleated = signature[:32] + s.to_bytes(32, "little")

    edited = copy.deepcopy(kit.record)
    edited["customer"] = "Example Aerospace AG"
    edited = build.with_id(edited)
    edited["attestation"] = copy.deepcopy(kit.record["attestation"])
    digest_rewritten = copy.deepcopy(edited)
    digest_rewritten["attestation"]["body_digest"] = "sha256:" + build.sha(
        build.canon(build.unsigned(edited)))

    umlaut = kit.variant(customer=u"Müller Raumfahrt GmbH")
    escaped_digest = build.attest(
        umlaut, kit.issuer,
        encode=lambda v: build.loose(v, ensure_ascii=True))

    list_edited = build.unsigned(kit.empty)
    list_edited["next_update"] = "2027-06-01T00:00:00Z"
    list_edited = build.with_id(list_edited)
    list_edited["attestation"] = copy.deepcopy(kit.empty["attestation"])

    return [
        _verify("c8-forged-key-refused", "C8", "§2; §11 step 3; C8",
                "criterion", "Re-signed by a fresh key whose public half is "
                "written into the record, with a list from the same key; "
                "the anchor lists neither.",
                build.attest(kit.minimal, kit.forger), kit.anchor, AT,
                kit.signed_list({}, key=kit.forger), kit.refusing),
        _verify("c8-embedded-key-disagrees", "C8", "§11 step 3", "must",
                "Signed by an anchored key, naming another anchored key as "
                "its public_key.",
                edit_attestation(public_key=kit.second.public.hex()),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-key-id-relabelled", "C8", "§8; §11 step 3", "must",
                "Signed by one anchored key, labelled as the other.",
                edit_attestation(key_id=kit.second.key_id,
                                 public_key=kit.second.public.hex()),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-signature-truncated", "C8", "§8", "must",
                "The signature is one byte short.",
                edit_attestation(signature=signature[:-1].hex()),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-signature-bit-flipped", "C8", "§8", "must",
                "One bit of the signature flipped.",
                edit_attestation(signature=bytes(flipped).hex()),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-signature-malleated", "C8", "§8; RFC 8032 section 5.1.7",
                "must", "The same signature with the group order added to "
                "s: Ed25519 requires s below the order.",
                edit_attestation(signature=malleated.hex()),
                kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-body-edited-identifier-rederived", "C8", "§11 step 3",
                "must", "A figure changed after signing and the serial "
                "re-derived to match: only the body digest catches it.",
                edited, kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-body-digest-rewritten", "C8", "§8; §11 step 3", "must",
                "As above with body_digest rewritten to the new body: only "
                "the signature catches it.",
                digest_rewritten, kit.anchor, AT, kit.empty, kit.refusing),
        _verify("c8-body-digest-over-escaped-json", "C8", "§3; §8", "must",
                "Signed over a body digest taken of JSON with non-ASCII "
                "escaped to \\uXXXX.", escaped_digest, kit.anchor, AT,
                kit.empty, kit.refusing),
        _verify("c8-attestation-field-undefined", "C8", "§8", "must",
                "The attestation carries a field section 8 does not define.",
                edit_attestation(comment="countersigned"), kit.anchor, AT,
                kit.empty, kit.refusing),
        _verify("c8-algorithm-other", "C8", "§8", "must",
                "The attestation names another algorithm.",
                edit_attestation(algorithm="ed448"), kit.anchor, AT,
                kit.empty, kit.refusing),
        _verify("c8-status-list-edited-after-signing", "C8",
                "§10; §11 step 6", "must",
                "A list's next_update pushed out after signing and its "
                "identifier re-derived; read when only the edited list "
                "would still be fresh.", kit.record, kit.anchor,
                "2026-11-15T00:00:00Z", list_edited, kit.refusing),
        _verify("c8-status-list-from-untrusted-key", "C8", "§11 step 6.3",
                "must", "A list signed by a key the anchor does not list.",
                kit.record, kit.anchor, AT,
                kit.signed_list({}, key=kit.forger), kit.refusing),
        _verify("c8-specimen-against-another-anchor", "C8", "§9; §11 step 3",
                "must", "The published specimen against an anchor that "
                "does not list the specimen key. No list can be signed with "
                "the specimen key (PROTOCOL.md, question 24), so a verifier "
                "that ignores the anchor reaches unknown here and passes "
                "too: this case has teeth only against one that reads a "
                "record with no list as current. c8-forged-key-refused is "
                "the case that separates the two.", kit.spec.specimen_text,
                kit.anchor, kit.in_specimen_window, None, kit.refusing),
        _verify("c8-control-anchored-key-current", "C8", "§11 step 3",
                "must", "The twin of the cases above: signed by a key the "
                "anchor lists, naming that key, with a list from the same "
                "key. It is current.", kit.record, kit.anchor, AT, kit.empty,
                ["current"]),
        _verify("c8-control-second-anchored-key-current", "C8",
                "§11 step 3", "must", "The same record signed by the "
                "anchor's other key, with a list from that key. It is "
                "current: either anchored key will do, so the two relabelled "
                "cases above are refused for their labels, not their key.",
                build.attest(kit.minimal, kit.second), kit.anchor, AT,
                kit.signed_list({}, key=kit.second), ["current"]),
    ]


# -- C9 --------------------------------------------------------------------

def _c9(kit):
    empty_anchor = build.anchor_text([])
    return [
        _verify("c9-empty-anchor", "C9", "§11 step 0; C9", "criterion",
                "A genuine record and a fresh list, against an anchor with "
                "no keys.", kit.record, empty_anchor, AT, kit.empty,
                kit.refusing),
        _verify("c9-empty-anchor-specimen", "C9", "§11 step 0; C9",
                "criterion", "The published specimen against an anchor "
                "with no keys. As with c8-specimen-against-another-anchor, "
                "no list can be made for the specimen key, so a verifier "
                "that ignores the anchor passes here unless it reads a "
                "record with no list as current; c9-empty-anchor is the case "
                "that separates the two.", kit.spec.specimen_text,
                empty_anchor, kit.in_specimen_window, None, kit.refusing),
        _verify("c9-anchor-without-schema", "C9", "§7", "must",
                "A keys array with no schema field: not a trust anchor.",
                kit.record, build.anchor_text([kit.issuer, kit.second],
                                              schema=None),
                AT, kit.empty, kit.refusing),
        _verify("c9-anchor-of-another-kind", "C9", "§7", "must",
                "A keys array under another document's schema.",
                kit.record, build.anchor_text([kit.issuer, kit.second],
                                              schema="example-key-list/v1"),
                AT, kit.empty, kit.refusing),
        _verify("c9-control-anchored-record-current", "C9", "§7; §11 step 0",
                "must", "The twin of the cases above: the same genuine "
                "record and list against an anchor that names its schema "
                "and lists the signing key. It is current, so the refusals "
                "above are the anchor's doing.", kit.record, kit.anchor, AT,
                kit.empty, ["current"]),
    ]


# -- C10 -------------------------------------------------------------------

def _c10(kit):
    finding_at = kit.finding["at"]
    superseding = kit.signed_list({kit.minimal["record_id"]: {
        "at": finding_at, "reason": "re-assessed over a corrected corpus",
        "state": "superseded",
        "superseded_by": kit.third_record["record_id"]}})
    elsewhere = kit.signed_list({kit.second_record["record_id"]: kit.finding})
    return [
        _verify("c10-good-standing", "C10", "§10; §11 step 6; C10",
                "criterion", "A signed record and a fresh signed list that "
                "says nothing about it.", kit.record, kit.anchor, AT,
                kit.empty, ["current"]),
        _verify("c10-withdrawn", "C10", "§10; §13 status-list; C10",
                "criterion", "The same record, and the section 13 list "
                "withdrawing it, signed.", kit.record, kit.anchor, AT,
                kit.withdrawing, ["withdrawn"]),
        _verify("c10-superseded", "C10", "§10", "must",
                "A finding that names its successor.", kit.record,
                kit.anchor, AT, superseding, ["superseded"]),
        _verify("c10-finding-not-yet-in-effect", "C10", "§11 step 6.4",
                "must", "Asked about an instant before the finding's at.",
                kit.record, kit.anchor, "2026-09-24T00:00:00Z",
                kit.withdrawing, ["current"]),
        _verify("c10-finding-at-the-instant", "C10", "§11 step 6.4", "must",
                "Asked about the finding's own at: at or before.",
                kit.record, kit.anchor, finding_at, kit.withdrawing,
                ["withdrawn"]),
        _verify("c10-withdrawal-not-an-expiry", "C10", "§11 step 6.6",
                "must", "Asked after the window closed: a withdrawal is "
                "never reported as an expiry.", kit.record, kit.anchor,
                AFTER_WINDOW, kit.withdrawing_long, ["withdrawn"]),
        _verify("c10-finding-against-another-record", "C10", "§10", "must",
                "The list withdraws a different serial.", kit.record,
                kit.anchor, AT, elsewhere, ["current"]),
        _verify("c10-reading-no-status-list", "C10", "§10; §11", "reading",
                "A genuine record with no status list. Section 10 grants "
                "assurance only through a list that is in scope, "
                "authenticated and fresh; the suite reads that as: not "
                "current (its own reading is unknown).", kit.record,
                kit.anchor, AT, None, kit.refusing),
    ]


# -- C11 -------------------------------------------------------------------

def _c11(kit):
    other = kit.second_record["record_id"]
    unsound = build.unsigned(kit.empty)
    unsound["list_id"] = "AHS-00000000" + unsound["list_id"][12:]
    return [
        _verify("c11-withdrawal-outlives-next-update", "C11",
                "§10; §11 step 6.4; C11", "criterion",
                "The withdrawing list read after its own next_update.",
                kit.record, kit.anchor, AFTER_NEXT_UPDATE, kit.withdrawing,
                ["withdrawn"]),
        _verify("c11-unsigned-withdrawal-honoured", "C11",
                "§10; §11 step 6.4; C11", "criterion",
                "Every attestation removed.", build.unsigned(kit.record),
                kit.anchor, AT, build.unsigned(kit.withdrawing),
                ["withdrawn"]),
        _verify("c11-stale", "C11", "§11 step 6.5", "must",
                "A list with no finding, read after its next_update.",
                kit.record, kit.anchor, AFTER_NEXT_UPDATE, kit.empty,
                ["stale"]),
        _verify("c11-stale-before-expiry", "C11", "§11 steps 6.5 and 6.6",
                "must", "Stale and expired at once: the window is last.",
                kit.record, kit.anchor, AFTER_WINDOW, kit.empty, ["stale"]),
        _verify("c11-unsigned-status-list", "C11", "§11 steps 6.3 and 6.5",
                "must", "A signed record, an unsigned list with no finding. "
                "Step 6.3 (unknown) and step 6.5 (unauthenticated) both "
                "describe it.", kit.record, kit.anchor, AT,
                build.unsigned(kit.empty), ["unauthenticated", "unknown"]),
        _verify("c11-unsigned-record", "C11", "§11 steps 6.3 and 6.5",
                "must", "An unsigned record, a signed list with no finding.",
                build.unsigned(kit.record), kit.anchor, AT, kit.empty,
                ["unauthenticated", "unknown"]),
        _verify("c11-unsigned-both", "C11", "§11 step 6.5", "must",
                "Neither is signed and the list has no finding.",
                build.unsigned(kit.record), kit.anchor, AT,
                build.unsigned(kit.empty), ["unauthenticated"]),
        _verify("c11-supersession-without-successor", "C11", "§10", "must",
                "A superseded finding that names no successor makes the "
                "list malformed, and no verdict is read from it.",
                kit.record, kit.anchor, AT, kit.signed_list({other: {
                    "at": kit.finding["at"], "reason": "re-done",
                    "state": "superseded"}}), kit.refusing),
        _verify("c11-reason-over-200", "C11", "§10", "must",
                "A finding whose reason runs to 201 characters.",
                kit.record, kit.anchor, AT, kit.signed_list({other: {
                    "at": kit.finding["at"], "reason": "x" * 201,
                    "state": "withdrawn"}}), kit.refusing),
        _verify("c11-finding-state-undefined", "C11", "§10", "must",
                "A finding in a state section 10 does not define.",
                kit.record, kit.anchor, AT, kit.signed_list({other: {
                    "at": kit.finding["at"], "reason": "under review",
                    "state": "suspended"}}), kit.refusing),
        _verify("c11-status-list-identifier-unsound", "C11", "§6; §10",
                "must", "A list whose list_id does not recompute, signed "
                "as it stands.", kit.record, kit.anchor, AT,
                build.attest(unsound, kit.issuer), kit.refusing),
        _verify("c11-status-list-window-empty", "C11", "§10", "must",
                "next_update equals as_of: a list that promises no "
                "successor.", kit.record, kit.anchor, AT,
                kit.signed_list({}, next_update=kit.vector_list["as_of"]),
                kit.refusing),
        _verify("c11-reading-unsigned-list-against-signed-record", "C11",
                "§10; §11 step 6.3", "reading",
                "A signed record and an unsigned list withdrawing it. Step "
                "6.3 cannot compare a key with no key; the suite reads the "
                "unsigned list as nobody's, so it cannot withdraw a signed "
                "record and the answer is unknown.", kit.record, kit.anchor,
                AT, build.unsigned(kit.withdrawing), ["unknown"]),
    ]


# -- C12 -------------------------------------------------------------------

def _c12(kit):
    cases = [Case("c12-relied-on-%s" % conclusion.replace("_", "-"), "C12",
                  "§11; C12", "criterion", "reliance",
                  {"conclusion": conclusion},
                  {"relied": conclusion == "current"},
                  "The reliance boolean for %s." % conclusion)
             for conclusion in kit.conclusions]
    # The boolean on every verify_record answer is judged under C12 as well
    # (runner.reliance). These two make sure that judgement sees it both
    # ways: a verifier that never answers current, or always does, cannot
    # show that its boolean follows its conclusion.
    cases.extend([
        _verify("c12-control-current-is-relied-on", "C12", "§11; C12",
                "must", "A sound record with a fresh list, through "
                "verify_record: current, and the boolean true.", kit.record,
                kit.anchor, AT, kit.empty, ["current"]),
        _verify("c12-control-withdrawn-is-not-relied-on", "C12",
                "§10; §11; C12", "must", "The same record under the list "
                "withdrawing it: withdrawn, and the boolean false.",
                kit.record, kit.anchor, AT, kit.withdrawing, ["withdrawn"]),
    ])
    return cases


# -- C13 -------------------------------------------------------------------

def _c13(kit):
    late = kit.signed(issued_at="2026-09-23T00:00:00Z",
                      not_before="2026-09-23T00:00:00Z")
    return [
        _verify("c13-status-list-of-another-scope", "C13",
                "§10; §11 step 6.2; C13", "criterion",
                "The list covers another record context.", kit.record,
                kit.anchor, AT,
                kit.signed_list({}, covers_context=OLDER_RECORD_CONTEXT),
                ["unknown"]),
        _verify("c13-record-issued-after-cut", "C13",
                "§10; §11 step 6.5; C13", "criterion",
                "The record was issued after the list's as_of.", late,
                kit.anchor, AT, kit.empty, ["unknown"]),
        _verify("c13-out-of-scope-finding", "C13", "§11 steps 6.2 and 6.4",
                "must", "A list of another scope withdrawing the record: "
                "scope is checked before any finding is read.", kit.record,
                kit.anchor, AT,
                kit.signed_list(kit.vector_list["entries"],
                                covers_context=OLDER_RECORD_CONTEXT),
                ["unknown"]),
        _verify("c13-another-issuers-list", "C13", "§11 step 6.3", "must",
                "The same serial signed by another anchored key, and a list "
                "from the first key withdrawing it: one issuer's list does "
                "not govern another's record.",
                build.attest(kit.minimal, kit.second), kit.anchor, AT,
                kit.withdrawing, ["unknown"]),
        _verify("c13-control-list-in-scope-current", "C13",
                "§10; §11 step 6", "must", "The twin of the scope and cut "
                "cases: a list covering the record's own context, cut after "
                "the record was issued, from the record's own key. It is "
                "current.", kit.record, kit.anchor, AT, kit.empty,
                ["current"]),
        _verify("c13-control-own-issuers-list-withdraws", "C13",
                "§11 steps 6.3 and 6.4", "must", "The twin of the "
                "other-issuer case: the record signed by the anchor's second "
                "key, and that key's own list withdrawing it. The finding is "
                "honoured, so the unknown above is the key's doing.",
                build.attest(kit.minimal, kit.second), kit.anchor, AT,
                kit.signed_list(kit.vector_list["entries"], key=kit.second),
                ["withdrawn"]),
    ]


# -- C14 -------------------------------------------------------------------

def _c14(kit):
    first = kit.minimal["record_id"]
    second = kit.second_record["record_id"]
    third = kit.third_record["record_id"]
    superseded = {"at": "2026-09-26T00:00:00Z",
                  "reason": "re-assessed over a corrected corpus",
                  "state": "superseded", "superseded_by": third}
    previous = kit.signed_list({first: kit.finding, second: superseded})
    chained = build.sha(build.canon(previous))

    def successor(entries, **changes):
        fields = {"sequence": 2, "as_of": "2026-10-20T00:00:00Z",
                  "next_update": "2026-11-20T00:00:00Z",
                  "previous_digest": chained}
        fields.update(changes)
        return kit.signed_list(entries, **fields)

    kept = {first: kit.finding, second: superseded}
    grown = dict(kept)
    grown[third] = {"at": "2026-10-15T00:00:00Z", "reason": "key compromise",
                    "state": "withdrawn"}
    softened = dict(kept)
    softened[first] = {"at": kit.finding["at"], "reason": "re-done",
                       "state": "superseded", "superseded_by": third}
    omitted = {second: superseded}
    escalated = {first: kit.finding,
                 second: {"at": superseded["at"], "reason": "withdrawn after "
                          "all", "state": "withdrawn"}}
    postponed = dict(kept)
    postponed[first] = dict(kit.finding, at="2026-10-05T00:00:00Z")
    return [
        _successor("c14-successor-accepted", "C14", "§10", "must",
                   "Sequence 2, chained to its predecessor, every finding "
                   "kept, one added.", previous, successor(grown), True),
        _successor("c14-softened-refused", "C14", "§10; C14", "criterion",
                   "A withdrawal re-stated as a supersession.", previous,
                   successor(softened), False),
        _successor("c14-omitted-refused", "C14", "§10; C14", "criterion",
                   "A withdrawal the predecessor carried, dropped.",
                   previous, successor(omitted), False),
        _successor("c14-escalation-accepted", "C14", "§10; C14", "must",
                   "A supersession escalated to a withdrawal.", previous,
                   successor(escalated), True),
        _successor("c14-chain-digest-without-attestation", "C14", "§10",
                   "must", "previous_digest taken over the predecessor "
                   "without its attestation.", previous,
                   successor(kept, previous_digest=build.sha(
                       build.canon(build.unsigned(previous)))), False),
        _successor("c14-sequence-skipped", "C14", "§10", "must",
                   "Sequence 3 after sequence 1.", previous,
                   successor(kept, sequence=3), False),
        _successor("c14-reading-finding-postponed", "C14", "§10; C14",
                   "reading", "The same withdrawal with its at moved "
                   "later. The suite reads a later effective instant as a "
                   "weakening, because a relying party asking about the gap "
                   "would be told current.", previous, successor(postponed),
                   False),
    ]


# -- C15 -------------------------------------------------------------------

def _c15(kit):
    past = kit.signed(issued_at="2001-01-01T00:00:00Z",
                      not_before="2001-01-01T00:00:00Z",
                      not_after="2001-12-31T00:00:00Z")
    past_list = kit.signed_list({}, as_of="2001-06-01T00:00:00Z",
                                next_update="2001-07-01T00:00:00Z")
    future = kit.signed(issued_at="2098-01-01T00:00:00Z",
                        not_before="2098-01-01T00:00:00Z",
                        not_after="2098-12-31T00:00:00Z")
    future_list = kit.signed_list({}, as_of="2098-06-01T00:00:00Z",
                                  next_update="2098-07-01T00:00:00Z")
    return [
        _build("c15-build-twice", "C15", "§3; §6; C15", "criterion",
               "The minimal record's fields built twice: the same bytes "
               "both times, carrying the section 13 identifier.",
               kit.fields(), kit.spec.vectors["minimal-record"]["record_id"],
               repeat=2),
        _verify("c15-resolved-in-the-past", "C15", "§11; C15", "criterion",
                "A record and list of 2001, asked about 2001: current then, "
                "whatever the clock says now.", past, kit.anchor,
                "2001-06-15T00:00:00Z", past_list, ["current"]),
        _verify("c15-resolved-in-the-future", "C15", "§11; C15", "must",
                "A record and list of 2098, asked about 2098.", future,
                kit.anchor, "2098-06-15T00:00:00Z", future_list,
                ["current"]),
        _verify("c15-control-past-record-read-after-its-list", "C15",
                "§11 step 6.5; C15", "must", "The record and list of 2001, "
                "asked about August 2001, after the list's next_update: "
                "stale then. The twin of the case above it, so a verifier "
                "that answers current whatever it is asked cannot pass "
                "both.", past, kit.anchor, "2001-08-01T00:00:00Z", past_list,
                ["stale"]),
    ]
