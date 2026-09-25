# Contributing

Thank you for helping. This is the conformance suite for the Agent
Run Conformance Specification (ARCS-1), maintained by Ashforde OÜ, a
private limited company (osaühing) registered in Estonia. The suite is only
worth running if its cases are right, so contributions are held to one
standard above all: every case must be a fair question under the text of
ARCS-1, and must say which clause makes it one. That matters more than
coverage, and much more than speed. Terms of art are defined in
[docs/GLOSSARY.md](docs/GLOSSARY.md).

How decisions are made is in [GOVERNANCE.md](GOVERNANCE.md). Participation
is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). A security issue,
including a case that lets a wrong implementation pass, goes through
[SECURITY.md](SECURITY.md), not a public issue.

## Before you start

For anything beyond a small fix, open an issue first, so that the change is
agreed before you spend time on it. There are three issue forms:

- **Case defect**: a case expects an answer ARCS-1 does not require, or its
  note does not match what it builds.
- **Specification question**: ARCS-1 does not settle an answer, and you
  want to discuss how the suite treats it.
- **Report a result**: you ran the suite against an implementation and want
  to tell us, publicly.

## Development

The suite uses the Python standard library alone, and must keep running on
the oldest Python the continuous integration (CI) workflow names (3.9). No
package is installed; clone and run.

```sh
python3 -m unittest discover -s tests                        # the suite's own tests
python3 -m arcs_conformance --impl 'python3 reference/adapter.py'   # must hold every criterion
python3 tools/gen_readme.py && python3 tools/gen_assets.py   # regenerate after any change
```

Run the tests under Python 3.9 as well as your usual version if you can;
CI runs every version the README names. A single test file runs on its own
as `python3 tests/test_runner.py`.

## Proposing a case

A new case, or a change to what a case accepts, needs all of these:

1. **The clause.** Name the section and step of ARCS-1 the case rests on,
   in the `clause` field (`§11 step 3` for section 11, step 3). Do not paste
   the specification's text into the case; cite it.
2. **The basis.** `criterion` if it is the test §12 itself states for the
   criterion, `must` if it rests on a requirement stated elsewhere, and
   `reading` if the text does not settle the answer. A reading counts
   towards nothing and needs an entry in PROTOCOL.md section 5.
3. **A negative and a positive.** The negative makes one change to a sound
   artefact, and is re-derived and re-signed so that the one change is all
   that is wrong, unless the case is about the identifier or the signature
   itself. If the criterion's other cases ask only for refusals, add a
   control (an identifier containing `-control-`): the same artefacts with
   the defect absent, which must be accepted. Otherwise a program that
   refuses everything would pass.
4. **The expected answers**, as the set the clause allows: where ARCS-1
   names the answer, that answer alone; where it says only that a document
   is refused, every refusing answer. PROTOCOL.md section 3 gives the rule.
5. **A note** in plain words saying what the artefact is and what the one
   change breaks.
6. **Tests.** Pin the case's answer set in `tests/test_expectations.py`.
   The reference adapter must pass it (`tests/test_reference.py`), no
   constant answer may pass all of its criterion's cases of that operation
   (`tests/test_blind.py`), and if a defect in `tests/broken_adapter.py`
   should now fail it, update that defect's pin in `tests/test_broken.py`.
   If no existing defect fails the new case, consider adding one that does:
   a case nothing can fail has not shown it can catch anything.

Then regenerate the README and the images; the counts, the coverage table
and the chart change with the catalogue.

## Raising a specification question

The suite never settles a question ARCS-1 leaves open. It records a
reading, reports it apart, and counts it towards nothing. If you have found
such a question:

- If it is not already in PROTOCOL.md section 5, open a *Specification
  question* issue. Say which sections are involved, what the two possible
  answers are, and what an implementation would do differently under each.
- ARCS-1 §15 treats a passage that cannot be implemented from the text
  alone as a defect in the specification, reported to contact@ashforde.org
  and corrected in a new edition. The issue here is for how the suite
  should behave meanwhile.

## What not to change

- **`spec/`** is a byte copy of the published specification and is never
  edited here. A new edition is copied in whole, with its checksum file
  `SHA256SUMS`, and its digest is added to `PUBLISHED` in
  `arcs_conformance/spec.py`.
- **Generated files.** The README's `<!-- gen:... -->` blocks and every
  file in `docs/assets/` are written by `tools/gen_readme.py` and
  `tools/gen_assets.py`. Change the generator or the tree, then regenerate;
  a test fails if a committed copy is stale.
- **The vendored `arcs_conformance/ed25519.py`** is kept identical, below
  its header, to its source in Aero Agent Skills, Ashforde OÜ's open
  library of aerospace engineering skills for artificial intelligence (AI)
  agents.

## Style

- **Code:** standard library only; Python 3.9 syntax; comments explain why
  a thing is done, not what the next line does. Match the surrounding code.
- **Prose:** plain declarative British English, the reason before the
  mechanism, no marketing language and no emoji. A figure in prose is a
  copy: prefer a generated block, and if a sentence must state a count,
  add a check for it in `tests/test_docs.py`.
- **Plain words:** write for a reader who has never met ARCS-1. Spell out
  every abbreviation, standard number and code-name at its first use in
  each file, then use the short form, and give a new term of art an entry
  in [docs/GLOSSARY.md](docs/GLOSSARY.md). `tests/test_plain_language.py`
  reads the glossary's abbreviation table and fails when a public file uses
  one before spelling it out, cites a conformance criterion by its number
  without the words ARCS-1 §12 gives it, or uses a short form the table
  does not carry; a new abbreviation goes into that table and the test's
  list together.
- **Commits:** a short imperative subject in lower case, saying what the
  change does (`add a control for C9`, C9 being the conformance criterion
  that an empty anchor cannot produce a pass), and a body saying why when
  it is not obvious. One coherent change per commit.
- **Changelog:** add a line under `[Unreleased]` in
  [CHANGELOG.md](CHANGELOG.md) for any change a user of the suite would
  notice.

## Sign-off: the Developer Certificate of Origin (DCO)

Every commit you contribute must carry a `Signed-off-by` line, which
certifies that you wrote the change or otherwise have the right to submit
it under the project's licence, as the
[Developer Certificate of Origin](https://developercertificate.org/)
(version 1.1) sets out. Add it with:

```sh
git commit -s
```

Use your real name. There is no contributor licence agreement and no
copyright assignment: your contribution is licensed under the Apache
License, Version 2.0, as its section 5 provides, and you keep the copyright
in it. [LICENSING.md](LICENSING.md) explains the terms of the repository.
