#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Rewrite the generated blocks of README.md from the tree.

    python3 tools/gen_readme.py           rewrite them in place
    python3 tools/gen_readme.py --check   exit 1 if any block is stale

WHAT IS GENERATED, AND WHAT IS NOT
----------------------------------
A block runs from `<!-- gen:NAME -->` to `<!-- /gen:NAME -->`. Everything
between the two lines is written here, from tools/figures.py: the mark, the
title and the statline with their alt text, the badges, the run excerpt (a
real run of the reference adapter), the option, operation, coverage and
version tables, and the citation. PROTOCOL.md carries one such block too,
the table naming the fifteen criteria, so that a reader who meets C12 there
is not sent to another file for its words. The glossary table is written
from docs/GLOSSARY.md, and the citation's title from CITATION.cff, so that
each is stated once. The prose outside the blocks is written by hand and
holds as few figures as it can; tests/test_docs.py reads back the ones it
does hold and compares each with the tree.

A block the README carries and this file does not know, or the reverse, is
an error rather than something to skip: a block nobody writes is a figure
nobody checks.
"""

import argparse
import html
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figures  # noqa: E402
import gen_assets  # noqa: E402

README = os.path.join(figures.ROOT, "README.md")
PROTOCOL = os.path.join(figures.ROOT, "PROTOCOL.md")
GLOSSARY = os.path.join(figures.ROOT, "docs", "GLOSSARY.md")
CITATION = os.path.join(figures.ROOT, "CITATION.cff")
BLOCK = re.compile(r"(<!-- gen:([a-z-]+) -->\n)(.*?)(<!-- /gen:\2 -->)",
                   re.S)

# The palette the other Ashforde OÜ repositories use for their badges.
LABEL = "1a1e35"
CYAN, VIOLET, MAGENTA, ORANGE, GREEN = ("0ea5e9", "8b5cf6", "ec4899",
                                        "f97316", "2ea043")

# What each operation asks, in a few words. Editorial, as a chart caption is:
# the fields, the sections and every count come from PROTOCOL.md and the
# catalogue.
ASKS = {
    "canonicalise": "serialise a JSON value as §3 defines",
    "derive_id": "derive the identifier a document's payload gives",
    "verify_record": "verify a record against an anchor, at an instant, "
                     "with or without a status list",
    "reliance": "say whether a conclusion permits reliance",
    "matches": "say whether a record covers a set of corpora",
    "check_successor": "say whether one status list may follow another",
    "build_record": "build a record from its fields",
}


def _shield(label, message, colour):
    def part(text):
        return (text.replace("-", "--").replace("_", "__")
                .replace(" ", "_").replace("+", "%2B").replace("/", "%2F")
                .replace("–", "%E2%80%93"))
    return ("https://img.shields.io/badge/%s-%s-%s?style=flat&labelColor=%s"
            % (part(label), part(message), colour, LABEL))


def _badge(href, label, message, colour, alt=None):
    return ('  <a href="%s"><img src="%s" alt="%s"></a>'
            % (href, _shield(label, message, colour),
               alt or "%s %s" % (label, message)))


def _picture(name, alt, width, height=None):
    size = 'width="%s"' % width
    if height:
        size += ' height="%s"' % height
    return ('<p align="center">\n  <picture>\n    <source media='
            '"(prefers-color-scheme: dark)" srcset="docs/assets/%s-dark.svg">'
            '\n    <img src="docs/assets/%s.svg" alt="%s" %s>\n'
            '  </picture>\n</p>\n' % (name, name, gen_assets._esc(alt), size))


def _svg_title(fig, name):
    for fname, draw in gen_assets.FIGURES:
        if fname == name:
            text = draw(fig, gen_assets.THEMES["light"])
            return html.unescape(re.search(r"<title>(.*?)</title>",
                                           text).group(1))
    raise KeyError(name)


def glossary_entries(section="Start here", path=GLOSSARY):
    """[(term, definition)] of one section of docs/GLOSSARY.md, in order.

    An entry is a paragraph that opens with the term in bold, ending in a
    full stop: `**Term.** What it means.`"""
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    body = re.split(r"^## %s\n" % re.escape(section), text, flags=re.M)[1]
    body = re.split(r"^## ", body, flags=re.M)[0]
    entries = []
    for para in re.split(r"\n\s*\n", body.strip()):
        match = re.match(r"\*\*(.+?)\.\*\* (.+)$", " ".join(para.split()))
        if match:
            entries.append((match.group(1), match.group(2)))
    if not entries:
        raise ValueError("docs/GLOSSARY.md has no entries under %r" % section)
    return entries


def citation_title(path=CITATION):
    with io.open(path, encoding="utf-8") as fh:
        match = re.search(r'^title: "(.+)"$', fh.read(), re.M)
    if not match:
        raise ValueError("CITATION.cff states no title")
    return match.group(1)


# -- the blocks -------------------------------------------------------------

def mark(fig):
    return _picture("mark", _svg_title(fig, "mark"), "128", "128")


def title(fig):
    return _picture("title", gen_assets.title_alt(fig), "620")


def statline(fig):
    return _picture("statline", gen_assets.statline_alt(fig), "100%")


def badges(fig):
    _, holds, total = fig.reference_holds()
    verdict = ("all %d criteria hold" % total if holds == total
               else "%d of %d criteria hold" % (holds, total))
    workflow = figures.REPOSITORY + "/actions/workflows/ci.yml"
    ci = ("https://img.shields.io/github/actions/workflow/status/ashfordeOU/"
          "arcs-conformance/ci.yml?branch=main&label=continuous_integration"
          "&style=flat&labelColor=%s" % LABEL)
    release = ("https://img.shields.io/github/v/release/ashfordeOU/"
               "arcs-conformance?label=release&style=flat&labelColor=%s"
               "&color=%s" % (LABEL, CYAN))
    rows = [
        '<p align="center">',
        _badge("LICENSE", "licence", "Apache-2.0", GREEN,
               alt="licence: Apache License, Version 2.0"),
        _badge(".github/workflows/ci.yml", "python",
               "%s+" % fig.pythons[0], CYAN,
               alt="Python %s or later" % fig.pythons[0]),
        _badge("#what-it-is", "dependencies", "standard library only",
               VIOLET, alt="dependencies: the Python standard library only"),
        _badge("#coverage", "cases", str(len(fig.cases)), MAGENTA,
               alt="test cases: %d" % len(fig.cases)),
        _badge("#coverage", "criteria", str(len(fig.criteria)), ORANGE,
               alt="conformance criteria: %d" % len(fig.criteria)),
        '</p>',
        '<p align="center">',
        '  <a href="%s"><img src="%s" alt="continuous integration (CI) '
        'status"></a>' % (workflow, ci),
        # Read from the repository itself: before the first release is
        # cut this says so, rather than linking a version to an empty page.
        '  <a href="%s/releases"><img src="%s" alt="the latest release, '
        'read from the repository"></a>'
        % (figures.REPOSITORY, release),
        _badge("spec/ARCS-1.md", "specification",
               "ARCS-1 " + fig.spec.edition, VIOLET,
               alt="specification: ARCS-1, edition %s" % fig.spec.edition),
        _badge("PROTOCOL.md", "adapter protocol",
               "v" + fig.protocol.rsplit("/", 1)[-1], MAGENTA,
               alt="adapter protocol %s" % fig.protocol),
        _badge("reference/adapter.py", "reference adapter", verdict, GREEN,
               alt="the reference adapter: %s" % verdict.replace(
                   "criteria", "conformance criteria")),
        '</p>',
    ]
    return "\n".join(rows) + "\n"


def diagram(fig):
    return _picture("how-it-works", _svg_title(fig, "how-it-works"), "900")


def excerpt(fig):
    outcomes = fig.reference()[0]
    status = figures.report.exit_status(outcomes)
    return ("```text\n$ python3 -m arcs_conformance --impl '%s'\n%s\n"
            "$ echo $?\n%d\n```\n"
            % (figures.REFERENCE_COMMAND, fig.excerpt(), status))


def options(fig):
    lines = ["| option | what it does |", "| --- | --- |"]
    for flag, metavar, text in fig.options():
        shown = "`%s %s`" % (flag, metavar) if metavar else "`%s`" % flag
        lines.append("| %s | %s |" % (shown, text))
    return "\n".join(lines) + "\n"


def _protocol_rows():
    """{op: (request fields, answer fields, section)} from PROTOCOL.md."""
    with io.open(PROTOCOL, encoding="utf-8") as fh:
        text = fh.read()
    rows = {}
    for op, fields, answer, section, _ in re.findall(
            r"^\| `([a-z_]+)` \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$",
            text, re.M):
        rows[op] = (fields, answer, section)
    return rows


def operations(fig):
    table = _protocol_rows()
    lines = ["| operation | the adapter is asked to | request fields | "
             "it answers | ARCS-1 | cases |",
             "| --- | --- | --- | --- | --- | --- |"]
    for row in fig.by_operation():
        fields, answer, section = table[row["op"]]
        lines.append("| `%s` | %s | %s | %s | %s | %d |" % (
            row["op"], ASKS[row["op"]], fields, answer, section,
            row["cases"]))
    return "\n".join(lines) + "\n"


def criteria(fig):
    """PROTOCOL.md's table of the fifteen criteria, each named in words."""
    lines = ["| | title in ARCS-1 §12 | the operations its cases use |",
             "| --- | --- | --- |"]
    for row in fig.by_criterion():
        lines.append("| **%s** | %s | %s |"
                     % (row["criterion"], row["title"],
                        ", ".join("`%s`" % op for op in row["operations"])))
    return "\n".join(lines) + "\n"


def totals(fig):
    rows = fig.by_criterion()
    own = sum(r["own"] for r in rows)
    derived = sum(r["derived"] for r in rows)
    ops = len(fig.operations)
    return ("**%d cases in %s operations: %d normative cases across all "
            "%s criteria of ARCS-1 §12, and %d readings.** Of the normative "
            "cases, %d follow the test §12 itself states for a criterion "
            "(*own test*) and %d rest on a *must* stated elsewhere in the "
            "text (*derived*); %d of them are controls, which must be "
            "accepted so that a criterion's refusals mean something.\n"
            % (len(fig.cases), figures.word(ops), len(fig.normative),
               figures.word(len(fig.criteria)), len(fig.readings), own,
               derived, len(fig.controls)))


def chart(fig):
    return _picture("coverage", _svg_title(fig, "coverage"), "900")


def coverage(fig):
    rows = fig.by_criterion()
    lines = ["| | title in ARCS-1 §12 | what an implementation has to show "
             "| own test | derived | controls | normative | readings |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in rows:
        lines.append("| **%s** | %s | %s | %d | %d | %d | %d | %d |" % (
            r["criterion"], r["title"], r["summary"], r["own"],
            r["derived"], r["controls"], r["normative"], r["readings"]))
    lines.append("| | **all %s** | | **%d** | **%d** | **%d** | **%d** | "
                 "**%d** |" % (figures.word(len(rows)),
                               sum(r["own"] for r in rows),
                               sum(r["derived"] for r in rows),
                               sum(r["controls"] for r in rows),
                               sum(r["normative"] for r in rows),
                               sum(r["readings"] for r in rows)))
    return "\n".join(lines) + "\n"


def versioning(fig):
    version, date = fig.release
    if version != fig.version:
        raise SystemExit("CHANGELOG.md's newest release is %s and the "
                         "package says %s" % (version, fig.version))
    pinned = [d for d, e in figures.specs.PUBLISHED.items()
              if e == fig.spec.edition]
    lines = ["| | |", "| --- | --- |",
             "| suite | `%s` %s, dated %s in "
             "[CHANGELOG.md](CHANGELOG.md) |" % (fig.name, fig.version,
                                                 date),
             "| adapter protocol | `%s` ([PROTOCOL.md](PROTOCOL.md)) |"
             % fig.protocol,
             "| specification | ARCS-1, edition %s, as published |"
             % fig.spec.edition,
             "| SHA-256 of `ARCS-1.md` the suite pins | `%s` |"
             % ", ".join(pinned),
             "| Python | %s to %s, each run in CI |"
             % (fig.pythons[0], fig.pythons[-1])]
    return "\n".join(lines) + "\n"


def glossary(fig):
    lines = ["| term | what it means |", "| --- | --- |"]
    for term, text in glossary_entries():
        if "|" in term + text or "](" in text:
            raise ValueError("glossary entry %r cannot go into a table" % term)
        lines.append("| **%s** | %s |" % (term, text))
    return "\n".join(lines) + "\n"


def cite(fig):
    version, date = fig.release
    year = date[:4]
    name = citation_title()
    return ("> Ashforde OÜ (%s). *%s*, version %s. %s\n\n```bibtex\n"
            "@software{arcs_conformance,\n  author  = {{Ashforde OÜ}},\n"
            "  title   = {%s},\n  version = {%s},\n  year    = {%s},\n"
            "  url     = {%s},\n  license = {Apache-2.0}\n}\n```\n"
            % (year, name, version, figures.REPOSITORY, name, version, year,
               figures.REPOSITORY))


BLOCKS = {
    "mark": mark, "title": title, "statline": statline, "badges": badges,
    "diagram": diagram, "excerpt": excerpt, "options": options,
    "operations": operations, "totals": totals, "chart": chart,
    "coverage": coverage, "glossary": glossary, "versioning": versioning,
    "cite": cite,
}
PROTOCOL_BLOCKS = {"criteria": criteria}
GENERATED = ((README, BLOCKS), (PROTOCOL, PROTOCOL_BLOCKS))


def render(text, fig=None, blocks=None, name="README.md"):
    """The text of one document with every generated block rewritten."""
    fig = fig or figures.Figures()
    blocks = BLOCKS if blocks is None else blocks
    found = [m.group(2) for m in BLOCK.finditer(text)]
    unknown = sorted(set(found) - set(blocks))
    missing = sorted(set(blocks) - set(found))
    twice = sorted(set(n for n in found if found.count(n) > 1))
    if unknown or missing or twice:
        raise ValueError("%s generated blocks: unknown %s, missing %s,"
                         " repeated %s" % (name, unknown, missing, twice))
    return BLOCK.sub(lambda m: m.group(1) + blocks[m.group(2)](fig)
                     + m.group(4), text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if a generated block is stale")
    args = parser.parse_args(argv)
    fig = figures.Figures()
    stale = 0
    for path, blocks in GENERATED:
        name = os.path.basename(path)
        with io.open(path, encoding="utf-8") as fh:
            current = fh.read()
        fresh = render(current, fig, blocks, name)
        if args.check:
            if fresh != current:
                sys.stderr.write("%s has stale generated blocks; run: "
                                 "python3 tools/gen_readme.py\n" % name)
                stale += 1
            continue
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(fresh)
        sys.stdout.write("%s: %d generated blocks written\n"
                         % (name, len(blocks)))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
