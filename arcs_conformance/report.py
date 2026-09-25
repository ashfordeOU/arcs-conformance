# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Reporting a run: every case, then every criterion, never one number alone.

WHY THE BREAKDOWN COMES FIRST
-----------------------------
A single figure, 117 of 120 say, invites exactly the reading a conformance
report must not allow: that the missing three are a rounding error. Three
failed cases can be one criterion broken three ways, and the criterion is
the unit ARCS-1 defines conformance in. So the report lists every case, then
every criterion with its own counts and verdict, and only then a closing
line, which names criteria and totals nothing.

WHAT A CRITERION'S VERDICT MEANS
--------------------------------
`holds`      every normative case under it passed.
`fails`      at least one normative case under it failed, or an answer
             given under another criterion broke it.
`not shown`  none failed and at least one could not be graded (ERROR).
`not run`    no normative case under it was selected on this run, and no
             answer given under another criterion broke it.

The second clause of `fails` exists for C12. The reliance boolean rides on
every verify_record answer, so every such answer is also a test of C12, and
a wrong boolean is charged there (runner.reliance) while the case it rode
on is graded on its conclusion. C12's row counts those answers beside its
own cases. Without them C12 would be graded by nine questions any
implementation can answer from a table, and the criteria whose conclusions
were right would carry C12's failure.

Readings are listed under their own heading and change none of these.
"""

import collections

from . import NAME, VERSION
from .runner import ERROR, FAIL, PASS, PROTOCOL


def _number(criterion):
    return int(criterion[1:])


def charged(outcomes, cid):
    """Judgements on normative answers that count towards `cid`."""
    return [c for o in outcomes if o.case.normative for c in o.charges
            if c.criterion == cid]


def criteria(outcomes, spec):
    rows = []
    for cid in sorted(spec.criteria, key=_number):
        mine = [o for o in outcomes
                if o.case.criterion == cid and o.case.normative]
        counts = collections.Counter(o.result for o in mine)
        answers = collections.Counter(c.result for c in charged(outcomes, cid))
        if counts[FAIL] or answers[FAIL]:
            verdict = "fails"
        elif not mine:
            verdict = "not run"
        elif counts[ERROR]:
            verdict = "not shown"
        else:
            verdict = "holds"
        rows.append({"criterion": cid, "title": spec.criteria[cid],
                     "cases": len(mine), "pass": counts[PASS],
                     "fail": counts[FAIL], "error": counts[ERROR],
                     "answers": sum(answers.values()),
                     "answers_fail": answers[FAIL],
                     "verdict": verdict})
    return rows


def readings(outcomes):
    return [o for o in outcomes if not o.case.normative]


def exit_status(outcomes):
    normative = [o for o in outcomes if o.case.normative]
    results = [o.result for o in normative]
    results += [c.result for o in normative for c in o.charges]
    if FAIL in results:
        return 1
    if ERROR in results:
        return 2
    return 0


def _ranges(ids):
    """C1, C2, C3, C5 -> C1-C3, C5."""
    numbers = sorted(_number(i) for i in ids)
    spans = []
    for n in numbers:
        if spans and spans[-1][1] == n - 1:
            spans[-1][1] = n
        else:
            spans.append([n, n])
    return ", ".join("C%d" % a if a == b else "C%d-C%d" % (a, b)
                     for a, b in spans)


def closing(rows, spec=None):
    by = collections.defaultdict(list)
    for row in rows:
        by[row["verdict"]].append(row["criterion"])
    parts = []
    for verdict, word in (("fails", "fail"), ("not shown", "not shown"),
                          ("holds", "hold"), ("not run", "not run")):
        if by[verdict]:
            parts.append("%s: %s" % (word, _ranges(by[verdict])))
    line = "Result: " + "; ".join(parts) + "."
    if len(by["holds"]) == len(rows):
        line += (" Every criterion ARCS-1 section 12 defines holds on these "
                 "cases. That is evidence about these cases and this build, "
                 "not a certification, and not an approval by anyone.")
    elif by["fails"]:
        line += (" At least one answer is one ARCS-1 forbids, so the "
                 "implementation, as its adapter presents it, does not "
                 "conform.")
    elif by["not shown"]:
        line += (" Conformance is not shown: the suite could not grade "
                 "every case, and could not tell is not a pass.")
    if spec is not None and not spec.pinned:
        line += (" The copy of ARCS-1 graded against is not a published "
                 "text this suite pins, so none of this is a result against "
                 "ARCS-1 as published.")
    return line


def _provenance(spec):
    if spec.pinned:
        return "the published text this suite pins"
    return "NOT a published text this suite pins"


def text(outcomes, spec, implementation, described, verbose=False):
    lines = ["%s %s, protocol %s" % (NAME, VERSION, PROTOCOL),
             "specification: ARCS-1, edition %s (ARCS-1.md sha256 %s, %s)"
             % (spec.edition, spec.sha256, _provenance(spec)),
             "implementation: %s" % implementation]
    if described:
        lines.append("  describes itself as: %s (not checked)" % described)
    lines += ["", "Cases"]
    for o in outcomes:
        tag = "" if o.case.normative else "  [reading]"
        lines.append("%-5s %-4s %-52s %s%s" % (o.result, o.case.criterion,
                                               o.case.id, o.case.clause, tag))
        if verbose or o.result != PASS:
            lines.append("      %s" % o.detail)
        for charge in o.charges:
            if verbose or charge.result != PASS:
                lines.append("      %s %s: %s%s" % (
                    charge.criterion, charge.result, charge.detail,
                    "" if o.case.normative else
                    " (a reading: counted towards nothing)"))
        if o.result == ERROR and o.stderr.strip():
            tail = o.stderr.strip().splitlines()[-3:]
            lines.extend("      | %s" % t for t in tail)
    rows = criteria(outcomes, spec)
    lines += ["", "Criteria (normative cases only; readings change none of "
              "these)"]
    width = max(len(row["title"]) for row in rows)
    for row in rows:
        lines.append("  %-4s %-*s %3d cases %3d pass %3d fail %3d error  %s"
                     % (row["criterion"], width, row["title"], row["cases"],
                        row["pass"], row["fail"], row["error"],
                        row["verdict"]))
        if row["answers"]:
            lines.append("       and the reliance boolean on %d verify_record "
                         "answers: %d agree with their conclusion, %d do not"
                         % (row["answers"],
                            row["answers"] - row["answers_fail"],
                            row["answers_fail"]))
    found = readings(outcomes)
    if found:
        lines += ["", "Readings (questions ARCS-1 leaves open; recorded, "
                  "counted towards nothing)"]
        for o in found:
            word = {PASS: "agrees with the suite's reading",
                    FAIL: "differs from the suite's reading",
                    ERROR: "could not be graded"}[o.result]
            lines.append("  %-4s %-52s %s" % (o.case.criterion, o.case.id,
                                              word))
    lines += ["", closing(rows, spec)]
    return "\n".join(lines) + "\n"


def as_json(outcomes, spec, implementation, described):
    rows = criteria(outcomes, spec)
    return {
        "suite": {"name": NAME, "version": VERSION, "protocol": PROTOCOL},
        "specification": {"name": "ARCS-1", "edition": spec.edition,
                          "sha256": spec.sha256, "pinned": spec.pinned},
        "implementation": {"command": implementation,
                           "describes_itself_as": described},
        "criteria": rows,
        "readings": [{"id": o.case.id, "criterion": o.case.criterion,
                      "result": o.result, "note": o.case.note}
                     for o in readings(outcomes)],
        "cases": [o.to_dict() for o in outcomes],
        "result": closing(rows, spec),
        "exit_status": exit_status(outcomes),
    }
