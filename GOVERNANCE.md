# Governance

This page says who decides what goes into the suite, and on what grounds.
It is short because the project is small, and it describes the project as
it is rather than as a committee it does not have.

## Maintainer

The suite is maintained by Ashforde OÜ, a private limited company
(osaühing) registered in Estonia (contact@ashforde.org), which also
publishes the specification the suite tests: the Agent Run
Conformance Specification (ARCS-1). The maintainer decides what is merged
and what is released, and records the reason when it declines a proposal.

## The specification decides, not the suite

The suite tests ARCS-1; it does not extend it. Every normative case must
rest on a clause of the published text. Where the text does not settle an
answer, the suite records a reading, counts it towards nothing, and lists
the question in PROTOCOL.md section 5. A disagreement about what a case
should accept is settled by the text, not by what the maintainer's own
implementation happens to do. If the text cannot settle it, the question
is a defect in the specification (ARCS-1 section 15), and the suite waits
for an edition that settles it.

Because the same company publishes the specification and maintains the
suite, that separation is kept in the open: a case that expects something
the text does not say is a defect in the suite, whoever wrote it, and
anyone may report it.

## How decisions are made

1. **In the open.** A substantive change starts as an issue, so that the
   reason for it and the alternatives are on the record.
2. **Against the bar below.** A change that meets it and draws no sustained
   objection goes ahead.
3. **The maintainer decides a disagreement**, by the text of ARCS-1 and the
   bar below, and records why.

## The bar

These hold whatever is decided:

- Every case cites its clause and states its basis.
- No criterion can hold for a program that checks nothing.
- The reference adapter, written from the specification alone, passes
  every normative case.
- Every figure the README states is generated from the tree, or checked by
  a test against it.
- The suite needs nothing but the Python standard library, and no network.
- `spec/` is a byte copy of a published text, never edited here.

## Releases

Releases follow the policy in the README's
[Versioning](README.md#versioning) section, and every change a user would
notice is recorded in [CHANGELOG.md](CHANGELOG.md). Only the maintainer
tags a release.

## Conduct and security

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
Security issues follow [SECURITY.md](SECURITY.md).

## Changing this page

A change to governance is proposed as a pull request and decided as above.
