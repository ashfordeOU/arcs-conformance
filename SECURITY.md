# Security Policy

This repository is the conformance suite for the Agent Run
Conformance Specification (ARCS-1), maintained by Ashforde OÜ, a private
limited company (osaühing) registered in Estonia. A conformance suite is a
security tool at one remove: people will read its result as evidence that a
verifier refuses forged, altered and withdrawn records, and some of them
will act on that evidence. So a defect that lets a wrong implementation
pass is treated here as a security issue, not as an ordinary bug, and is
reported privately.

This policy covers the code and automation in this repository: the suite
(`arcs_conformance/`), the reference adapter, the tools and the continuous
integration (CI) workflows in `.github/`.

## Reporting a vulnerability

Report suspected vulnerabilities **privately**. Do not open a public issue
or pull request that describes the vulnerability before a fix is
available.

Write to **contact@ashforde.org** (Ashforde OÜ), with `SECURITY` in the
subject line. That address is read by the maintainer, and it is the route
to use for anything in the scope below.

## What to include

- The suite version (`python3 -m arcs_conformance --version`) and the
  identifiers of the cases involved
- The smallest adapter, or copy of the specification, that shows the
  problem
- What the suite reported, and what it should have reported
- Your impact assessment: what a wrong implementation, or an attacker,
  could get past the suite
- Optional contact details for follow-up

## Scope

- **A case that lets a wrong implementation pass.** An implementation that
  lacks a check ARCS-1 requires, trusts a key it should not, accepts an
  altered or withdrawn record, or otherwise answers as the specification
  forbids, and still gets a PASS on the case written to catch that, or
  still sees the criterion *hold*. This includes a way to make the report
  say *holds* when a normative case failed or could not be graded.
- **A runner that can be made to execute outside the adapter command.** The
  suite runs exactly the command given to `--impl`, one process per call,
  and on POSIX systems (those that follow the Portable Operating System
  Interface standards: Linux, macOS and similar) never through a shell.
  Anything in a case, a specification copy or an adapter's answer that
  makes the suite run another command, write outside the paths it was
  given, or read files it has no reason to read is in scope.
- **A path to grade against a tampered specification unnoticed.** The suite
  refuses a copy of `spec/` that fails its own checksum file,
  `SHA256SUMS`, and says in the report when an intact copy is not the
  published text it pins. A way to grade against an edited copy while the
  report still names the published text, or to make the checksum file
  reach outside the directory, is in scope.
- **A flaw in the vendored Ed25519 signature code** in
  `arcs_conformance/ed25519.py` (Ed25519 being one instance of the
  Edwards-curve Digital Signature Algorithm) that accepts a signature it
  should refuse, or refuses one it should accept.

## Out of scope

- **What the adapter does.** The suite runs the command you give it, with
  your privileges and your environment. That is its purpose, not a
  vulnerability. Run only adapters you trust, as you would any program.
- **The test keys.** Every private key the suite signs with is derived from
  a sentence published in PROTOCOL.md, on purpose, so that anyone can
  regenerate every artefact. They protect nothing and must never appear in
  a trust anchor anybody relies on.
- **A defect in an implementation under test.** Report it to that
  implementation's authors.
- **A question the specification leaves open.** PROTOCOL.md section 5 lists
  them, and section 15 of ARCS-1 says where a defect in the specification
  is reported: contact@ashforde.org. If an open question lets a wrong
  implementation pass, report it here as well.

## Disclosure policy

- Acknowledgment within 3 business days of a complete report.
- We tell you whether we accept the report as a security issue, and what
  we intend to do, as soon as we have reproduced it.
- A fix ships as a new release of the suite, with an entry in
  [CHANGELOG.md](CHANGELOG.md) that names the affected versions. Where a
  defect meant earlier results could have shown a pass they should not
  have, the entry says which cases and criteria were affected, so that
  anyone who published a result can check it.
- We do not disclose publicly before a fix is available. If a report cannot
  be fixed within 90 days, we coordinate disclosure with the reporter
  rather than remaining silent.
- Reporters are credited in release notes unless they ask to remain
  anonymous. There is no bug bounty.

## Supported versions

Only the latest release receives fixes. A result is always quoted with the
suite version that produced it, so a fix never changes the meaning of an
old result; it tells you whether to run the suite again.
