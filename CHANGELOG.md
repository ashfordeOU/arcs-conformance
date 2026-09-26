# Changelog

Every change a user of this conformance suite, for the Agent Run
Conformance Specification (ARCS-1), would notice is recorded here, newest
first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow the policy in the README's
[Versioning](README.md#versioning) section: a result is always quoted with
the suite version that produced it and the digest of the specification it
was graded against.

The figures in an entry describe that release and are not updated
afterwards. The current figures are in the README, which generates them from
the tree.

## [Unreleased]

Nothing yet.

## [2.1.0] — 2026-09-26

ARCS-1 is now the aerospace profile of TRACE (Trust, Runtime Attestation
and Compliance Evidence), and its one canonical copy lives here. The suite
grades against edition 2026-09-26 as published, pinned by the SHA-256
digest (Secure Hash Algorithm, 256-bit) of `ARCS-1.md` (`6d68f8d5d9ea2ec130dacb9c9d2af50cae67008f3a2b77911e5b66f58d05ccec`).

### Changed

- **The specification is a profile, not a standard of its own.** Edition
  2026-09-26 states that ARCS-1 defers to TRACE for everything TRACE
  defines, and adds only the gate verdicts, the named person who signs off,
  and the corpus and harness versions. Its new §17 maps each field of a
  conformance record onto TRACE's record. §4 to §13, the fifteen criteria
  and the four worked examples are unchanged, so no case changed and an
  implementation that passed 2.0.0 passes this release.
- **The canonical copy.** `spec/` is now the one canonical copy of the
  specification directory, published here beside the suite rather than in
  Aero Agent Skills, the open library of aerospace engineering skills,
  which now carries a pointer to it. The earlier edition's digest
  stays pinned, so a copy of it is still graded as published.

The suite is unchanged in size: 141 cases in seven operations: 135
normative cases across the fifteen conformance criteria (C1 to C15) of
ARCS-1 section 12, and 6 readings. The adapter kept broken on purpose still
comes with seventeen named defects, and `PROTOCOL.md` section 5 still
lists twenty-four places the specification leaves open.

## [2.0.0] — 2026-09-24

The specification is renamed, and the suite with it. It grades against
ARCS-1, the Agent Run Conformance Specification, edition 2026-09-24 as
published, pinned by the SHA-256 digest (Secure Hash Algorithm, 256-bit) of `ARCS-1.md`
(`10e0a328fb3a489f3c65678a708b68fc06bef1c9cdf9e5dc67dbe9c8dfc6d1d8`).

### Changed

- **The name.** The specification's name now names no vendor, because the
  body that publishes it is to be one that does not trade in what it
  certifies. The value every record carries in its `spec` field is
  `ARCS-1`, and a record carrying any other value is read under that one or
  not at all.
- **The package and the repository.** The suite runs as
  `python -m arcs_conformance`, and lives at
  `https://github.com/ashfordeOU/arcs-conformance`. This is why the major
  version moves: a command that ran the suite before does not run it now.
- **The published copy.** `spec/` is the set published with the new
  edition, with the specimen issued under the new name. The worked examples
  in section 13 were recomputed, because the name is inside the bytes they
  digest; no criterion, clause or case changed.

The suite is unchanged in size: 141 cases in seven operations: 135
normative cases across the fifteen conformance criteria (C1 to C15) of
ARCS-1 section 12, and 6 readings. The adapter kept broken on purpose still
comes with seventeen named defects, and `PROTOCOL.md` section 5 still
lists twenty-four places the specification leaves open.

## [1.0.0] — 2026-09-22

The first release. It grades against ARCS-1 edition 2026-09-21 as
published, pinned by the SHA-256 digest (Secure Hash Algorithm, 256-bit) of
`ARCS-1.md`
(`3f46642d52c4f90b67c838e84a900420709da1c2f055af852d0bda8fba9cc6a1`).

### Added

- **The suite.** 141 cases in seven operations: 135 normative cases across
  the fifteen conformance criteria (C1 to C15) of ARCS-1 section 12, and 6
  readings. Every case cites the clause it tests and states its basis: the
  criterion's own test, a *must* stated elsewhere in the text, or a reading
  of a question the text leaves open. Readings are reported apart and count
  towards nothing.
- **The adapter protocol** `arcs-conformance-adapter/1`
  ([PROTOCOL.md](PROTOCOL.md)): one JSON (JavaScript Object Notation)
  request on standard input, one JSON answer on standard output, one
  process per call, so that an implementation in any language can be tested
  without linking to anything.
- **Controls.** Every criterion whose other cases ask only for a refusal
  carries a twin that must be accepted, so no constant answer passes all of
  a criterion's cases of one operation (with the one exception PROTOCOL.md
  question 11 explains), and a program that checks nothing fails every
  criterion.
- **The reliance boolean** is judged on every `verify_record` answer and
  charged to C12 (one conclusion permits reliance), so a wrong boolean
  fails C12 and does not blame the criterion whose case it rode on.
- **The report**: every case, then every criterion with its own counts and
  verdict (*holds*, *fails*, *not shown*, *not run*), then a closing line
  that names criteria and totals nothing. Exit statuses 0 to 3. `--json`
  writes the whole report for a machine; `--list`, `--dump`, `--only`,
  `--case`, `--timeout`, `--jobs` and `--spec` select and inspect.
- **The copy of ARCS-1 in `spec/`**, refused unless it matches its own
  checksum file, `SHA256SUMS`, with the published text's digest pinned so that a report
  about any other copy says so in its header and its closing line.
- **The reference adapter** (`reference/adapter.py`), written from ARCS-1
  alone and sharing only the Ed25519 signature code with the suite
  (Ed25519 being one instance of the Edwards-curve Digital Signature
  Algorithm). It holds C1 to C15.
- **The suite's own tests**: a broken adapter with seventeen named
  defects, sixteen of them pinned to the cases they must fail and the
  criteria they must break, and one that breaks too much for such a list
  and is held to the single property the protocol states for it; a program
  that checks nothing, which must fail every criterion; and the answer set
  of every case, pinned a second time by hand.
- **Where ARCS-1 is unclear**: PROTOCOL.md section 5 lists twenty-four
  places where the specification does not settle an answer, with what the
  suite does meanwhile.
- **A glossary**, [docs/GLOSSARY.md](docs/GLOSSARY.md), defining every
  term of art in plain words and carrying a table of every abbreviation,
  and a test that fails when a public file uses one of them before
  spelling it out, cites a conformance criterion by its number without the
  words section 12 gives it, or uses a short form the table does not
  carry.
- **The repository's terms and community files**: [LICENSING.md](LICENSING.md),
  [NOTICE](NOTICE), [CITATION.cff](CITATION.cff), `codemeta.json`,
  [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md) with the
  Developer Certificate of Origin, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
  (Contributor Covenant 2.1), [GOVERNANCE.md](GOVERNANCE.md), issue forms
  and a pull-request template.
- **Continuous integration** on Python 3.9 to 3.14, with every action
  pinned to a full commit hash and Dependabot, the service that proposes
  updates to the versions a repository pins, watching them.
- **Generated figures.** The README's statline, badges, tables and run
  excerpt, and every image in `docs/assets`, are written from the tree by
  `tools/gen_readme.py` and `tools/gen_assets.py`, and a test fails when a
  committed copy is stale.

