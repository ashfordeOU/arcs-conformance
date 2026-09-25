#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Every public file spells out each abbreviation before it relies on it.

WHY THIS FILE EXISTS
--------------------
The people this suite most needs to reach have never heard of ARCS-1 or of
the company that publishes it. A page that says `ARCS-1`, `claim@1` or `C8`
before it says what they are has lost that reader on its first screen, and
an earlier version of this repository did exactly that. So every public
file is held to one rule: the first time an abbreviation, a standard number
or a code-name appears in a file, the words it stands for appear in the
same sentence (or the same table row), or earlier in that file.

HOW
---
Three rules, each read back from the tree rather than remembered.

1. docs/GLOSSARY.md carries a table of every abbreviation with what it
   stands for, for readers. REGISTRY below gives, for each, the pattern
   that finds a use and the words that spell it out. The two are held to
   each other: an abbreviation in the table that the registry lacks, or the
   reverse, fails, and the words the registry demands must appear in the
   table's own explanation.
2. A conformance criterion cited by its number alone says nothing. So at
   the first use of C1 to C15 on its own in a file, the title ARCS-1
   section 12 gives that criterion must stand in the same sentence, table
   row or image label, or earlier in the file. The titles are read from the
   copy of the specification, never typed here. A number used as the end of
   a range (C1 to C15) is a reference to the set and needs only the words
   the registry demands.
3. A short form the registry does not know would otherwise pass unseen, so
   any run of capitals, or a standard number such as X.509, that no rule
   here covers fails as well, unless it is in ALLOWED_CAPITALS with the
   reason it is there. Text set entirely in capitals is a label, not prose,
   and is read only under the first rule.

Official texts reproduced verbatim (the licence and the code of conduct),
the byte copy of the specification and the source code are exempt; every
other text file must be either scanned or listed as exempt, so a new
document cannot slip past. Code, inline or fenced, is read under the first
rule and not the other two: it is what a reader types, not prose.

Run: python3 tests/test_plain_language.py
"""

import html
import io
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ElementTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcs_conformance import spec as specs  # noqa: E402

# (the short form as the glossary table spells it, a pattern that finds a
# use, the words that spell it out). Matching of the words ignores case,
# emphasis and line breaks.
REGISTRY = (
    ("ARCS", r"\bARCS\b(?!-1\b)",
     "Agent Run Conformance Specification"),
    ("ARCS-1", r"\bARCS-1\b", "Agent Run Conformance Specification"),
    ("AHD, AHS", r"\bAH[DS]\b", "prefix"),
    ("Aero Agent Roles", r"\bAero Agent Roles\b",
     "library of aerospace engineering roles"),
    ("Aero Agent Skills", r"\bAero Agent Skills\b",
     "library of aerospace engineering skills"),
    ("Aero Harness", r"\bAero Harness\b", "inspection runtime"),
    ("AI", r"\bAI\b", "artificial intelligence"),
    ("Apache-2.0", r"\bApache-2\.0\b", "Apache License, Version 2.0"),
    ("API", r"\bAPIs?\b", "application programming interface"),
    ("ASCII", r"\bASCII\b",
     "American Standard Code for Information Interchange"),
    ("C1 to C15", r"\bC(?:1[0-5]|[1-9])\b", "conformance criteri"),
    ("CANON", r"\bCANON\b", "canonical serialisation"),
    ("CC BY 4.0", r"\bCC[ -]BY\b",
     "Creative Commons Attribution 4.0 International"),
    ("CFF", r"\bCFF\b", "Citation File Format"),
    ("CI", r"\bCI\b", "continuous integration"),
    ("claim@1", r"claim@1", "conformance claim format"),
    ("DCO", r"\bDCO\b", "Developer Certificate of Origin"),
    ("Dependabot", r"\bDependabot\b", "proposes updates"),
    ("Ed25519", r"\bEd25519\b", "Edwards-curve Digital Signature Algorithm"),
    ("EdDSA", r"\bEdDSA\b", "Edwards-curve Digital Signature Algorithm"),
    ("EE", r"\bEE\b", "Estonia"),
    ("FAQ", r"\bFAQs?\b", "frequently asked questions"),
    ("hex", r"\bhex\b", "hexadecimal"),
    ("ID", r"\bIDs?\b", "identifier"),
    ("NaN", r"\bNaN\b", "not a number"),
    ("OÜ", r"\bOÜ\b", "osaühing"),
    ("POSIX", r"\bPOSIX\b", "Portable Operating System Interface"),
    ("PR", r"\bPRs?\b", "pull request"),
    ("RFC", r"\bRFC\b", "Request for Comments"),
    ("RFC 2119", r"\bRFC 2119\b", "Requirement Levels"),
    ("RFC 3161", r"\bRFC 3161\b", "Time-Stamp Protocol"),
    ("RFC 3339", r"\bRFC 3339\b", "Date and Time on the Internet"),
    ("RFC 6962", r"\bRFC 6962\b", "Certificate Transparency"),
    ("RFC 8032", r"\bRFC 8032\b", "Edwards-Curve Digital Signature Algorithm"),
    ("RFC 8785", r"\bRFC 8785\b", "JSON Canonicalization Scheme"),
    ("SHA", r"\bSHA\b(?!-)", "Secure Hash Algorithm"),
    ("SHA-256", r"\bSHA-256\b", "Secure Hash Algorithm"),
    ("SHA256SUMS", r"\bSHA256SUMS\b", "checksum"),
    ("SPDX", r"\bSPDX\b", "Software Package Data Exchange"),
    ("stderr", r"\bstderr\b", "standard error"),
    ("stdin", r"\bstdin\b", "standard input"),
    ("stdlib", r"\bstdlib\b", "standard library"),
    ("stdout", r"\bstdout\b", "standard output"),
    ("SVG", r"\bSVG\b", "Scalable Vector Graphics"),
    ("TSA", r"\bTSA\b", "time-stamping authority"),
    ("URL", r"\bURLs?\b", "Uniform Resource Locator"),
    ("UTC", r"\bUTC\b", "Coordinated Universal Time"),
    ("UTF-8, UTF-16", r"\bUTF-(?:8|16)\b", "Unicode Transformation Format"),
    ("X.509", r"\bX\.509\b", "public-key certificates"),
    ("YAML", r"\bYAML\b", "YAML Ain't Markup Language"),
    ("JSON", r"\bJSON\b", "JavaScript Object Notation"),
)

# A run of capitals, or a standard number, that the rules above would
# otherwise take for an unexplained short form. Each is here for a reason.
ALLOWED_CAPITALS = {
    # The three results of a case, defined in the README's table and in the
    # glossary, and printed in capitals by the suite itself.
    "PASS", "FAIL", "ERROR",
    # Files of this repository, named as they are spelled on disk.
    "README.md", "PROTOCOL.md", "LICENSE", "LICENSING.md", "NOTICE",
    "SECURITY.md", "CONTRIBUTING.md", "GOVERNANCE.md", "CHANGELOG.md",
    "CITATION.cff", "GLOSSARY.md", "ARCS-1.md", "README",
    # A placeholder the command line prints for an argument, shown beside
    # the option in the README's table of options.
    "DIR",
}

GLOSSARY = "docs/GLOSSARY.md"

# Reproduced verbatim from their publishers, or a byte copy of a published
# text, and so not ours to reword; or source code, whose comments are for
# the people changing it.
EXEMPT_FILES = {"LICENSE", "CODE_OF_CONDUCT.md", ".gitignore", ".ci-native"}
EXEMPT_DIRS = {".git", "spec", "__pycache__"}
SCANNED_SUFFIXES = (".md", ".yml", ".yaml", ".cff", ".json", ".svg", "")

URL = re.compile(r"(?:https?|mailto):[^\s)>\"'`]+")


def read(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def ignored_names():
    """The plain file names .gitignore keeps out of the repository, such as
    the reports a run writes; they are never published."""
    names = set()
    for line in read(".gitignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not \
                re.search(r"[*/?\[]", line):
            names.add(line)
    return names


def public_files():
    """Every text file a reader of the repository can open, source code
    aside."""
    ignored = ignored_names()
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXEMPT_DIRS)
        for name in sorted(files):
            path = os.path.relpath(os.path.join(base, name), ROOT)
            path = path.replace(os.sep, "/")
            if path.endswith(".py") or name.endswith(".pyc") or \
                    name in ignored:
                continue
            yield path


def scanned(path):
    if path in EXEMPT_FILES:
        return False
    return os.path.splitext(path)[1] in SCANNED_SUFFIXES


def svg_text(text):
    """The title, then every run of visible text, one paragraph each."""
    root = ElementTree.fromstring(text.encode("utf-8"))
    ns = "{http://www.w3.org/2000/svg}"
    parts = [root.find(ns + "title").text or ""]
    for node in root.iter(ns + "text"):
        parts.append("".join(node.itertext()))
    return "\n\n".join(parts)


def markdown_text(text):
    """What a reader sees: comments gone, an image read as its alt text,
    other markup and every link target removed."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r'<img\b[^>]*?\balt="([^"]*)"[^>]*>', r"\n\n\1\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\]\([^)\s]*\)", "]", text)
    return html.unescape(URL.sub("", text))


def reader_text(path):
    text = read(path)
    if path.endswith(".svg"):
        return svg_text(text)
    if path.endswith(".md") or "." not in os.path.basename(path):
        return markdown_text(text)
    if path.endswith((".yml", ".yaml")):
        # A comment is read as prose: its markers go, so a sentence that
        # runs over several comment lines is one sentence.
        text = re.sub(r"(?m)^[ \t]*# ?", "", text)
    return URL.sub("", text)


STRUCTURED = re.compile(r"\n\s*(?:- |[\w@-]+:\s|\")")


def sentence_end(text, start, after, structured):
    """Where the sentence (or table row, or data field) holding a use ends."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    line_end = len(text) if line_end < 0 else line_end
    if text[line_start:line_end].lstrip().startswith("|"):
        return line_end
    ends = [text.find(mark, after) for mark in (". ", ".\n", "\n\n")]
    if structured:
        found = STRUCTURED.search(text, after)
        ends.append(found.start() if found else -1)
    ends = [e for e in ends if e >= 0]
    return min(ends) if ends else len(text)


def flat(text):
    return " ".join(re.sub(r"[*`_]", "", text).split()).lower()


def unexplained(path, text=None):
    """[(short form, the line of its first use)] that nothing spells out."""
    text = reader_text(path) if text is None else text
    structured = os.path.splitext(path)[1] in (".yml", ".yaml", ".cff",
                                               ".json")
    found = []
    for short, pattern, words in REGISTRY:
        match = re.search(pattern, text)
        if not match:
            continue
        end = sentence_end(text, match.start(), match.end(), structured)
        if flat(words) not in flat(text[:end]):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.start())
            found.append((short, text[line_start:line_end if line_end >= 0
                                      else None].strip()[:120]))
    return found


CODE_SPAN = re.compile(r"```.*?```|`[^`\n]*`", re.S)
CRITERION = re.compile(r"\bC(?:1[0-5]|[1-9])\b")
# C1 to C15, C1–C15, C5-C6: a reference to a run of criteria, not to one.
CRITERION_RANGE = re.compile(r"\bC(?:1[0-5]|[1-9])\s*(?:to|[-–—])\s*"
                             r"C(?:1[0-5]|[1-9])\b")
# JSON, ARCS-1, X.509: a short form set in capitals, or a standard number.
CAPITALS = re.compile(r"\b[A-Z][A-Z0-9]+(?:[-.][A-Za-z0-9]+)*\b"
                      r"|\b[A-Z]\.[0-9]+\b")


def spoken(path, text=None):
    """What a reader reads as prose: code, which is what they type instead,
    is left out."""
    return CODE_SPAN.sub(" ", reader_text(path) if text is None else text)


def line_at(text, start):
    end = text.find("\n", start)
    line = text[text.rfind("\n", 0, start) + 1:end if end >= 0 else None]
    return line.strip()[:120]


def paragraph_at(text, start):
    return text[text.rfind("\n\n", 0, start) + 1:
                (text.find("\n\n", start) + 1) or len(text)]


def unnamed_criteria(path, text=None, titles=None):
    """[(C-number, its line)] used on its own before its section 12 title."""
    titles = specs.load().criteria if titles is None else titles
    text = spoken(path) if text is None else text
    structured = os.path.splitext(path)[1] in (".yml", ".yaml", ".cff",
                                               ".json")
    ranges = [m.span() for m in CRITERION_RANGE.finditer(text)]
    found, seen = [], set()
    for match in CRITERION.finditer(text):
        code = match.group(0)
        if code in seen or any(a <= match.start() < b for a, b in ranges):
            continue
        seen.add(code)
        end = sentence_end(text, match.start(), match.end(), structured)
        if flat(titles[code]) not in flat(text[:end]):
            found.append((code, line_at(text, match.start())))
    return found


def unregistered(path, text=None):
    """[(short form, its line)] that no rule in this file knows about."""
    text = spoken(path) if text is None else text
    known = []
    for _, pattern, _ in REGISTRY:
        known += [m.span() for m in re.finditer(pattern, text)]
    known += [m.span() for m in CRITERION.finditer(text)]
    found, seen = [], set()
    for match in CAPITALS.finditer(text):
        token = match.group(0)
        if token in seen or token in ALLOWED_CAPITALS:
            continue
        if any(a < match.end() and match.start() < b for a, b in known):
            continue
        if not re.search(r"[a-z]", paragraph_at(text, match.start())):
            continue  # a label set in capitals, not a sentence
        seen.add(token)
        found.append((token, line_at(text, match.start())))
    return found


def glossary_table():
    """{short form: what it stands for} from the glossary's table."""
    section = read(GLOSSARY).split("\n## Abbreviations\n")[1]
    rows = re.findall(r"^\| (.+?) \| (.+?) \| (.*?) ?\|$", section, re.M)
    return dict((short, stands) for short, stands, _ in rows
                if short != "abbreviation" and not short.startswith("-"))


class TheRegistry(unittest.TestCase):
    def test_the_glossary_and_the_registry_name_the_same_abbreviations(self):
        table = glossary_table()
        registry = [short for short, _, _ in REGISTRY]
        self.assertEqual(len(registry), len(set(registry)))
        self.assertEqual(sorted(set(table) - set(registry)), [],
                         "in docs/GLOSSARY.md's table but not checked here")
        self.assertEqual(sorted(set(registry) - set(table)), [],
                         "checked here but missing from docs/GLOSSARY.md")

    def test_the_glossary_spells_out_what_the_registry_demands(self):
        table = glossary_table()
        wrong = [short for short, _, words in REGISTRY
                 if short in table and flat(words) not in flat(table[short])]
        self.assertEqual(wrong, [])

    def test_every_pattern_finds_its_own_short_form(self):
        for short, pattern, _ in REGISTRY:
            first = short.split(",")[0].split(" to ")[0]
            self.assertTrue(re.search(pattern, first), short)


class TheRule(unittest.TestCase):
    """The checker itself, on text small enough to read."""

    def test_a_short_form_before_its_words_fails(self):
        text = "ARCS-1 is short.\n\nIt is the Agent Run Conformance " \
               "Specification.\n"
        self.assertEqual([s for s, _ in unexplained("x.md", text)],
                         ["ARCS-1"])

    def test_the_words_in_the_same_sentence_pass(self):
        text = "The Agent Run Conformance Specification (ARCS-1).\n"
        self.assertEqual(unexplained("x.md", text), [])
        text = "ARCS-1, the Agent Run Conformance Specification.\n"
        self.assertEqual(unexplained("x.md", text), [])

    def test_the_next_sentence_is_too_late(self):
        text = "Read ARCS-1. It is the Agent Run Conformance " \
               "Specification.\n"
        self.assertEqual([s for s, _ in unexplained("x.md", text)],
                         ["ARCS-1"])

    def test_a_table_row_is_one_unit(self):
        text = "| ARCS-1 | Agent Run Conformance Specification |\n"
        self.assertEqual(unexplained("x.md", text), [])

    def test_a_link_target_is_not_a_use(self):
        text = "[the text](spec/ARCS-1.md) and https://x.org/CI/ARCS-1\n"
        self.assertEqual(unexplained("x.md", markdown_text(text)), [])

    def test_an_image_is_read_by_its_alt_text(self):
        text = '<img src="a.svg" alt="ARCS-1 and nothing more">\n'
        self.assertEqual([s for s, _ in unexplained("x.md",
                                                    markdown_text(text))],
                         ["ARCS-1"])

    def test_a_criterion_cited_by_its_number_alone_fails(self):
        titles = {"C9": "An empty anchor cannot produce a pass",
                  "C14": "A finding is never softened or dropped"}
        self.assertEqual([c for c, _ in unnamed_criteria(
            "x.md", "C14 forbids it. C9 too.\n", titles)], ["C14", "C9"])

    def test_a_criterion_named_in_words_passes(self):
        titles = {"C9": "An empty anchor cannot produce a pass"}
        for text in ("C9 (an empty anchor cannot produce a pass) holds.\n",
                     "| **C9** | An empty anchor cannot produce a pass |\n",
                     "An empty anchor cannot produce a pass.\n\nSo C9.\n"):
            self.assertEqual(unnamed_criteria("x.md", text, titles), [], text)

    def test_a_range_of_criteria_is_a_reference_to_the_set(self):
        titles = {"C1": "Canonical serialisation", "C15": "No clock"}
        self.assertEqual(unnamed_criteria("x.md", "It holds C1 to C15.\n",
                                          titles), [])
        self.assertEqual(unnamed_criteria("x.md", "It holds C1–C15.\n",
                                          titles), [])

    def test_an_unregistered_short_form_fails(self):
        found = [s for s, _ in unregistered("x.md",
                                            "The PKI and the HSM matter.\n")]
        self.assertEqual(found, ["PKI", "HSM"])
        self.assertEqual(unregistered("x.md", "The X.400 form.\n")[0][0],
                         "X.400")

    def test_a_registered_short_form_and_a_label_pass(self):
        text = "JSON (JavaScript Object Notation) and C8.\n"
        self.assertEqual(unregistered("x.md", text), [])
        self.assertEqual(unregistered("x.md", "HOW A RUN WORKS\n"), [])

    def test_code_is_not_prose(self):
        text = "Run `python3 -m x --only C8` or ```\nPKI\n```\n"
        self.assertEqual(unregistered("x.md", spoken("x.md", text)), [])
        self.assertEqual(unnamed_criteria("x.md", spoken("x.md", text),
                                          {"C8": "Whatever"}), [])


class ThePublicFiles(unittest.TestCase):
    def test_every_text_file_is_scanned_or_deliberately_exempt(self):
        stray = [p for p in public_files()
                 if not scanned(p) and p not in EXEMPT_FILES]
        self.assertEqual(stray, [])

    def test_no_public_file_uses_an_abbreviation_before_spelling_it_out(self):
        found = []
        for path in public_files():
            if scanned(path):
                for short, line in unexplained(path):
                    found.append("%s: %s first used unexplained in: %s"
                                 % (path, short, line))
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_no_public_file_cites_a_criterion_by_its_number_alone(self):
        titles = specs.load().criteria
        found = []
        for path in public_files():
            if scanned(path):
                for code, line in unnamed_criteria(path, titles=titles):
                    found.append("%s: %s first used without the words of "
                                 "ARCS-1 section 12 (%r) in: %s"
                                 % (path, code, titles[code], line))
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_no_public_file_uses_a_short_form_no_rule_here_knows(self):
        found = []
        for path in public_files():
            if scanned(path):
                for token, line in unregistered(path):
                    found.append("%s: %s is in neither the glossary's table "
                                 "nor ALLOWED_CAPITALS, first used in: %s"
                                 % (path, token, line))
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_the_first_screen_says_why_a_stranger_should_care(self):
        """The tagline, which is the first prose on the page, says what this
        is, who publishes it and what goes wrong without it. The reason
        cannot be left to a paragraph a screen further down."""
        text = read("README.md")
        tagline = flat(markdown_text(
            text.split("<!-- /gen:title -->")[1]
                .split("<!-- gen:statline -->")[0]))
        for needed in ("test suite", "ashforde oü"):
            self.assertIn(needed, tagline)
        self.assertTrue(any(word in tagline for word in
                            ("forgery", "forged", "accepts a forgery")),
                        "the tagline does not say what goes wrong without "
                        "a verifier that checks: %r" % tagline)

    def test_the_readme_opens_by_saying_what_this_is_and_who_publishes_it(
            self):
        text = markdown_text(read("README.md"))
        opening = flat(text.split("\n## ")[0])
        for needed in ("what this repository is", "who publishes it",
                       "why it matters", "ashforde oü, a private limited "
                       "company (osaühing"):
            self.assertIn(needed, opening)


if __name__ == "__main__":
    sys.exit(unittest.main())
