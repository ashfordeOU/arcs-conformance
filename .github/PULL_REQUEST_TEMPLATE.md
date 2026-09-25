## What and why

<!-- What the change does, and the reason for it. Link the issue it closes. -->

## Checklist

- [ ] `python3 -m unittest discover -s tests` passes, on Python 3.9 as well as a current version if you can
- [ ] `python3 -m arcs_conformance --impl 'python3 reference/adapter.py'` still holds every criterion
- [ ] Generated files are regenerated, not edited: `python3 tools/gen_readme.py` and `python3 tools/gen_assets.py`
- [ ] Nothing under `spec/` is changed (a new edition is copied in whole, with its checksum file `SHA256SUMS`)
- [ ] A new or changed case cites its clause, states its basis, and comes with a negative and, where the criterion needs one, a control; its answer set is pinned in `tests/test_expectations.py`
- [ ] Any figure added to hand-written prose is checked in `tests/test_docs.py`
- [ ] Every abbreviation, standard number and code-name is spelled out at its first use in each file, and any new term of art is defined in `docs/GLOSSARY.md`
- [ ] `CHANGELOG.md` has a line under `[Unreleased]` for any change a user of the suite would notice
- [ ] Every commit in this pull request is signed off (`git commit -s`) under the Developer Certificate of Origin
