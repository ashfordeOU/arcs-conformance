# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Run the suite against an implementation, list it, or write it out.

    python3 -m arcs_conformance --impl 'python3 reference/adapter.py'
    python3 -m arcs_conformance --impl '<your adapter>' --json report.json
    python3 -m arcs_conformance --list
    python3 -m arcs_conformance --dump cases/

Exit status: 0 every normative case run passed; 1 at least one failed, or
carried a reliance boolean its conclusion does not (C12); 2 none failed and
at least one could not be graded; 3 the suite itself could not run, because
the copy of the specification is damaged or the arguments cannot be used.
1 and 2 are kept apart for the reason section 11 gives: a caller that
collapses refused into cannot be determined will one day treat a failed run
as a clean one.
"""

import argparse
import io
import json
import os
import sys

from . import NAME, VERSION, cases as catalogue, report, runner, spec as specs

SUITE_ERROR = 3


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: %s\n" % (self.prog, message))
        sys.exit(SUITE_ERROR)


def _parser():
    parser = _Parser(
        prog="python3 -m arcs_conformance",
        description="Run the ARCS-1 conformance suite against an "
                    "implementation that speaks the adapter protocol "
                    "(PROTOCOL.md).")
    parser.add_argument("--impl", metavar="COMMAND",
                        help="the adapter command, split as a POSIX shell "
                             "would split it and never run through one (on "
                             "Windows, the command line as written)")
    parser.add_argument("--spec", metavar="DIR",
                        help="a copy of the published ARCS-1 directory "
                             "(default: the copy in spec/)")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="seconds allowed for each call (default 30)")
    parser.add_argument("--jobs", type=int, default=1,
                        help="calls in flight at once (default 1; raise it "
                             "only for an adapter that tolerates it)")
    parser.add_argument("--only", metavar="C1,C8",
                        help="run only the cases of these criteria")
    parser.add_argument("--case", action="append", default=[],
                        metavar="ID", help="run only this case (repeatable)")
    parser.add_argument("--json", metavar="PATH",
                        help="also write the full report as JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="print the detail of passing cases too")
    parser.add_argument("--list", action="store_true",
                        help="list the cases and exit")
    parser.add_argument("--dump", metavar="DIR",
                        help="write each case's request and expectation as "
                             "JSON into DIR and exit")
    parser.add_argument("--version", action="version",
                        version="%s %s" % (NAME, VERSION))
    return parser


def _select(cases, only, ids):
    chosen = cases
    if only:
        wanted = set(c.strip().upper() for c in only.split(",") if c.strip())
        unknown = wanted - set(c.criterion for c in cases)
        if unknown:
            raise ValueError("no criterion %s" % ", ".join(sorted(unknown)))
        chosen = [c for c in chosen if c.criterion in wanted]
    if ids:
        known = set(c.id for c in cases)
        unknown = [i for i in ids if i not in known]
        if unknown:
            raise ValueError("no case %s" % ", ".join(unknown))
        chosen = [c for c in chosen if c.id in ids]
    return chosen


def _list(cases, out):
    for case in cases:
        out.write("%-4s %-9s %-15s %-52s %s\n" % (
            case.criterion, case.basis, case.op, case.id, case.clause))
    normative = sum(1 for c in cases if c.normative)
    out.write("%d cases: %d normative, %d readings\n"
              % (len(cases), normative, len(cases) - normative))


def _dump(cases, directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)
    for case in cases:
        record = case.to_dict()
        record["request"] = runner.request_for(case)
        path = os.path.join(directory, case.id + ".json")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.write("wrote %d case(s) to %s\n" % (len(cases), directory))


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        spec = specs.load(args.spec)
        cases = _select(catalogue.catalogue(spec), args.only, args.case)
    except (specs.SpecError, ValueError) as exc:
        sys.stderr.write("the suite cannot run: %s\n" % exc)
        return SUITE_ERROR
    if args.list:
        _list(cases, sys.stdout)
        return 0
    if args.dump:
        _dump(cases, args.dump)
        return 0
    if not args.impl:
        sys.stderr.write("--impl is required to run the suite; --list and "
                         "--dump need none\n")
        return SUITE_ERROR
    try:
        argv_impl = runner.command(args.impl)
    except ValueError as exc:
        sys.stderr.write("the suite cannot run: %s\n" % exc)
        return SUITE_ERROR
    described = runner.describe(argv_impl, args.timeout)
    outcomes = runner.run(argv_impl, cases, args.timeout, max(1, args.jobs))
    sys.stdout.write(report.text(outcomes, spec, args.impl, described,
                                 args.verbose))
    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report.as_json(outcomes, spec, args.impl,
                                               described),
                                ensure_ascii=False, indent=2) + "\n")
    return report.exit_status(outcomes)


if __name__ == "__main__":
    sys.exit(main())
