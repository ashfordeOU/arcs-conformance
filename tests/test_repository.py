#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The repository's terms, identity and hygiene, held to what they claim.

A licence file that is not the official text is not the licence it names.
A version stated in four files is four copies. A statement of whose terms
cover `spec/` is only true while it matches `spec/LICENSE`. And everything
in this repository is public, so nothing in it may carry a path from
somebody's machine or point at a repository that is not public. Each of
those is checked here against the tree, not remembered.

Run: python3 tests/test_repository.py
"""

import ast
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import sysconfig
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import VERSION  # noqa: E402

# SHA-256 of https://www.apache.org/licenses/LICENSE-2.0.txt.
APACHE_2_0 = ("cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc5"
              "23d30")
# SHA-256 of the Contributor Covenant 2.1 as published, without the front
# matter of its source file, with its reporting placeholder in place.
COVENANT_2_1 = ("369bf7301883368fc19203bd0f1233fed2b83f0378ad19c4d0708bf6192"
                "5339b")
COVENANT_PLACEHOLDER = "[INSERT CONTACT METHOD]"
CONTACT = "contact@ashforde.org"

REGISTRY_CODE = "17321180"
ADDRESS = ("Ahtri tn 12, Kesklinna linnaosa, 15551 Tallinn, Harju maakond, "
           "Estonia")
REGISTER = "https://ariregister.rik.ee/eng/company/17321180/Ashforde-OU"
NO_MARKS = '"Aero Harness", "ARCS" or "Ashforde", or any mark'

# Everything in this repository is public, so two kinds of text are kept out
# of it, and they are checked in two different ways.
#
# The first kind is text this file can safely name: an absolute path from
# somebody's own computer, an internal work-order number, a claim to a mark,
# and a sentence claiming certification, approval or qualification.
# The last two are claims this repository must not make: it may say only
# that nothing grants a right to the names, and that a result is evidence.
# Each pattern below is written so that it does not match its own source, so
# that this file is scanned like every other and can catch its own leak.
#
# The second kind is a short list of words that must not appear in public
# and that this file therefore must not print either: the names of the
# maintainer's own working directories and tools, the name of a repository
# that is not public, a word the maintainer does not use about its own
# material, and the names by which a tool might be credited as an author.
# Writing them here would publish the very thing the check exists to keep
# out, so each is held as the SHA-256 digest of the lower-cased word, or
# pair of adjacent words. A digest hides the list from a reader passing
# through and from a search engine; it is not a secret, and the maintainer
# regenerates it with sha256() over the words it keeps.
FORBIDDEN = (
    (r"/[U]sers/|/home/[a-z]|/var/[f]olders|/private/(?:tm[p]|va[r])\b",
     "an absolute path from somebody's own computer"),
    (r"\bAH-[0-9]+\b", "a work-order number"),
    (r"\btrade ?marks? of\b|\u2122|\u00ae|\bcertification[ ]mark\b"
     r"|\bregistered (?:trade ?)?marks?\b",
     "a claim to a mark"),
    (r"\b(?:is|are|was|were|been|be) (?:certified|approved|qualified)\b",
     "a claim of certification"),
)

# SHA-256 of each word, or pair of adjacent words, described above.
WITHHELD = frozenset((
    "24626cb1dc15eb7572c6a321d5663592c60f7926c9386e8a464e75178e4e9215",
    "4546c80cfc69b62c728f769cb2899736587fa11e633de2037956f8fe448e38c3",
    "5417dcf3515cce99d317b6d1e22915f647f195e0f1cd9578534cf18a6d353895",
    "7813670ff886c2f9397c151cf25b097663b3b1edda5c403ebf162982972b2c8e",
    "8cfde6efdfc4ed5ab1f6acbbd1ba49bf31932f84d0a4c090eb41c7d151e8b180",
    "8e454131633bac114e1bad6d72f3857ae68df51351928c1594933830aa08a9a6",
    "c1a89c1ffc591782dc5fa2bf851a838de7b75f45ea3d02b9e58a11abf72a4172",
    "c5f9d8f01eaaecc599699fbc9ada0dd9c4da6a59258bc55d6e464373afc049d5",
    "c70eca6b0f88f44d81a41311647e50fda1ac454ec04ffd442b0eb4743a993131",
    "c857d09db23e6822e3600bc06ad8d58f92ed62bc8efd81c753f77048662cb97d",
    "f85305749c95859ba8cd52a8a433ea327207e65b68156f807124c56239275b69",
    "fafff6df80ac162a1fcd273d2b841e8de2a9af1fd3e2e5092380a0b389e3d68b",
))

# A word, or a name written with dots, hyphens or underscores inside it.
WORD = re.compile(r"[a-z0-9]+(?:[-._][a-z0-9]+)*")
SKIP_DIRS = {".git", "__pycache__", "spec"}
TEXT = (".py", ".md", ".yml", ".yaml", ".json", ".cff", ".svg", ".txt",
        "")


def read(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def flat(text):
    return " ".join(text.split())


def public_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS
                         and not d.endswith(".egg-info"))
        for name in sorted(files):
            if os.path.splitext(name)[1] in TEXT:
                path = os.path.join(base, name)
                yield os.path.relpath(path, ROOT).replace(os.sep, "/")


def digest(term):
    return hashlib.sha256(term.encode("utf-8")).hexdigest()


def withheld_in(text, digests=WITHHELD):
    """The lines carrying a word, or a pair of adjacent words, whose digest
    is listed: [(line number, the first eight characters of the digest)].

    The finding names the line and the digest rather than the word, so that
    a failure printed in a log does not publish what the check keeps out.
    A pair is looked for within one line only."""
    found = []
    for number, line in enumerate(text.lower().split("\n"), 1):
        words = WORD.findall(line)
        for term in words + [" ".join(p) for p in zip(words, words[1:])]:
            seen = digest(term)
            if seen in digests:
                found.append((number, seen[:8]))
    return sorted(set(found))


def citation():
    """The top-level scalar fields of CITATION.cff, without a YAML parser."""
    fields = {}
    for key, value in re.findall(r"^([a-z-]+): *(.+?) *$",
                                 read("CITATION.cff"), re.M):
        fields[key] = value.strip('"')
    return fields


def changelog_release():
    match = re.search(r"^## \[([0-9.]+)\] — ([0-9-]+)$", read("CHANGELOG.md"),
                      re.M)
    return match.group(1), match.group(2)


class TheTerms(unittest.TestCase):
    def test_the_licence_is_the_official_apache_2_0_text(self):
        with open(os.path.join(ROOT, "LICENSE"), "rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(),
                             APACHE_2_0)

    def test_the_code_of_conduct_is_the_covenant_with_only_the_contact(self):
        text = read("CODE_OF_CONDUCT.md")
        self.assertEqual(text.count(CONTACT), 1)
        restored = text.replace(CONTACT, COVENANT_PLACEHOLDER)
        self.assertEqual(hashlib.sha256(restored.encode("utf-8"))
                         .hexdigest(), COVENANT_2_1)

    def test_the_terms_of_spec_are_quoted_exactly(self):
        spec_licence = read("spec/LICENSE")
        terms = flat(spec_licence.split("word for word:")[1]
                     .split("This file is generated")[0])
        section = read("spec/ARCS-1.md").split("### Terms")[1]
        self.assertEqual(flat(section.split("\n---")[0]), terms)
        quoted = re.findall(r"^> ?(.*)$", read("LICENSING.md"), re.M)
        self.assertEqual(flat(" ".join(quoted)), terms)

    def test_no_file_grants_a_name_or_a_mark(self):
        for name in ("README.md", "NOTICE", "LICENSING.md"):
            self.assertIn(NO_MARKS, flat(read(name)), name)

    def test_the_notice_names_what_the_repository_carries(self):
        notice = flat(read("NOTICE"))
        for needed in ("Apache License, Version 2.0",
                       "arcs_conformance/ed25519.py", "RFC 8032",
                       "The directory spec/ is not covered",
                       "Contributor Covenant, version 2.1"):
            self.assertIn(needed, notice)

    def test_the_vendored_header_is_the_length_the_notice_says(self):
        with io.open(os.path.join(ROOT, "arcs_conformance", "ed25519.py"),
                     encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        header = lines.index("#!/usr/bin/env python3")
        self.assertIn("below its own eleven-line header", flat(read("NOTICE")))
        self.assertEqual(header, 11)

    def test_every_python_file_says_its_licence(self):
        for path in public_files():
            if path.endswith(".py"):
                head = read(path)[:400]
                self.assertIn("SPDX-License-Identifier: Apache-2.0", head,
                              path)


class TheIdentity(unittest.TestCase):
    def test_the_company_is_stated_the_same_everywhere(self):
        for name in ("README.md", "NOTICE", "LICENSING.md"):
            text = flat(read(name))
            self.assertIn(REGISTRY_CODE, text, name)
            self.assertIn(ADDRESS, text, name)
            self.assertIn(CONTACT, text, name)
        self.assertIn(REGISTER, read("README.md"))
        for name in ("README.md", "NOTICE", "LICENSING.md", "CITATION.cff",
                     "codemeta.json", "SECURITY.md", "GOVERNANCE.md",
                     "CONTRIBUTING.md", "docs/GLOSSARY.md"):
            self.assertIn("Ashforde OÜ, a private limited company (osaühing",
                          flat(read(name)), name)
        fields = read("CITATION.cff")
        for needed in ('name: "Ashforde OÜ"', 'post-code: "15551"',
                       'city: "Tallinn"', 'country: "EE"',
                       'email: "%s"' % CONTACT):
            self.assertIn(needed, fields)
        meta = json.loads(read("codemeta.json"))
        address = meta["author"][0]["address"]
        self.assertEqual(meta["author"][0]["name"], "Ashforde OÜ")
        self.assertEqual(address["postalCode"], "15551")
        self.assertEqual(address["addressCountry"], "EE")

    def test_the_citation_names_the_edition_the_suite_grades_against(self):
        from arcs_conformance import spec as specs
        edition = specs.load().edition
        self.assertIn('version: "edition %s"' % edition, read("CITATION.cff"))

    def test_one_version_and_one_date(self):
        fields = citation()
        meta = json.loads(read("codemeta.json"))
        version, date = changelog_release()
        self.assertEqual(version, VERSION)
        self.assertEqual(fields["version"], VERSION)
        self.assertEqual(meta["version"], VERSION)
        self.assertEqual(fields["date-released"], date)
        self.assertEqual(meta["datePublished"], date)
        self.assertEqual(fields["license"], "Apache-2.0")
        self.assertTrue(meta["license"].endswith("/Apache-2.0"))


class TheHygiene(unittest.TestCase):
    def test_this_file_is_scanned_like_every_other(self):
        me = os.path.relpath(os.path.abspath(__file__), ROOT)
        self.assertIn(me.replace(os.sep, "/"), list(public_files()))

    def test_nothing_public_carries_what_it_must_not(self):
        found = []
        for path in public_files():
            text = read(path)
            for pattern, why in FORBIDDEN:
                for match in re.finditer(pattern, text, re.I):
                    found.append("%s: %s (%s)" % (path, match.group(0), why))
        self.assertEqual(found, [])

    def test_nothing_public_carries_a_withheld_word(self):
        found = []
        for path in public_files():
            for number, seen in withheld_in(read(path)):
                found.append("%s line %d carries the word %s..."
                             % (path, number, seen))
        self.assertEqual(found, [])

    def test_the_withheld_check_finds_a_planted_word(self):
        planted = "zzq-planted-name"
        digests = frozenset([digest(planted), digest("two words")])
        self.assertEqual(withheld_in("a line naming %s here" % planted,
                                     digests), [(1, digest(planted)[:8])])
        self.assertEqual(withheld_in("with two words in it", digests),
                         [(1, digest("two words")[:8])])
        self.assertEqual(withheld_in("a line naming nothing", digests), [])
        self.assertEqual(withheld_in("zzq-planted-nameless", digests), [])

    def test_every_action_is_pinned_to_a_commit(self):
        workflows = os.path.join(ROOT, ".github", "workflows")
        for name in sorted(os.listdir(workflows)):
            text = read(".github/workflows/" + name)
            self.assertIn("permissions:\n  contents: read", text, name)
            for line in re.findall(r"uses:\s*(\S.*)$", text, re.M):
                self.assertRegex(line, r"^[\w.-]+/[\w.-]+@[0-9a-f]{40} "
                                       r"# v[0-9]", name)

    def test_the_suite_needs_only_the_standard_library(self):
        local = {"arcs_conformance", "adapter", "figures", "gen_assets",
                 "gen_readme", "broken_adapter"}
        local |= set(os.path.splitext(n)[0]
                     for n in os.listdir(os.path.join(ROOT, "tests")))
        stdlib = os.path.realpath(sysconfig.get_paths()["stdlib"])
        outside = []
        for path in public_files():
            if not path.endswith(".py"):
                continue
            tree = ast.parse(read(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    if top in local:
                        continue
                    if hasattr(sys, "stdlib_module_names") and \
                            top not in sys.stdlib_module_names:
                        outside.append("%s: %s" % (path, top))
                        continue
                    found = importlib.util.find_spec(top)
                    origin = found.origin if found else "missing"
                    if origin in (None, "built-in", "frozen"):
                        continue
                    real = os.path.realpath(origin)
                    if not real.startswith(stdlib) or \
                            "-packages" in real:
                        outside.append("%s: %s (%s)" % (path, top, origin))
        self.assertEqual(outside, [])


if __name__ == "__main__":
    unittest.main()
