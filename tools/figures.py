# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Every figure the README and its images state, read from the tree.

WHY THIS FILE EXISTS
--------------------
A figure typed into prose is a copy, and a copy drifts: the day a case is
added, a README that says 141 is wrong and nothing says so. So every count
the README's generated blocks and the images in docs/assets carry is
computed here, from the same objects the suite runs on:

  cases, bases, controls   the catalogue (arcs_conformance.cases)
  criteria and titles      section 12 of the copy of ARCS-1 in spec/
  edition and digest       the copy in spec/, and the digest the suite pins
  operations               the catalogue's operation list
  command-line options     the suite's own argument parser
  Python versions          the `python:` entries of .github/workflows/ci.yml
  the reference verdict    a real run of the reference adapter, through the
                           real protocol, one process per call

tools/gen_readme.py and tools/gen_assets.py render these; neither holds a
number of its own. Standard library only, and deterministic: the same tree
gives the same bytes.
"""

import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from arcs_conformance import (  # noqa: E402
    NAME, VERSION, __main__ as cli, cases as catalogue, report, runner,
    spec as specs)

REPOSITORY = "https://github.com/ashfordeOU/arcs-conformance"
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "ci.yml")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

# How the README tells a reader to run the reference adapter. The run below
# starts the same file with this interpreter, so that a check made under
# another Python does not depend on which `python3` is first on the PATH.
REFERENCE_COMMAND = "python3 reference/adapter.py"
REFERENCE_ARGV = [sys.executable, os.path.join(ROOT, "reference",
                                               "adapter.py")]

NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six",
                "seven", "eight", "nine", "ten", "eleven", "twelve",
                "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                "eighteen", "nineteen", "twenty")


def word(n):
    """A small count spelled out, as prose spells it; larger ones as digits."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def number(criterion):
    return int(criterion[1:])


def span(criteria, dash="–"):
    """C1, C2, C3, C5 -> C1–C3, C5 (the report's own ranges, typeset)."""
    return report._ranges(criteria).replace("-", dash)


def python_versions(path=WORKFLOW):
    """Every Python the CI workflow runs, oldest first."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    found = set()
    for value in re.findall(r"^\s*-?\s*python:\s*(.+?)\s*$", text, re.M):
        found.update(re.findall(r"[0-9]+\.[0-9]+", value))
    if not found:
        raise ValueError("%s names no Python version" % path)
    return sorted(found, key=lambda v: tuple(int(p) for p in v.split(".")))


def released(path=CHANGELOG):
    """(version, date) of the newest release CHANGELOG.md records."""
    with open(path, encoding="utf-8") as fh:
        match = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\] — "
                          r"([0-9]{4}-[0-9]{2}-[0-9]{2})$", fh.read(), re.M)
    if not match:
        raise ValueError("CHANGELOG.md records no release")
    return match.group(1), match.group(2)


class Figures(object):
    """The counts, read once; the reference run, made on first use."""

    def __init__(self):
        self.spec = specs.load()
        self.cases = catalogue.catalogue(self.spec)
        self.name = NAME
        self.version = VERSION
        self.protocol = runner.PROTOCOL
        self.pythons = python_versions()
        self.release = released()
        self._run = None

    # -- the catalogue ----------------------------------------------------

    @property
    def criteria(self):
        return sorted(self.spec.criteria, key=number)

    @property
    def normative(self):
        return [c for c in self.cases if c.normative]

    @property
    def readings(self):
        return [c for c in self.cases if not c.normative]

    @property
    def controls(self):
        return [c for c in self.cases if "-control-" in c.id]

    @property
    def operations(self):
        return list(catalogue.OPERATIONS)

    def by_criterion(self):
        """One row per criterion: its title, its sentence and its counts."""
        rows = []
        for cid in self.criteria:
            mine = [c for c in self.cases if c.criterion == cid]
            bases = collections.Counter(c.basis for c in mine)
            rows.append({
                "criterion": cid,
                "title": self.spec.criteria[cid],
                "summary": catalogue.SUMMARY[cid],
                "own": bases["criterion"],
                "derived": bases["must"],
                "normative": bases["criterion"] + bases["must"],
                "controls": sum(1 for c in mine if "-control-" in c.id),
                "readings": bases["reading"],
                "operations": sorted(set(c.op for c in mine),
                                     key=catalogue.OPERATIONS.index),
            })
        return rows

    def by_operation(self):
        rows = []
        for op in catalogue.OPERATIONS:
            mine = [c for c in self.cases if c.op == op]
            rows.append({"op": op, "cases": len(mine),
                         "normative": sum(1 for c in mine if c.normative),
                         "criteria": span(set(c.criterion for c in mine))})
        return rows

    def options(self):
        """(flags, metavar, help) for every option the command line takes."""
        rows = []
        for action in cli._parser()._actions:
            if not action.option_strings or "-h" in action.option_strings:
                continue
            flag = max(action.option_strings, key=len)
            metavar = action.metavar or ("" if action.nargs == 0 else
                                         action.dest.upper())
            text = action.help or ""
            if flag == "--version":
                metavar, text = "", "print the suite's name and version"
            rows.append((flag, metavar, text))
        return rows

    # -- the reference run ------------------------------------------------

    def reference(self):
        """(outcomes, report text, criterion rows) of a real run."""
        if self._run is None:
            described = runner.describe(REFERENCE_ARGV, 60)
            outcomes = runner.run(REFERENCE_ARGV, self.cases, 60, 8)
            text = report.text(outcomes, self.spec, REFERENCE_COMMAND,
                               described)
            self._run = (outcomes, text, report.criteria(outcomes,
                                                         self.spec))
        return self._run

    def reference_holds(self):
        """(the criteria the reference adapter holds, as a typeset range,
        how many hold, how many there are)."""
        rows = self.reference()[2]
        held = [r["criterion"] for r in rows if r["verdict"] == "holds"]
        return span(held), len(held), len(rows)

    def excerpt(self, cases_shown=3):
        """The reference run's report, with most case lines elided."""
        lines = self.reference()[1].rstrip("\n").split("\n")
        start = lines.index("Cases") + 1
        end = lines.index("", start)
        case_lines = [l for l in lines[start:end] if not l.startswith(" ")]
        kept = lines[:start] + case_lines[:cases_shown]
        kept.append("[%d more case lines]" % (len(case_lines) - cases_shown))
        return "\n".join(kept + lines[end:])
