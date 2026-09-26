# Licensing

This repository is the conformance suite for the Agent Run
Conformance Specification (ARCS-1). It is published by Ashforde OÜ, a
private limited company (osaühing) registered in Estonia, and it carries
files under two sets of terms, and it matters which is which. This page
says, in plain language, what each set covers and what you may do. It is a
guide, not legal advice, and it changes neither set of terms. The binding
texts are [LICENSE](LICENSE) (the Apache License, Version 2.0) and
[spec/LICENSE](spec/LICENSE) (the terms of section 16 of ARCS-1, written
§16 below); where this page and those texts differ, the texts govern.

## In short

| what | terms | where they are stated |
| --- | --- | --- |
| the suite, the cases, the reference adapter, the tests, the tools, the images and the documentation: everything outside `spec/` except `CODE_OF_CONDUCT.md` | Apache License, Version 2.0 (Apache-2.0) | [LICENSE](LICENSE), [NOTICE](NOTICE) |
| `spec/`: the copy of the ARCS-1 specification, its specimen and trust anchor, its `LICENSE` and its checksum file `SHA256SUMS` | the terms of ARCS-1 §16 | [spec/LICENSE](spec/LICENSE), and §16 of [spec/ARCS-1.md](spec/ARCS-1.md) |
| `CODE_OF_CONDUCT.md` | Creative Commons Attribution 4.0 International (CC BY 4.0), as the Contributor Covenant is | <https://creativecommons.org/licenses/by/4.0/> |

What you may do, whichever you are:

- **Run the suite**, against any implementation, as often as you like,
  commercially or not. No permission is needed and nothing is owed.
- **Implement the specification**, and build and sell a verifier from it.
  ARCS-1 §16 grants that to any person, with no permission from Ashforde OÜ
  and no obligation to it.
- **Publish your result.** No permission is needed. Publishing the whole
  report, rather than a headline figure, is a request, not a condition; the
  README says why.
- **Copy, change and redistribute the suite**, on the Apache terms below.

What nothing here grants:

- **Any right to the reference implementation** ARCS-1 mentions, which is
  the Aero Harness, Ashforde OÜ's inspection runtime, and is private.
  ARCS-1 §16 says that implementing the specification grants none.
- **Any right to the names "Aero Harness", "ARCS" or "Ashforde", or any
  mark.** The terms of `spec/` do not mention them, and the Apache License
  says in its section 6 that it grants no permission to use the licensor's
  trade names or marks, beyond the reasonable and customary use needed to
  describe where the work came from.
- **A certification.** A result from this suite is evidence about the cases
  it ran. ARCS-1 §16: conformance to the specification is not certification
  by Ashforde OÜ.

## The suite: Apache License, Version 2.0

Everything in this repository outside `spec/`, apart from
`CODE_OF_CONDUCT.md`, is Copyright 2026 Ashforde OÜ and licensed under the
Apache License, Version 2.0. The full text is in [LICENSE](LICENSE),
exactly as the Apache Software Foundation publishes it. In short, the
licence lets you use, copy, modify and distribute the suite, in source or
compiled form, for any purpose, and grants a patent licence for the
contributions it covers. In return, when you redistribute it you:

- give recipients a copy of the licence;
- keep the copyright, patent, trademark and attribution notices, including
  those in [NOTICE](NOTICE);
- state, in any file you changed, that you changed it.

It comes without warranty or liability (sections 7 and 8). If you fork the
suite, please give the fork a name that cannot be mistaken for this one,
and say which version of this suite it started from, so that a result from
your fork is never read as a result from this suite.

## `spec/`: the terms of ARCS-1 §16

`spec/` is the one canonical copy of the ARCS-1 specification directory,
which Ashforde OÜ publishes here, at
<https://github.com/ashfordeOU/arcs-conformance/tree/main/spec>, beside the suite that grades against it. It is
**not** under the Apache License, and the Apache License at the root of
this repository does not replace its terms. The suite carries it because
it grades against it, and checks it against its own checksum file,
`SHA256SUMS`, every time it runs.

Its terms are those of ARCS-1 §16, which `spec/LICENSE` repeats word for
word:

> Any person may copy this document and the files published beside it, quote
> them, implement the specification, and build and sell a verifier from it,
> with no permission from Ashforde OÜ and no obligation to it. These terms
> travel with the files: they apply wherever a copy is found, and a licence
> covering the repository that happens to carry a copy does not replace
> them. Implementing the specification grants no right to the reference
> implementation, and conformance to it is not certification by
> Ashforde OÜ.

Two practical consequences:

- **Do not edit `spec/`.** It is a copy of a published text, and a copy
  that differs from its `SHA256SUMS` is refused by the suite. A defect in
  the specification is reported to Ashforde OÜ under ARCS-1 §15 and
  corrected in a new edition, which the suite then copies in whole.
- **Keep its terms with it.** If you redistribute the suite, `spec/` goes
  with its own `LICENSE`, and the Apache License does not cover it.

## Stating conformance

Publishing a result is free: the report, the command line, the suite
version and the specification digest it names. That is what this
repository is for. So is the plain statement, in the course of trade or
anywhere else, that a product implements ARCS-1 and that these criteria
held on this version of this suite. A badge is a published result too when
it reports one: `ARCS-1: C1 to C15 hold, arcs-conformance 2.0.0` names the
conformance criteria that held and the suite version that was run, and
needs no permission either.

Presenting a product under Ashforde OÜ's names is a separate
conversation: "Aero Harness", "ARCS" or "Ashforde" in a product name or a
logo, or any presentation suggesting that Ashforde OÜ stands behind the
claim, endorses the product or has approved it. Nothing in this repository
grants that, and nothing here sets its terms. Write to
contact@ashforde.org.

None of this narrows ARCS-1 §16. Anyone may implement the specification,
and build and sell a verifier from it, without asking.

## Contributions

Contributions are accepted under the Apache License, Version 2.0, as its
section 5 provides: what you contribute is licensed on the same terms as
the rest of the suite. There is no contributor licence agreement and no
copyright assignment; you keep the copyright in your contribution. Each
contributed commit is signed off under the
[Developer Certificate of Origin](https://developercertificate.org/)
(DCO), as [CONTRIBUTING.md](CONTRIBUTING.md) describes. Changes to `spec/` are not
accepted as pull requests, because the directory is built from the
reference implementation's tree and published here unchanged; a defect in
the specification is reported under ARCS-1 §15.

## Third-party material

- `arcs_conformance/ed25519.py`, the suite's Ed25519 signature code (one
  instance of the Edwards-curve Digital Signature Algorithm), is vendored,
  unmodified below its header, from Aero Agent Skills, Ashforde OÜ's open
  library of aerospace engineering skills for artificial intelligence (AI)
  agents, which it also publishes under the Apache License, Version 2.0
  ([NOTICE](NOTICE)).
- The test vectors in `tests/test_ed25519.py` are those of RFC 8032
  (Request for Comments 8032, Edwards-Curve Digital Signature Algorithm
  (EdDSA)), section 7.1.
- `CODE_OF_CONDUCT.md` is the Contributor Covenant, version 2.1, with only
  the contact filled in, and carries its own attribution.

The suite has no other dependency: it uses the Python standard library
alone.

## Questions

Licensing questions, and anything this page does not answer:
**contact@ashforde.org**. Ashforde OÜ, registry code 17321180, Ahtri tn 12,
Kesklinna linnaosa, 15551 Tallinn, Harju maakond, Estonia.
