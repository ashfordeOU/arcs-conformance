# The adapter protocol, `arcs-conformance-adapter/1`

The suite tests implementations it cannot see, written in languages it does
not speak. So it assumes the one interface every language has: a command
that reads a request on standard input and writes one answer on standard
output. Wrapping an implementation in such a command is the adapter, and
this document is everything an adapter needs. Nothing else is required, and
nothing needs to be asked of anyone. This is version 1 of the protocol, and
every request names it as `arcs-conformance-adapter/1`.

The specification the answers are graded against is the Agent Run
Conformance Specification (ARCS-1), in the copy in `spec/`. Section numbers
written with § below are its sections (§11 is section 11). Requests and
answers are written in JSON (JavaScript Object Notation). Every other term
of art, and every abbreviation, is defined in plain words in
[docs/GLOSSARY.md](docs/GLOSSARY.md).

C1 to C15 are the conformance criteria of ARCS-1 section 12. An
implementation conforms when all fifteen hold, and this document cites them
by number throughout, so here they are in the specification's own words,
with the operations whose cases test each. The table is written from the
copy of ARCS-1 in `spec/` by `tools/gen_readme.py`.

<!-- gen:criteria -->
| | title in ARCS-1 §12 | the operations its cases use |
| --- | --- | --- |
| **C1** | Canonical serialisation | `canonicalise`, `verify_record` |
| **C2** | Instants are refused, not normalised | `verify_record`, `build_record` |
| **C3** | The record carries exactly the defined fields | `verify_record` |
| **C4** | The identifier is derived and recomputable | `derive_id`, `verify_record` |
| **C5** | A specimen is marked in three places | `verify_record`, `matches`, `build_record` |
| **C6** | The window is stated and non-empty | `verify_record`, `build_record` |
| **C7** | The body names its own type, and the verifier checks it | `verify_record` |
| **C8** | Verification uses the verifier's anchor, never the record's key | `verify_record` |
| **C9** | An empty anchor cannot produce a pass | `verify_record` |
| **C10** | Standing is resolved from the list, never from the record | `verify_record` |
| **C11** | Doubt removes assurance and never launders a finding | `verify_record` |
| **C12** | One conclusion permits reliance | `verify_record`, `reliance` |
| **C13** | A list states its own scope, cut and successor | `verify_record` |
| **C14** | A finding is never softened or dropped | `check_successor` |
| **C15** | No clock | `verify_record`, `build_record` |
<!-- /gen:criteria -->

---

## 1. How the suite calls an adapter

| aspect | rule |
| --- | --- |
| command | `--impl '<command>'`. On POSIX systems (those that follow the Portable Operating System Interface standards: Linux, macOS and similar) it is split into arguments as a POSIX shell would split it and executed directly, never through a shell, so pipes and redirections do nothing; put them in a script and name the script. On Windows the text is handed to the system as the command line, as written, because a POSIX split would eat the backslashes of a Windows path |
| working directory | the directory the suite was started from |
| environment | inherited unchanged |
| processes | one process per call. Every case makes one call, except `c15-build-twice`, which makes the same call twice |
| standard input | exactly one request: a JSON object in ASCII (the American Standard Code for Information Interchange), every character outside ASCII escaped, then end of file |
| standard output | exactly one JSON object, in UTF-8 (Unicode Transformation Format, 8-bit). Whitespace around it is ignored; anything else makes the call an ERROR |
| standard error | free. Its last lines are printed against an ERROR and never graded |
| exit status 0 | the object on standard output is the answer. A refusal is an answer and exits 0 |
| exit status 3 | the adapter does not implement this operation. The case is an ERROR, never a PASS |
| any other exit status | the adapter failed. The case is an ERROR |
| time | 30 seconds per call unless `--timeout` says otherwise. On expiry the case is an ERROR and, on POSIX, the call's whole process group is killed, so an adapter that wraps the real verifier takes it down with it. A process that has left the group and still holds the pipes is abandoned after 5 seconds, never waited for |
| concurrency | one call at a time unless `--jobs` says otherwise |

An ERROR is never counted as a pass or as a fail. A criterion with an
ERROR against it and no FAIL is reported as *not shown*, for the reason
§10 gives about status lists: *I could not check* is not *it is fine*.

---

## 2. Requests

Every request carries three fields besides the operation's own:

| field | value |
| --- | --- |
| `protocol` | `arcs-conformance-adapter/1` |
| `op` | the operation, below |
| `case` | the case identifier, for the adapter's logs only. An adapter whose answer depends on it is not being tested |

**Artefacts travel as JSON text inside a string.** A record, a status list,
a trust anchor, build fields and the value to canonicalise are each passed
as the text of a JSON document, not as a parsed object. A verifier is handed
a file, not a data structure, and some cases are about text no parser
would carry through unchanged: a key given twice, a `NaN` (not a number), a
decimal written `1.0`. Arguments that are not artefacts (`at`, `corpora`, `conclusion`) are
plain JSON values.

**The text is never canonical.** Every document the suite builds is handed
over indented, with its top-level keys in reverse order. An implementation
that hashes the bytes it was given, rather than `CANON` of what they say
(ARCS-1's name for the canonical serialisation of §3),
never reaches `current` on a document the suite built, and so fails every
case that asks for `current` (the `hashes-the-text` defect in the suite's
own tests shows it). The published specimen is handed over exactly as
published.

### The operations

| op | request fields | answer fields | section | criteria its cases serve |
| --- | --- | --- | --- | --- |
| `canonicalise` | `value` | `canonical_hex`, or `refused` | §3 | C1 |
| `derive_id` | `document` | `id` | §6 | C4 |
| `verify_record` | `document`, `anchor`, `at`, `status_list` | `conclusion`, `relied` | §11 | C1-C13, C15 |
| `reliance` | `conclusion` | `relied` | §11 | C12 |
| `matches` | `document`, `corpora` | `matches` | §9 | C5 |
| `check_successor` | `previous`, `successor` | `accepted` | §10 | C14 |
| `build_record` | `fields` | `document`, or `refused` | §5, §6 | C2, C5, C6, C15 |

One further operation is optional and never graded: `describe`, answered
with `{"name": "...", "version": "..."}`, which the report prints beside
the words *not checked*. Any answer may also carry `problems`, a list of
strings the report shows against a FAIL and never grades.

### `canonicalise` (§3)

```json
{"protocol": "arcs-conformance-adapter/1", "case": "c1-vector-canonical-ordering",
 "op": "canonicalise", "value": "{\"z\": 1, \"n\": 10, ...}"}
```

Parse `value` and answer `{"canonical_hex": "<the CANON bytes, in hexadecimal>"}`,
or `{"refused": true}` where §3 says the value has no serialisation: a
floating-point number, `NaN` or an infinity, a key given twice. The answer
is the bytes written in hexadecimal, not a string, because the question is
about bytes.

### `derive_id` (§6)

Answer `{"id": "..."}`: the identifier the document's own payload derives,
whatever identifier it carries. The prefix, which ARCS-1 §6 gives as a
prefix and does not spell out, follows the document: `AHS` for a status
list (its `context` is the §7 list string), `SPECIMEN` for a record with
`specimen: true`, `AHD` for any other record. No anchor, no network.

### `verify_record` (§11)

| field | value |
| --- | --- |
| `document` | the record, as text |
| `anchor` | the trust anchor, as text (section 4 below) |
| `at` | the instant asked about, written `YYYY-MM-DDTHH:MM:SSZ` as §4 requires |
| `status_list` | the status list, as text. Absent when the case gives none |

Answer `{"conclusion": "...", "relied": true|false}`. The conclusion is one
of the nine §11 names, or `refused`:

    unsound_id  unknown  withdrawn  superseded  unauthenticated
    stale  not_yet_valid  expired  current  refused

`refused` is this protocol's one addition. It is the answer for a document
the verifier refused before any of the nine could be reached: a record of
the wrong shape (§11 step 1), a document of the wrong type (step 4), an
anchor the verifier would not load (step 0). §11 names no conclusion for
these (question 1 below), and none for a failure of authenticity either
(step 3 says *stop*), so wherever a case turns on one of them it accepts any
refusing answer, `refused` and `unauthenticated` among them.

`relied` is the reliance boolean of §11. It must be `true` for `current`
and `false` for everything else, on every answer, whatever the case is
about. The case is graded on its conclusion; the boolean's value is judged
separately on every answer and charged to C12, whose row in the report
counts those judgements beside its own cases. An implementation whose
conclusions are right and whose boolean is wrong fails C12 and nothing
else. An answer that carries no boolean at all is not a verify_record
response, and, like one that carries no conclusion, it is an ERROR against
its case.

### `reliance` (C12)

Given `{"conclusion": "stale"}`, answer `{"relied": false}`. The suite asks
once for each of the nine conclusions.

### `matches` (§9)

Given a record and a `corpora` object (corpus name to digest), answer
`{"matches": true|false}`: whether the record covers that corpus set. §9
requires `false` for a specimen against any set at all.

### `check_successor` (§10, C14)

Given two status lists as text, answer `{"accepted": true|false}`: whether
`successor` may follow `previous`. A successor may escalate a finding and
never weaken or drop one; its `sequence` is one more; its `previous_digest`
is `SHA(CANON(previous))`, which is ARCS-1's notation for the SHA-256 digest
(Secure Hash Algorithm, 256-bit) of the canonical form of the previous
list, with that list's attestation included.

### `build_record` (§5, §6, C15)

Given `fields`, the text of a record without `record_id` or `attestation`,
answer `{"document": "<the built record, as JSON text>"}` or
`{"refused": true}`. The built record carries every given field unchanged
and the derived `record_id`, and nothing else. The suite asks twice where C15
requires it and compares the two texts byte for byte. Every instant is an
argument, so nothing in a build may come from a clock.

---

## 3. How answers are graded

| where ARCS-1 | the case accepts |
| --- | --- |
| names the answer | that answer and no other |
| says only that a document is refused, or stops without naming a conclusion | any refusing answer: the nine conclusions except `current`, and `refused` |
| says a record is refused *although its identifier is sound* (C3) | any refusing answer except `unsound_id` |
| describes one situation in two steps that answer differently | either (question 3 below) |
| (any verify_record answer) | `relied` equal to whether `conclusion` is `current`; a disagreement is C12's FAIL, never the case's |

**Controls.** A case that asks only for a refusal is passed by a program
that refuses everything. So wherever a criterion's other cases ask for
nothing but refusals, the criterion also carries a control, a case whose
identifier contains `-control-`: the same artefacts with the one defect
absent, which must come out `current`, or as the finding where the negative
is about a finding. A refusal counts only beside an acceptance of its twin,
and no constant answer to any operation passes all of a criterion's cases of
that operation, except `matches` under C5, where §9 states only the false
side (question 11). One consequence is deliberate: a verifier that cannot
answer `current` at all fails every control, and every criterion that
carries one fails with it, because its refusals cannot be told from
refusing everything.

A case is **PASS** when the answer is one the clause allows, **FAIL** when
it is one the clause forbids, and **ERROR** when there was no answer to
grade. Each case says, in `--list` and in `--dump`, which clause it rests on
and on what basis: `criterion` (the test §12 itself gives), `must` (a
requirement stated elsewhere in the text), or `reading` (a question the text
leaves open; see section 5). Readings are reported apart and count towards
nothing.

---

## 4. Trust anchors and test keys

ARCS-1 fixes an anchor's `schema` string (§7) and says it carries a `keys`
array, and says nothing else about its shape (question 5 below). The suite
therefore hands anchors over in the shape of the published specimen anchor:

```json
{"schema": "aero-dossier-trust-anchor/v1",
 "keys": [{"key_id": "k_...", "public_key": "<64 hexadecimal characters>",
           "algorithm": "ed25519", "issuer": "...", "note": "..."}]}
```

Entries may carry other fields, as the published anchor's do, and an
adapter must tolerate them.

Every artefact the suite signs is signed by one of three test keys. Each
private key is the SHA-256 of the UTF-8 text
`ARCS-1 conformance suite test key: ` followed by its label, `issuer`,
`second issuer` or `forger`. Ed25519, the Edwards-curve Digital Signature
Algorithm that RFC 8032 (a Request for Comments) defines, signs
deterministically, so anyone holding that sentence and the specification
can regenerate every artefact in the suite byte for byte, which is also why
these keys protect nothing and must never appear in an anchor anybody
relies on.
`python3 -m arcs_conformance --dump DIR` writes every request, with its
expected answer, as a JSON file per case.

---

## 5. Where ARCS-1 leaves the answer open

These are findings about the specification (edition 2026-09-26). §15 says
where such findings go; until an edition settles one, each item says what
the suite does meanwhile.

1. **No conclusion for a refusal before step 5.** §11 lists nine
   conclusions. Steps 0, 1 and 4 refuse without naming one, and step 3 says
   *stop*. The protocol adds `refused`, and a case that turns on any of
   these steps accepts every refusing answer.
2. **A record with no status list.** §11 supplies a list *when standing is
   in question*; §10 grants assurance *only by a list that is in scope,
   authenticated and fresh*. Whether a record checked without a list can be
   `current` is not said. Normative cases accept `current` or `unknown`
   there; the reading `c10-reading-no-status-list` records the suite's view,
   that it cannot.
3. **One side signed, the other not.** For a signed record and an unsigned
   list, or the reverse, step 6.3 (keys differ: `unknown`) and step 6.5
   (unsigned: `unauthenticated`) both apply. Normative cases accept either;
   the reading `c11-reading-unsigned-list-against-signed-record` records the
   suite's view that an unsigned list cannot withdraw a signed record.
4. **Where the three specimen marks are checked.** §9 requires them to
   agree and §11 gives the check no step and no conclusion. The suite
   accepts any refusal. Nor does the text say whether a specimen whose
   three marks agree is refused at verification at all; §9 says only that
   it matches no corpus set. The reading
   `c5-reading-marked-specimen-verifies` records the suite's view, that it
   is refused at matching and not at verification, and so verifies as
   `current` when it is checked with a fresh status list that carries no
   finding against it.
5. **The anchor document.** Only `schema` and `keys` are named. The fields
   of a key entry, whether others are tolerated, and what a verifier does
   with an entry whose `key_id` is not its key's are not said.
6. **Is `public_key` optional?** §8 lists it among *exactly these fields*;
   §11 step 3 says *if the record also carries* it. Not tested.
7. **Is `not_after` inside the window?** The name says yes; C6's reason (a
   window with equal ends covers no time) says no. Not tested at the
   boundary; the minimal adapter reads the window as half-open.
8. **Escaping inside strings.** §3's four rules do not say whether a
   newline is `\n` or `\u000a`, or whether `/` is escaped. The reading
   `c1-reading-string-escapes` takes the form the §3 Python line emits,
   which is also that of RFC 8785 (JSON Canonicalization Scheme), a
   different canonical form that ARCS-1 does not use.
9. **Floats, `NaN` and duplicate keys in a verifier.** §3 says a conforming
   implementation must respect them; §11 step 1 does not list them. The
   suite treats refusal as required.
10. **When `binding_integrity` is owed.** *Required when the record names a
    corpus that references another corpus it also names*: a verifier cannot
    decide that from the record alone. Its absence is not tested.
11. **The corpus-matching function** is named in §9 and not defined. The
    reading `c5-reading-record-matches-its-corpora` takes digest-for-digest
    equality over the corpora the record names.
12. **Must a successor carry `previous_digest`?** §10 marks it optional
    without saying whether that is for the first list only. Not tested; the
    minimal adapter requires it of a successor.
13. **What weakens a finding.** C14 forbids weakening without defining it.
    The reading `c14-reading-finding-postponed` treats moving a finding's
    `at` later as weakening. A changed `superseded_by` is not tested.
14. **A finding dated after its list was cut.** The §13 vector withdraws a
    record with effect three days after the list's `as_of`. Nothing says
    whether that is intended; the suite follows the vector.
15. **A list read about an instant before its own `as_of`** is not
    addressed. Not tested.
16. **200 characters.** Whether the limit on `reason` counts Unicode code
    points or UTF-16 units is not said. Tested with ASCII only.
17. **Time-stamps.** The published specimen carries, under `provenance`,
    a time-stamp token under RFC 3161 (the Internet X.509 Public Key
    Infrastructure Time-Stamp Protocol, X.509 being the standard format for
    public-key certificates), which a time-stamping authority signs to show
    that given data existed at a given time. ARCS-1 does not
    define it, so no case tests it and no conforming verifier is required to
    check it.
18. **The keys of `entries`.** *record_id to finding*, with no form stated
    for a key that is not a serial. Not tested.
19. **Integer range.** *Counts are integers*, unbounded. A runtime with
    53-bit numbers would diverge above 2^53. Tested to 41 bits only.
20. **Leap seconds.** RFC 3339 (Date and Time on the Internet: Timestamps),
    which §4 narrows, allows `:60`; §4 does not say. Not tested.
21. **The `at` argument itself.** Whether a verifier must refuse an `at`
    with an offset, as it must inside an artefact, is not said. Not tested.
22. **C5's own test cannot fail.** Deleting `specimen` from a signed
    specimen changes its payload, so every verifier refuses the result at
    step 2 as `unsound_id`, whether or not it checks the three marks. The
    test with teeth is one C5 does not state: drop the flag and re-derive
    the serial (`c5-flag-dropped-and-reissued`). The suite runs C5's test as
    stated and does not count on it.
23. **Where a malformed serial is caught.** Step 1 checks the record
    against §5, where `record_id` is a required field, and step 2
    recomputes it. A serial in the wrong form, uppercase hexadecimal say,
    can therefore be refused at step 1 or found unsound at step 2, and
    `c4-serial-in-uppercase` accepts any refusal. A serial of the right form
    that does not recompute is step 2's alone, and those cases accept only
    `unsound_id`.
24. **No status list for the specimen key.** The specimen and its anchor
    are published; a list signed by the specimen key is not, and nobody
    else can make one. So the specimen can never be shown `current` under a
    list, and a case built on it cannot tell a verifier that checks the
    anchor from one that ignores it, unless that verifier reads a record
    with no list as `current` (question 2). The specimen cases say so, and
    `c8-forged-key-refused` and `c9-empty-anchor` carry the anchor checks.
