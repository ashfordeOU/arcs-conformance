# Glossary

Plain-language definitions of every term of art and every abbreviation used
in this repository, for a reader who has never met the specification or the
company behind it. Each entry says what the thing is in a sentence or two.
Where a term comes from the specification, the entry names the section that
defines it, so that the specification stays the authority and this page
stays a guide.

The specification is the Agent Run Conformance Specification
(ARCS-1), published by Ashforde OÜ, a private limited company (osaühing)
registered in Estonia. A copy is in [spec/ARCS-1.md](../spec/ARCS-1.md). A
reference such as §11 means section 11 of it, and §11 step 3 means step 3 of
that section.

The entries under *Start here* are the ones the README repeats in its own
Glossary section.

## Start here

**ARCS-1.** The Agent Run Conformance Specification: the public
document that says how a conformance record is written, identified, signed,
checked and withdrawn. It is the aerospace profile of TRACE (Trust, Runtime Attestation and
Compliance Evidence), below: it
defers to TRACE for everything TRACE defines, and adds the gate verdicts,
the named person who signs off, and the exact corpus and harness versions.
The number 1 identifies the specification itself: a change that altered
what conforms would be a different specification, ARCS-2, while a
correction that only clarifies is a new edition of ARCS-1, named by its
date (§14). Its one canonical copy is in `spec/` in this repository.

**TRACE.** Trust, Runtime Attestation and Compliance Evidence: the open
specification, hosted at the Linux Foundation, for a signed record of what
a software agent ran, where, under which policy and calling which tools.
ARCS-1 is a profile of it, and §17 of ARCS-1 maps each field of a
conformance record onto TRACE's record. This suite tests verifiers of
ARCS-1 records; it does not test TRACE records.

**Conformance claim.** The statement a record makes, in the words of §1:
*this runtime, against this specification, over these exact corpora, for
this period, attested by this key*.

**Record.** One conformance claim, written as a JSON (JavaScript Object
Notation) object with exactly the fields §5 defines, in the claim dialect
ARCS-1 names `claim@1`: version 1 of the conformance claim format. The
published specimen file calls a record a dossier.

**Issuer.** The party whose key signs a record. ARCS-1 treats the issuer as
the key, not as a name: a name in a field is a claim, and a signature is a
check (§2).

**Verifier.** A program that checks a record for someone about to rely on
it, following the procedure in §11, and returns exactly one conclusion.
This suite tests verifiers; it is not one.

**Trust anchor.** The set of public keys the verifier has itself decided to
trust, often shortened to anchor. It is supplied by the verifier and never
taken from the record, because a record's own key proves nothing: a forger
ships their own key too (§2, §11 step 0).

**Status list.** A separately signed document in which the issuer states
what it now says about records it has already issued: which have been
withdrawn and which superseded (§10).

**Standing.** Whether a record is still in force. A record cannot state its
own standing, because it cannot be edited once issued; only the issuer's
status list can (§10).

**Conclusion.** One of the nine answers §11 allows a verifier: `unsound_id`,
`unknown`, `withdrawn`, `superseded`, `unauthenticated`, `stale`,
`not_yet_valid`, `expired` and `current`. Only `current` permits reliance.

**Conformance criterion.** One of the fifteen tests in §12, numbered C1 to
C15, each a check a stranger can run against artefacts they already hold.
An implementation conforms to `claim@1` when all fifteen hold.

**Conformance suite.** A set of test cases that checks an implementation
against a specification. This repository is the conformance suite for
ARCS-1.

**Case.** One question put to an implementation: a request, the clause of
ARCS-1 that makes it a fair question, and the set of answers that clause
allows.

**Adapter.** A small command, written once by an implementation's authors,
that reads the suite's request as JSON on standard input, asks their
implementation, and writes the answer as JSON on standard output.
PROTOCOL.md defines everything it must do.

**Reading.** A case about a question ARCS-1 does not settle. The suite
records whether the implementation agrees with the suite's reading, reports
it under its own heading, and counts it towards nothing.

**Pass.** An answer the clause allows. A pass is evidence about the cases
that were run; it is not a certification, an approval or an endorsement by
Ashforde OÜ or by anyone (§16).

## Records and how they are checked

**Holder.** Anyone in possession of a record (§2).

**Relying party.** Anyone about to act on the strength of a record (§2).

**Implementation.** Software that does some or all of what ARCS-1 defines,
such as building records or verifying them. The suite tests an
implementation through its adapter.

**Aero Harness.** Ashforde OÜ's inspection runtime: a private program that
runs a battery of automated checks over bodies of files (corpora), records
which files it checked by their digests, and signs the result as a
conformance record. It is a harness in the software sense of a test
harness, and has nothing to do with a wiring harness. It is one
implementation of ARCS-1, whose name names no vendor. The suite neither
needs it nor contacts it; it tests the programs
that check what the Aero Harness signs.

**Aero Agent Skills.** Ashforde OÜ's open library of aerospace engineering
skills for artificial intelligence (AI) agents, published at
<https://github.com/ashfordeOU/aero-agent-skills>. It carries a pointer to
the copy of ARCS-1 in this repository, and the `skills` corpus of the
published specimen is that library.

**Aero Agent Roles.** Ashforde OÜ's open library of aerospace engineering
roles, which bind those skills into end-to-end deliverables, published at
<https://github.com/ashfordeOU/aero-agent-roles>. The `roles` corpus of the
published specimen is that library.

**Runtime.** The program that does the work, as against the documents that
describe it or the records that report it. ARCS-1 requires every record to
name the runtime that did the checking (§5); the Aero Harness is the
runtime behind the published specimen.

**Reference implementation.** The implementation ARCS-1 names as an example
of a conforming one: the Aero Harness runtime. ARCS-1 says it is never the
definition; the text is (§1).

**Corpus.** A body of files the runtime inspected; the plural is corpora. A
record names each corpus by its SHA-256 digest (Secure Hash Algorithm,
256-bit), never by a version, so that an edited corpus cannot pass as the
one that was assessed (§5). The published specimen names two corpora,
`skills` and `roles`: the Aero Agent Skills and Aero Agent Roles
libraries.

**Digest.** The fixed-length fingerprint a hash function computes from some
bytes; here always SHA-256, written as 64 lower-case hexadecimal
characters. Change one byte and the digest changes.

**Canonical serialisation.** The single byte-for-byte way §3 writes a JSON
value before it is hashed or signed: keys sorted by Unicode code point, no
spaces, characters outside ASCII (the American Standard Code for
Information Interchange) written as themselves, and no trailing newline.
ARCS-1 calls it `CANON`. Two serialisers that disagree by one byte give two
identities to one statement.

**Payload.** A record with its `record_id` and `attestation` fields
removed: the part its identifier is derived from (§6).

**Record identifier.** A record's `record_id`, also called its serial. It
is derived from the record's own payload, never assigned: the first 24
hexadecimal characters of the payload's SHA-256 digest, in three groups of
eight, after the prefix `AHD` for an issued record or `SPECIMEN` for a
specimen. Anyone holding the record can recompute it, and a mismatch means
the record was edited or its serial copied from another (§6).

**Attestation.** The signature block of a record or a status list (§8): a
signature over a digest of the document's body, with the signing key's
identifier and a context string. The signature is made with Ed25519, one
instance of the Edwards-curve Digital Signature Algorithm (EdDSA), on the
curve edwards25519.

**Malleated signature.** A signature rewritten, without the signing key,
into a second form that a careless verifier still accepts. The suite's case
`c8-signature-malleated` adds the group order to the signature's `s` value,
which RFC 8032 (Request for Comments 8032, the Edwards-Curve Digital
Signature Algorithm) section 5.1.7 forbids: a verifier must refuse a
signature whose `s` is not below that order.

**Body digest.** The SHA-256 digest of a document's canonical form with its
attestation removed, written `sha256:` and then the digest. The signature is
made over it (§8).

**Context string.** A fixed label inside the signed bytes that names what
kind of document, or what kind of signature, this is, so that one cannot be
passed off as another (§7). A record's `context` field, for example, is
`aeroskills-harness-dossier/v3`.

**Instant.** A moment in time, written exactly as `YYYY-MM-DDTHH:MM:SSZ`:
year, month, day, the letter T, hours, minutes, seconds, and the letter Z
for Coordinated Universal Time (UTC). Any other spelling must be refused,
never repaired (§4).

**Window.** The period from a record's `not_before` to its `not_after`, in
which the record says it applies (§5). Outside it a verifier answers
`not_yet_valid` or `expired`.

**Specimen.** A demonstration record, real in every respect, marked as a
specimen in three places that must agree: the `specimen` field, the start of
the `customer` field, and the `SPECIMEN` prefix of its identifier (§9). A
specimen covers no deployment.

**Finding.** One entry in a status list against one record: whether it is
withdrawn or superseded, when that took effect, and why (§10).

**Withdrawn.** The finding that says: do not rely on this record (§10).

**Superseded.** The finding that says a later record replaces this one: the
work was re-done, not found wrong, and the successor must be named (§10).

**Stale.** Said of a status list read after its own `next_update`. Its
findings still count, but it can no longer vouch that nothing has been filed
since, so it grants no assurance (§10, §11).

**Unauthenticated, unknown, unsound_id.** Conclusions that refuse reliance:
the record or list is unsigned or its signature does not check out; the
list does not govern this record, or was cut before the record existed; the
record's identifier does not recompute from its payload (§11).

**Reliance boolean.** A single true-or-false a verifier may give beside its
conclusion: true for `current` and for nothing else, so that a caller who
reads only the boolean fails safe on every form of doubt (§11).

**Successor list.** A status list that follows an earlier one: its
`sequence` is one more, it names the digest of the earlier list, and it may
escalate a finding but never soften or drop one (§10, and C14, the
criterion that a finding is never softened or dropped).

**Countermand.** The issuer's act of withdrawing or correcting records it
has already issued, under its countermand policy. ARCS-1 does not set that
policy's terms; it fixes the channel, a signed status list (§7, §14).

**Edition.** A dated revision of ARCS-1 that clarifies without changing what
conforms (§14). The README's Versioning section names the edition this suite
grades against.

**Test vector.** A worked example printed with its right answer, against
which an implementer can check their code. ARCS-1 gives its vectors in §13.

## How the suite works

**Operation.** One kind of request the suite sends to an adapter, such as
`verify_record` or `canonicalise`. PROTOCOL.md section 2 lists them all.

**Basis.** Why a case is a fair question: `criterion` (the test §12 itself
states), `must` (a requirement stated elsewhere in the text) or `reading`
(a question the text leaves open).

**Normative case.** A case whose expected answer the text of ARCS-1
settles, with the basis `criterion` or `must`. Only normative cases count
towards a criterion's verdict.

**Own test.** A normative case with the basis `criterion`: it follows the
test §12 states for its criterion.

**Derived case.** A normative case with the basis `must`: it rests on a
requirement ARCS-1 states elsewhere, which the criterion's own test does not
reach.

**Negative and positive.** A negative case makes one change to a sound
artefact, which the verifier must refuse. Its positive twin leaves the
change out.

**Control.** A case whose identifier contains `-control-`: the artefacts of
a negative case with the defect absent, which must be accepted. Without
controls, a program that refuses everything would pass every refusal.

**Reference adapter.** The file `reference/adapter.py`: a minimal
implementation written from ARCS-1 alone, which passes every case. It shows
that the cases can be passed and is a template for your own adapter. It is
not the reference implementation, and not a verifier to rely on.

**Test key.** One of the keys the suite signs its artefacts with. Each is
derived from a sentence published in PROTOCOL.md, so anyone can regenerate
every artefact; for the same reason the keys protect nothing and must never
be trusted.

**PASS, FAIL, ERROR.** The result of one case: an answer the clause allows,
an answer it forbids, or no answer that could be graded.

**Holds, fails, not shown, not run.** The verdict on one criterion: every
normative case under it passed; at least one failed; none failed but at
least one could not be graded; or none was selected on this run.

**Exit status.** The number a program returns when it ends, which scripts
and continuous integration (CI) systems act on. The README's section on
reading a report says what each of the suite's statuses means.

**Pinned digest.** The SHA-256 digest of the published `ARCS-1.md` that the
suite records, so that every report can say whether it graded against the
published text or against some other copy.

**Checksum file.** The file `spec/SHA256SUMS`, which lists the SHA-256
digest of every other file of the specification in the format
`shasum -a 256 -c` reads. The suite refuses a copy that does not match it.

**Generated block.** A part of the README between `<!-- gen:NAME -->`
markers, written from the tree by `tools/gen_readme.py`. A test fails when a
committed block differs from what the generator writes.

**Continuous integration.** Checks that run automatically on every change
pushed to the repository. Here, GitHub Actions runs the steps in
`.github/workflows/ci.yml`, and the README lists what each one shows.

## Terms from the operator records

Ashforde OÜ publishes records about its own runtime in the public repository
[Aero Harness operator records](https://github.com/ashfordeOU/aero-harness-records).
This suite tests none of it, but a reader who follows that link meets these
terms.

**Gate.** An automated check the Aero Harness runs. Each gate has a name of
the form `gate-…`, and the operator records list every gate with the date
it was last proven to catch what it is there to catch.

**Calibration.** Proving that a gate still detects the defects it was built
to detect, by planting those defects and confirming that the gate fails on
them. The operator records log every proof with its date, including a proof
that fails.

**Self-calibration.** Calibration against defects the operator wrote
itself. It is called that because nobody independent chose the defects, and
it is evidence, not certification by anyone.

**Held-out control.** A set of planted defects that a gate's author does
not get to adjust when the gate changes, so that a gate cannot be quietly
tuned to pass its own test.

**Evidence log.** An append-only public log of commitments to issued
records, built as a Merkle tree under RFC 6962 (Request for Comments 6962,
Certificate Transparency). It lets a holder prove that their record was
committed to, and anyone check that no entry was altered, removed or
inserted afterwards.

**Merkle tree.** A tree of hashes in which each node is the hash of the two
beneath it, so that a single root digest commits to every leaf. RFC 6962
fixes how the hashes are formed.

**Leaf.** One entry in the evidence log: a commitment to a record, computed
as a SHA-256 digest over a context label, the record's identifier and a
random value, called a salt, that the record carries. A leaf never contains
the record's content.

**Blinding.** Making a leaf impossible to link to its record without
holding the record. The salt does it, and every checkpoint is padded to the
same number of leaves with dummy commitments, so that the log's size says
nothing about how many records were issued.

**Checkpoint.** A published statement of the evidence log's size and root
digest at a moment. It names the checkpoint before it, carries a consistency
proof from it, and carries a time-stamp token over the rest.

**Consistency proof.** A short list of hashes, defined by RFC 6962, that
proves a later tree contains the earlier one unchanged: nothing altered,
removed or inserted.

**Time-stamp token.** A statement, signed by a time-stamping authority (TSA)
under RFC 3161 (Request for Comments 3161, the Internet X.509 Public Key
Infrastructure Time-Stamp Protocol), that given data existed at a given
time; X.509 is the standard format for public-key certificates. ARCS-1 does
not define one, so this suite does not test the token the published
specimen carries.

## Abbreviations

Every abbreviation, code-name and standard number used in this repository,
spelled out. `tests/test_plain_language.py` reads this table and fails when
a public file uses one of these before it has spelled it out.

| abbreviation | stands for | notes |
| --- | --- | --- |
| ARCS | Agent Run Conformance Specification | the name of the specification series |
| ARCS-1 | the first Agent Run Conformance Specification | the specification this suite tests; its editions are named by date |
| AHD, AHS | no expansion: the prefix of an issued record's identifier and of a status list's identifier | ARCS-1 §6 gives them as prefixes only |
| Aero Agent Roles | Ashforde OÜ's open library of aerospace engineering roles, which bind skills into end-to-end deliverables | the `roles` corpus of the published specimen |
| Aero Agent Skills | Ashforde OÜ's open library of aerospace engineering skills for artificial intelligence (AI) agents | it points to ARCS-1's canonical copy in this repository; the `skills` corpus of the published specimen |
| Aero Harness | Ashforde OÜ's inspection runtime, which is private | it runs the checks and issues the records ARCS-1 defines |
| AI | artificial intelligence | |
| Apache-2.0 | Apache License, Version 2.0 | the licence of the suite's code and documentation |
| API | application programming interface | |
| ASCII | American Standard Code for Information Interchange | the 128-character set of basic Latin letters, digits and symbols |
| C1 to C15 | the fifteen conformance criteria of ARCS-1 §12 | each is named in words in the README's coverage table |
| CANON | canonical serialisation, ARCS-1's own name for it | ARCS-1 §3 |
| CC BY 4.0 | Creative Commons Attribution 4.0 International | the licence of the Contributor Covenant text in CODE_OF_CONDUCT.md |
| CFF | Citation File Format | the format of CITATION.cff |
| CI | continuous integration | the automatic checks on every change |
| claim@1 | conformance claim format, version 1 | defined by ARCS-1 |
| DCO | Developer Certificate of Origin | the statement a contributor's sign-off makes |
| Dependabot | GitHub's service that proposes updates to the versions a repository pins | here it watches only the pinned actions in .github/workflows |
| Ed25519 | one instance of the Edwards-curve Digital Signature Algorithm (EdDSA), on the curve edwards25519 | the signature scheme ARCS-1 uses, from RFC 8032 |
| EdDSA | Edwards-curve Digital Signature Algorithm | RFC 8032 |
| EE | Estonia, as a two-letter country code | in the citation metadata |
| FAQ | frequently asked questions | |
| hex | hexadecimal | numbers in base 16, written with 0 to 9 and a to f |
| ID | identifier | |
| JSON | JavaScript Object Notation | the text format of every record, list, request and answer |
| NaN | not a number | a floating-point value JSON does not allow |
| OÜ | osaühing | an Estonian private limited company |
| POSIX | Portable Operating System Interface | the family of standards Linux, macOS and similar systems follow |
| PR | pull request | a proposed change on GitHub |
| RFC | Request for Comments | the numbered series in which Internet standards are published |
| RFC 2119 | Key words for use in RFCs to Indicate Requirement Levels | fixes what *must*, *should* and *may* mean in ARCS-1 |
| RFC 3161 | Internet X.509 Public Key Infrastructure Time-Stamp Protocol | how a time-stamping authority signs a time-stamp token; X.509 is the standard format for public-key certificates |
| RFC 3339 | Date and Time on the Internet: Timestamps | the date format ARCS-1 §4 narrows |
| RFC 6962 | Certificate Transparency | the Merkle-tree log construction the operator records use |
| RFC 8032 | Edwards-Curve Digital Signature Algorithm (EdDSA) | defines Ed25519; its test vectors check the suite's signature code |
| RFC 8785 | JSON Canonicalization Scheme | the canonical form TRACE uses; ARCS-1 §3 says where its own rule agrees with it |
| SHA | Secure Hash Algorithm | ARCS-1 writes `SHA(bytes)` for the SHA-256 digest |
| SHA-256 | Secure Hash Algorithm, 256-bit | the hash function ARCS-1 uses throughout |
| SHA256SUMS | the checksum file of the specification | one SHA-256 digest per file |
| SPDX | Software Package Data Exchange | the standard short names for licences, such as Apache-2.0 |
| stderr | standard error | |
| stdin | standard input | |
| stdlib | standard library | |
| stdout | standard output | |
| SVG | Scalable Vector Graphics | the format of every image in docs/assets |
| TRACE | Trust, Runtime Attestation and Compliance Evidence | the open specification ARCS-1 is a profile of |
| TSA | time-stamping authority | |
| URL | Uniform Resource Locator, a web address | |
| UTC | Coordinated Universal Time | |
| UTF-8, UTF-16 | Unicode Transformation Format, 8-bit and 16-bit | ways of writing Unicode text as bytes |
| X.509 | the standard format for public-key certificates | named in the title of RFC 3161 |
| YAML | YAML Ain't Markup Language | a plain-text data format |
