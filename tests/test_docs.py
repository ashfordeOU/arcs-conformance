#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The README and PROTOCOL.md, held to the catalogue they describe.

A figure in prose is a copy, and a copy drifts. The README's generated
blocks are held to their generator by tests/test_generated.py; this file
reads the README a second way, independently of that generator, and also
reads back every figure the hand-written prose states, every table
PROTOCOL.md gives an adapter author, and every link the README makes, and
compares each with the catalogue, the runner, the command line and the
tree. The day a case is added without its sentence, a test says so.

Run: python3 tests/test_docs.py
"""

import io
import os
import posixpath
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from arcs_conformance import (  # noqa: E402
    __main__ as cli, cases as catalogue, report, runner, spec as specs)
import broken_adapter  # noqa: E402
import test_broken  # noqa: E402

WORDS = {"two": 2, "three": 3, "four": 4, "six": 6, "seven": 7, "nine": 9,
         "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "twenty-one": 21,
         "twenty-four": 24}
# The documents a reader moves between, whose links must all resolve.
LINKED = ("README.md", "PROTOCOL.md", "LICENSING.md", "CONTRIBUTING.md",
          "GOVERNANCE.md", "SECURITY.md", "CHANGELOG.md", "docs/GLOSSARY.md",
          ".github/PULL_REQUEST_TEMPLATE.md")
GENERATED = re.compile(r"<!-- gen:([a-z-]+) -->\n.*?<!-- /gen:\1 -->", re.S)
FENCED = re.compile(r"^```.*?^```", re.S | re.M)


def read(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def number(word):
    return int(word) if word.isdigit() else WORDS[word]


def prose(text):
    """The hand-written part of a Markdown file: no generated blocks, no
    fenced code."""
    return FENCED.sub("", GENERATED.sub("", text))


def slug(heading):
    """The anchor GitHub gives a heading."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower(), flags=re.U)
    return text.replace(" ", "-")


def anchors(text):
    return set(slug(h) for h in re.findall(r"^#{1,6} (.+?)\s*$", text, re.M))


def ci_pythons():
    with io.open(os.path.join(ROOT, ".github", "workflows", "ci.yml"),
                 encoding="utf-8") as fh:
        text = fh.read()
    found = set()
    for value in re.findall(r"^\s*-?\s*python:\s*(.+?)\s*$", text, re.M):
        found.update(re.findall(r"[0-9]+\.[0-9]+", value))
    return sorted(found, key=lambda v: tuple(int(p) for p in v.split(".")))


def criteria_in(text):
    """'C1-C11, C13, C15' -> {'C1', ..., 'C11', 'C13', 'C15'}."""
    found = set()
    for a, b in re.findall(r"C([0-9]+)(?:-C([0-9]+))?", text):
        found.update("C%d" % n for n in range(int(a), int(b or a) + 1))
    return found


class TheReadme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = catalogue.catalogue(cls.spec)
        cls.readme = read("README.md")

    def test_the_totals(self):
        match = re.search(
            r"([0-9]+) cases in ([a-z-]+) operations: ([0-9]+) normative "
            r"cases across all ([a-z-]+)\s+criteria of ARCS-1 §12, and "
            r"([0-9]+) readings", self.readme)
        self.assertTrue(match, "the README's totals sentence has changed")
        total, ops, normative, criteria, readings = match.groups()
        self.assertEqual(int(total), len(self.cases))
        self.assertEqual(number(ops), len(catalogue.OPERATIONS))
        self.assertEqual(int(normative),
                         sum(1 for c in self.cases if c.normative))
        self.assertEqual(number(criteria), len(self.spec.criteria))
        self.assertEqual(int(readings),
                         sum(1 for c in self.cases if not c.normative))

    def test_the_coverage_table(self):
        rows = re.findall(r"^\| \*\*(C[0-9]+)\*\* \| (.+?) \| (.+?) \| "
                          r"([0-9]+) \| ([0-9]+) \| ([0-9]+) \| ([0-9]+) \| "
                          r"([0-9]+) \|$", self.readme, re.M)
        self.assertEqual([r[0] for r in rows],
                         sorted(self.spec.criteria, key=lambda c: int(c[1:])))
        for (cid, title, summary, own, derived, controls, normative,
             readings) in rows:
            mine = [c for c in self.cases if c.criterion == cid]
            self.assertEqual(title, self.spec.criteria[cid])
            self.assertEqual(summary, catalogue.SUMMARY[cid])
            self.assertEqual(int(own),
                             sum(1 for c in mine if c.basis == "criterion"),
                             cid)
            self.assertEqual(int(derived),
                             sum(1 for c in mine if c.basis == "must"), cid)
            self.assertEqual(int(controls),
                             sum(1 for c in mine if "-control-" in c.id),
                             cid)
            self.assertEqual(int(normative),
                             sum(1 for c in mine if c.normative), cid)
            self.assertEqual(int(readings),
                             sum(1 for c in mine if not c.normative), cid)

    def test_one_plain_sentence_for_each_criterion(self):
        self.assertEqual(set(catalogue.SUMMARY), set(self.spec.criteria))
        for cid, sentence in catalogue.SUMMARY.items():
            self.assertTrue(sentence.endswith("."), cid)
            self.assertNotIn(". ", sentence, cid)
            self.assertNotIn("|", sentence, cid)

    def test_the_edition_named_is_the_copys(self):
        for name in ("README.md", "PROTOCOL.md"):
            named = set(re.findall(r"edition ([0-9]{4}-[0-9]{2}-[0-9]{2})",
                                   read(name)))
            self.assertEqual(named, {self.spec.edition}, name)

    def test_the_defects_and_the_open_questions(self):
        defects = re.search(r"carries\s+([a-z-]+)\s+named\s+defects",
                            self.readme)
        self.assertEqual(number(defects.group(1)),
                         len(broken_adapter.DEFECTS))
        pinned = re.search(r"and\s+([a-z-]+)\s+of\s+them\s+are\s+pinned",
                           self.readme)
        self.assertEqual(number(pinned.group(1)), len(test_broken.EXPECTED))
        by_property = [d for d in test_broken.BY_PROPERTY
                       if "`%s`" % d not in self.readme]
        self.assertEqual(by_property, [])
        groups = re.search(r"in\s+([a-z-]+)\s+combined\s+groups", self.readme)
        self.assertEqual(number(groups.group(1)), len(test_broken.GROUPS))
        alone = re.search(r"([a-z-]+)\s+run\s+only\s+alone\s+\(([^)]*)\)",
                          self.readme)
        expected = set(broken_adapter.DEFECTS) - set(test_broken.COMBINED)
        self.assertEqual(number(alone.group(1)), len(expected))
        self.assertEqual(set(re.findall(r"`([a-z-]+)`", alone.group(2))),
                         expected)
        places = re.search(r"found\s+([a-z-]+)\s+places", self.readme)
        section = read("PROTOCOL.md").split("## 5.")[1]
        items = re.findall(r"^([0-9]+)\. \*\*", section, re.M)
        self.assertEqual(items, [str(n) for n in range(1, len(items) + 1)])
        self.assertEqual(number(places.group(1)), len(items))

    def test_the_vectors_named(self):
        stated = re.search(r"the\s+([a-z-]+)\s+vectors\s+of\s+ARCS-1\s+§13",
                           prose(self.readme))
        self.assertEqual(number(stated.group(1)), len(specs.VECTORS))

    def test_the_python_named(self):
        pythons = ci_pythons()
        text = " ".join(prose(self.readme).split())
        self.assertIn("Python %s or later" % pythons[0], text)
        named = set(re.findall(r"\b3\.[0-9]+\b", text))
        self.assertTrue(named <= set(pythons), named - set(pythons))

    def test_the_exit_statuses(self):
        rows = dict(re.findall(r"^\| ([0-9]) \| (.+?) \|$", self.readme,
                               re.M))
        self.assertEqual(sorted(rows), ["0", "1", "2", "3"])
        self.assertIn("passed", rows["0"])
        self.assertIn("failed", rows["1"])
        self.assertIn("could not be graded", rows["2"])
        self.assertIn("could not run", rows[str(cli.SUITE_ERROR)])
        case = self.cases[0]
        for result, status in ((runner.PASS, 0), (runner.FAIL, 1),
                               (runner.ERROR, 2)):
            outcome = runner.Outcome(case, result, "")
            self.assertEqual(report.exit_status([outcome]), status)
        self.assertIn("**Exit status %d** means the adapter does not "
                      "implement" % runner.UNSUPPORTED, self.readme)
        self.assertIn("exit with status %d for the operations it does not"
                      % runner.UNSUPPORTED, " ".join(self.readme.split()))

    def test_every_link_resolves(self):
        text = prose(self.readme)
        own = anchors(self.readme)
        links = re.findall(r"\]\(([^)\s]+)\)", text)
        links += re.findall(r'href="([^"]+)"', self.readme)
        broken = []
        for link in links:
            if re.match(r"[a-z]+:", link):
                continue
            path, _, anchor = link.partition("#")
            if not path:
                if anchor not in own:
                    broken.append(link)
                continue
            full = os.path.join(ROOT, *path.split("/"))
            if not os.path.exists(full):
                broken.append(link)
            elif anchor and anchor not in anchors(read(path)):
                broken.append(link)
        for form in re.findall(r"issues/new\?template=([a-z-]+\.yml)",
                               self.readme):
            if not os.path.exists(os.path.join(
                    ROOT, ".github", "ISSUE_TEMPLATE", form)):
                broken.append(form)
        self.assertEqual(broken, [])


    def test_the_results_and_the_bases(self):
        text = " ".join(prose(self.readme).split())
        results = re.search(r"\*\*Every case\*\* is one of ([a-z]+) "
                            r"results", text)
        named = {runner.PASS, runner.FAIL, runner.ERROR}
        self.assertEqual(number(results.group(1)), len(named))
        rows = re.findall(r"^\| ([A-Z]+) \| ", self.readme, re.M)
        self.assertEqual(set(r for r in rows if r in named), named)
        bases = re.search(r"\*\*([A-Z][a-z]+) bases, kept apart\.\*\*",
                          text)
        self.assertEqual(number(bases.group(1).lower()),
                         len(set(c.basis for c in self.cases)))
        for basis in set(c.basis for c in self.cases):
            self.assertIn("`%s`" % basis, text)

    def test_the_local_checks_named_in_the_layout(self):
        stated = re.search(r"^\| `\.ci-native` \| the ([a-z]+) commands",
                           self.readme, re.M)
        commands = [line for line in read(".ci-native").splitlines()
                    if line.strip()]
        self.assertEqual(number(stated.group(1)), len(commands))

    def test_every_count_of_criteria_the_prose_states(self):
        for name in ("README.md", "CHANGELOG.md", "docs/GLOSSARY.md"):
            stated = re.findall(r"\b([a-z-]+|[0-9]+)\s+conformance\s+"
                                r"criteria\b", prose(read(name)))
            counts = [number(s) for s in stated if s in WORDS or
                      s.isdigit()]
            self.assertTrue(counts or name == "CHANGELOG.md", name)
            for count in counts:
                self.assertEqual(count, len(self.spec.criteria), name)

    def test_the_continuous_integration_table_is_the_workflow(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "ci.yml"),
                     encoding="utf-8") as fh:
            workflow = fh.read()
        checks = []
        for step in re.split(r"^\s*- name: ", workflow, flags=re.M)[1:]:
            if re.search(r"^\s*run:", step, re.M):
                checks.append(step.split("\n", 1)[0].strip())
        section = self.readme.split("**What continuous integration "
                                    "checks.**")[1].split("\n## ")[0]
        rows = re.findall(r"^\| (.+?) \| (.+?) \|$", section, re.M)
        named = [step for step, _ in rows
                 if step not in ("step",) and not step.startswith("-")]
        self.assertEqual(named, checks)


class TheGlossary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.glossary = read("docs/GLOSSARY.md")

    def entry(self, term):
        match = re.search(r"^\*\*%s\.\*\* (.+?)(?:\n\n|\Z)"
                          % re.escape(term), self.glossary, re.M | re.S)
        self.assertTrue(match, term)
        return " ".join(match.group(1).split())

    def test_the_conclusions_are_the_specifications(self):
        text = self.entry("Conclusion")
        stated = re.search(r"One of the ([a-z]+) answers", text)
        self.assertEqual(number(stated.group(1)), len(self.spec.conclusions))
        self.assertEqual(tuple(re.findall(r"`([a-z_]+)`", text)[:-1]),
                         self.spec.conclusions)

    def test_the_criteria_are_the_specifications(self):
        text = self.entry("Conformance criterion")
        stated = re.findall(r"\b(?:the|all) ([a-z]+) (?:tests|hold)", text)
        self.assertTrue(stated)
        for word in stated:
            self.assertEqual(number(word), len(self.spec.criteria))
        first, last = re.search(r"numbered (C[0-9]+) to (C[0-9]+)",
                                text).groups()
        ordered = sorted(self.spec.criteria, key=lambda c: int(c[1:]))
        self.assertEqual((first, last), (ordered[0], ordered[-1]))

    def test_every_entry_is_a_term_and_a_sentence(self):
        entries = re.findall(r"^\*\*(.+?)\*\* ", self.glossary, re.M)
        self.assertTrue(entries)
        for term in entries:
            self.assertTrue(term.endswith("."), term)
            self.assertTrue(self.entry(term[:-1]).endswith("."), term)
        terms = [t.lower() for t in entries]
        self.assertEqual(len(terms), len(set(terms)))

    def test_every_term_the_readme_italicises_first_is_defined(self):
        opening = read("README.md").split("\n## Contents")[0]
        defined = set(t.lower().rstrip(".") for t in
                      re.findall(r"^\*\*(.+?)\*\* ", self.glossary, re.M))
        marked = re.findall(r"such as \*([a-z ]+)\*, \*([a-z ]+)\* and "
                            r"\*([a-z ]+)\*", " ".join(opening.split()))
        self.assertTrue(marked)
        for term in marked[0]:
            self.assertIn(term, defined)


class TheChangelog(unittest.TestCase):
    """The newest entry describes its release. While nothing is recorded
    under [Unreleased], the tree is that release, so its figures must be the
    tree's; once a change is recorded there, the entry is history and is
    left as it was."""

    def test_the_newest_release_while_nothing_is_unreleased(self):
        text = read("CHANGELOG.md")
        unreleased = text.split("## [Unreleased]")[1].split("\n## [")[0]
        if unreleased.strip() != "Nothing yet.":
            self.skipTest("changes are recorded under [Unreleased]")
        entry = " ".join(text.split("\n## [")[2].split("\n## [")[0].split())
        spec = specs.load()
        cases = catalogue.catalogue(spec)
        match = re.search(r"([0-9]+) cases in ([a-z]+) operations: ([0-9]+) "
                          r"normative cases across the ([a-z]+) conformance "
                          r"criteria \(C1 to C([0-9]+)\) of ARCS-1 section "
                          r"12, and ([0-9]+) readings", entry)
        self.assertTrue(match, "the release entry's totals have changed")
        total, ops, normative, criteria, last, readings = match.groups()
        self.assertEqual(int(total), len(cases))
        self.assertEqual(number(ops), len(catalogue.OPERATIONS))
        self.assertEqual(int(normative), sum(1 for c in cases if c.normative))
        self.assertEqual(number(criteria), len(spec.criteria))
        self.assertEqual(int(last), len(spec.criteria))
        self.assertEqual(int(readings),
                         sum(1 for c in cases if not c.normative))
        defects = re.search(r"with ([a-z-]+) named defects", entry)
        self.assertEqual(number(defects.group(1)), len(broken_adapter.DEFECTS))
        places = re.search(r"lists ([a-z-]+) places", entry)
        section = read("PROTOCOL.md").split("## 5.")[1]
        self.assertEqual(number(places.group(1)),
                         len(re.findall(r"^[0-9]+\. \*\*", section, re.M)))
        self.assertIn("edition %s" % spec.edition, entry)


class TheLinks(unittest.TestCase):
    def test_every_relative_link_in_every_document_resolves(self):
        broken = []
        for name in LINKED:
            text = read(name)
            base = os.path.dirname(name)
            for link in re.findall(r"\]\(([^)\s]+)\)", prose(text)):
                if re.match(r"[a-z]+:", link):
                    continue
                path, _, anchor = link.partition("#")
                target = posixpath.normpath(posixpath.join(base, path)) \
                    if path else name
                full = os.path.join(ROOT, *target.split("/"))
                if not os.path.exists(full):
                    broken.append("%s: %s" % (name, link))
                elif anchor and target.endswith(".md") and \
                        anchor not in anchors(read(target)):
                    broken.append("%s: %s" % (name, link))
        self.assertEqual(broken, [])


class TheProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = specs.load()
        cls.cases = catalogue.catalogue(cls.spec)
        cls.protocol = read("PROTOCOL.md")

    def test_its_name(self):
        self.assertIn("# The adapter protocol, `%s`" % runner.PROTOCOL,
                      self.protocol)

    def test_the_operations_table(self):
        rows = re.findall(r"^\| `([a-z_]+)` \| (.+?) \| (.+?) \| (.+?) \| "
                          r"(.+?) \|$", self.protocol, re.M)
        self.assertEqual(sorted(r[0] for r in rows),
                         sorted(catalogue.OPERATIONS))
        for op, fields, _, _, served in rows:
            mine = [c for c in self.cases if c.op == op]
            sent = set()
            for case in mine:
                sent.update(case.request)
            self.assertEqual(set(re.findall(r"`([a-z_]+)`", fields)), sent,
                             op)
            self.assertEqual(criteria_in(served),
                             set(c.criterion for c in mine), op)

    def test_the_vocabulary(self):
        block = re.search(r"one\nof the nine §11 names, or `refused`:\n\n"
                          r"((?: {4}.*\n)+)", self.protocol)
        self.assertEqual(tuple(block.group(1).split()),
                         self.spec.conclusions + (catalogue.REFUSED,))

    def test_the_default_timeout(self):
        stated = re.search(r"\| time \| ([0-9]+) seconds per call",
                           self.protocol)
        default = cli._parser().parse_args([]).timeout
        self.assertEqual(float(stated.group(1)), default)

    def test_the_grace_period(self):
        stated = re.search(r"abandoned after ([0-9]+) seconds",
                           self.protocol)
        self.assertEqual(float(stated.group(1)), runner._GRACE)

    def test_the_exit_statuses(self):
        self.assertIn("| exit status %d |" % runner.UNSUPPORTED,
                      self.protocol)

    def test_every_reading_is_named_among_the_open_questions(self):
        section = self.protocol.split("## 5.")[1]
        missing = [c.id for c in self.cases
                   if not c.normative and "`%s`" % c.id not in section]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
