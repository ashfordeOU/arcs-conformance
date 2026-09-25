# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Running an implementation through the catalogue, one process per call.

WHY ONE PROCESS PER CALL
------------------------
The suite has to test implementations it cannot see, in languages it does
not speak, so the only interface it assumes is the one every language has:
a command that reads a request on standard input and writes an answer on
standard output. One process per call costs start-up time and buys
isolation. No case can leave state behind that changes the answer to the
next, and a crash on one hostile document is an ERROR against that case,
not the end of the run.

WHAT IS GRADED, AND WHAT IS NOT
-------------------------------
A case is PASS when the answer is one the specification allows, FAIL when
it is an answer the specification forbids, and ERROR when there was no
answer to grade: the command did not start, ran out of time, exited with a
status other than 0, or wrote something that is not a response. ERROR is
never read as PASS and never as FAIL. It is the suite saying it could not
tell, and section 10's rule applies to the suite as much as to a verifier:
I could not check is not it is fine.

One check runs on every verify_record answer whatever the case asks: the
reliance boolean must be true for `current` and false for everything else
(section 11, C12). An implementation that answers the right conclusion with
the wrong boolean has told a caller who reads only the boolean something
the conclusion does not say, and that is a FAIL. It is C12's FAIL, and it
is charged to C12 rather than to the criterion the case is under. The case
itself is graded on its conclusion: an implementation whose conclusions are
right and whose boolean is wrong has broken one criterion, and a report
that blamed eleven for it would send its author to the wrong code. An
answer with no boolean at all is another matter. It is not a verify_record
response as PROTOCOL.md describes one, so, like an answer with no
conclusion, it is an ERROR against its case, and C12 has nothing to judge.

WHY A KILLED ADAPTER TAKES ITS CHILDREN WITH IT
-----------------------------------------------
Many adapters are wrappers: a shell script, an npm script, a launcher that
starts the real verifier. Killing only the wrapper on a timeout leaves the
verifier running with the suite's pipes still open, and the suite would wait
for it however long it takes. So on POSIX each call runs in a process group
of its own and the whole group is killed; and whatever still holds the pipes
after that is given a few seconds and then abandoned, never waited for.
"""

import json
import os
import re
import shlex
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

from .cases import REFUSED, RELIANCE_CRITERION

PROTOCOL = "arcs-conformance-adapter/1"
UNSUPPORTED = 3
PASS, FAIL, ERROR = "PASS", "FAIL", "ERROR"
_HEX = re.compile(r"\A(?:[0-9a-fA-F]{2})*\Z")
_TAIL = 600
_GRACE = 5.0


class Charge(object):
    """A judgement on one case's answer that belongs to another criterion."""

    def __init__(self, criterion, result, detail):
        self.criterion = criterion
        self.result = result
        self.detail = detail

    def to_dict(self):
        return {"criterion": self.criterion, "result": self.result,
                "detail": self.detail}


class Outcome(object):
    """What happened to one case.

    `result` grades the answer against the case's own clause and counts
    towards the case's own criterion. `charges` are judgements on the same
    answer that count towards another criterion: today only C12's, on the
    reliance boolean of a verify_record answer.
    """

    def __init__(self, case, result, detail, responses=None, stderr="",
                 seconds=0.0, charges=None):
        self.case = case
        self.result = result
        self.detail = detail
        self.responses = responses or []
        self.stderr = stderr
        self.seconds = seconds
        self.charges = charges or []

    def to_dict(self):
        return {"id": self.case.id, "criterion": self.case.criterion,
                "clause": self.case.clause, "basis": self.case.basis,
                "op": self.case.op, "result": self.result,
                "detail": self.detail, "expect": self.case.expect,
                "charged": [c.to_dict() for c in self.charges],
                "responses": self.responses, "stderr": self.stderr,
                "seconds": round(self.seconds, 3)}


def command(text, windows=None):
    """What `--impl` names, in the form the platform starts a process from.

    On POSIX the text is split as a shell would split it and never run by
    one. Windows starts a process from a command line, not from a vector of
    arguments, and a POSIX split would eat every backslash in a Windows
    path, so there the text is handed over as written.
    """
    if windows is None:
        windows = os.name == "nt"
    if not text or not text.strip():
        raise ValueError("--impl names no command")
    if windows:
        return text
    argv = shlex.split(text)
    if not argv:
        raise ValueError("--impl names no command")
    return argv


def request_for(case):
    request = {"protocol": PROTOCOL, "case": case.id, "op": case.op}
    request.update(case.request)
    return request


def _kill(proc):
    """Kill the call's whole process group, the adapter's children too."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except OSError:
        pass


def _drain(proc):
    """Standard error of a killed call, without waiting on stragglers.

    A descendant that left the process group can hold the pipes open after
    the group is dead. The suite gives it _GRACE seconds and then closes its
    own ends, because a run that hangs on one case grades none.
    """
    try:
        return proc.communicate(timeout=_GRACE)[1]
    except subprocess.TimeoutExpired:
        for pipe in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if pipe:
                    pipe.close()
            except (OSError, ValueError):
                pass
        try:
            proc.wait(timeout=_GRACE)
        except subprocess.TimeoutExpired:
            pass
        return b""


def call(argv, request, timeout, cwd=None):
    """(response or None, why there is none, stderr text)."""
    data = json.dumps(request, ensure_ascii=True, sort_keys=True)
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=cwd,
                                start_new_session=(os.name == "posix"))
    except (OSError, ValueError) as exc:
        return None, "the implementation did not start: %s" % exc, ""
    try:
        out, err = proc.communicate(data.encode("ascii"), timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill(proc)
        return None, "no answer within %gs" % timeout, _text(_drain(proc))
    err = _text(err)
    if proc.returncode == UNSUPPORTED:
        return None, ("the implementation does not support %s (exit status "
                      "%d)" % (request.get("op"), UNSUPPORTED)), err
    if proc.returncode != 0:
        return None, "exit status %d" % proc.returncode, err
    try:
        response = json.loads(out.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, "standard output is not one JSON object", err
    if not isinstance(response, dict):
        return None, "standard output is not one JSON object", err
    return response, None, err


def _text(raw):
    text = (raw or b"").decode("utf-8", "replace")
    return text[-_TAIL:]


def run_case(argv, case, timeout, cwd=None):
    started = time.time()
    responses = []
    stderr = ""
    for _ in range(case.repeat):
        response, why, stderr = call(argv, request_for(case), timeout, cwd)
        if response is None:
            return Outcome(case, ERROR, why, responses, stderr,
                           time.time() - started)
        responses.append(response)
    result, detail = grade(case, responses)
    charges = []
    judged = reliance(case, responses)
    if judged is not None:
        charges.append(Charge(RELIANCE_CRITERION, judged[0], judged[1]))
    return Outcome(case, result, detail, responses, stderr,
                   time.time() - started, charges)


def run(argv, cases, timeout=30.0, jobs=1, cwd=None):
    """Every case, in catalogue order whatever order they finish in."""
    if jobs <= 1:
        return [run_case(argv, case, timeout, cwd) for case in cases]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(lambda c: run_case(argv, c, timeout, cwd),
                             cases))


def describe(argv, timeout=30.0, cwd=None):
    """What the implementation says it is, or None. Never checked."""
    response, _, _ = call(argv, {"protocol": PROTOCOL, "op": "describe"},
                          timeout, cwd)
    if not response:
        return None
    name, version = response.get("name"), response.get("version")
    if not isinstance(name, str):
        return None
    return name if not isinstance(version, str) else "%s %s" % (name, version)


# -- grading -----------------------------------------------------------------

def _problems(response):
    problems = response.get("problems")
    if isinstance(problems, list) and problems:
        return " (it said: %s)" % "; ".join(str(p) for p in problems[:3])
    return ""


def _protocol_error(field, kind):
    return ERROR, "the response carries no %s (%s)" % (field, kind)


def grade(case, responses):
    """(PASS | FAIL | ERROR, one sentence), against the case's own clause."""
    response = responses[0]
    expect = case.expect
    grader = _GRADERS[case.op]
    return grader(case, responses, response, expect)


def reliance(case, responses):
    """C12's judgement on a verify_record answer's boolean, or None.

    None where there is nothing to judge: another operation, or an answer
    whose conclusion or boolean is missing, which grade() has already
    reported as an ERROR against the case.
    """
    if case.op != "verify_record":
        return None
    conclusion = responses[0].get("conclusion")
    relied = responses[0].get("relied")
    if not isinstance(conclusion, str) or not isinstance(relied, bool):
        return None
    if relied != (conclusion == "current"):
        return FAIL, ("answered %s with relied %s: the reliance boolean is "
                      "true for current and nothing else"
                      % (conclusion, str(relied).lower()))
    return PASS, "relied %s with %s" % (str(relied).lower(), conclusion)


def _grade_verify(case, responses, response, expect):
    conclusion = response.get("conclusion")
    relied = response.get("relied")
    if not isinstance(conclusion, str):
        return _protocol_error("conclusion", "a string")
    if not isinstance(relied, bool):
        return _protocol_error("relied", "a boolean")
    allowed = expect["conclusion"]
    vocabulary = case.vocabulary
    if conclusion not in vocabulary:
        return FAIL, ("answered %r, which is none of the section 11 "
                      "conclusions and not %s" % (conclusion, REFUSED))
    # The boolean is judged by reliance() and charged to C12, not here.
    if conclusion not in allowed:
        return FAIL, ("answered %s; the clause allows %s%s"
                      % (conclusion, _allowed(allowed), _problems(response)))
    return PASS, "answered %s" % conclusion


def _allowed(allowed):
    return allowed[0] if len(allowed) == 1 else \
        "any of " + ", ".join(allowed)


def _refused(response, expect):
    """The verdict on an answer that is a refusal, or None if it is not."""
    if response.get("refused") is not True:
        return None
    if expect.get("refused"):
        return PASS, "refused%s" % _problems(response)
    return FAIL, "refused an input the clause accepts%s" % _problems(response)


def _grade_canonicalise(case, responses, response, expect):
    refused = _refused(response, expect)
    if refused:
        return refused
    got = response.get("canonical_hex")
    if not isinstance(got, str) or not _HEX.match(got):
        return _protocol_error("canonical_hex", "hex of the bytes")
    if expect.get("refused"):
        return FAIL, "serialised it as %s where the clause requires a " \
            "refusal" % _show(got)
    if got.lower() != expect["canonical_hex"]:
        return FAIL, "produced %s; the clause gives %s" % (
            _show(got), _show(expect["canonical_hex"]))
    return PASS, "the bytes match"


def _show(hex_text):
    try:
        return repr(bytes.fromhex(hex_text).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return "bytes %s" % hex_text[:80]


def _grade_derive(case, responses, response, expect):
    refused = _refused(response, expect)
    if refused:
        return refused
    got = response.get("id")
    if not isinstance(got, str):
        return _protocol_error("id", "a string")
    if got != expect["id"]:
        return FAIL, "derived %s; section 6 gives %s" % (got, expect["id"])
    return PASS, "derived %s" % got


def _grade_boolean(field):
    def grader(case, responses, response, expect):
        got = response.get(field)
        if not isinstance(got, bool):
            return _protocol_error(field, "a boolean")
        if got != expect[field]:
            return FAIL, "answered %s %s; the clause requires %s%s" % (
                field, str(got).lower(), str(expect[field]).lower(),
                _problems(response))
        return PASS, "answered %s %s" % (field, str(got).lower())
    return grader


def _grade_build(case, responses, response, expect):
    for each in responses:
        refused = _refused(each, expect)
        if refused:
            return refused
    documents = [r.get("document") for r in responses]
    if not all(isinstance(d, str) for d in documents):
        return _protocol_error("document", "the built record as JSON text")
    if expect.get("refused"):
        return FAIL, "built a record where the clause requires a refusal"
    if len(set(documents)) != 1:
        return FAIL, ("two builds from the same inputs gave different "
                      "bytes (C15)")
    try:
        built = json.loads(documents[0])
    except ValueError:
        return FAIL, "the built record is not JSON"
    if not isinstance(built, dict):
        return FAIL, "the built record is not a JSON object"
    fields = expect["fields"]
    extra = sorted(set(built) - set(fields) - {"record_id"})
    if extra:
        return FAIL, "the builder added %s, which it was not given" % \
            ", ".join(extra)
    changed = sorted(k for k in fields if built.get(k) != fields[k])
    if changed:
        return FAIL, "the builder changed or dropped %s" % ", ".join(changed)
    if built.get("record_id") != expect["record_id"]:
        return FAIL, "built record_id %r; section 6 gives %s" % (
            built.get("record_id"), expect["record_id"])
    return PASS, "built %s%s" % (
        expect["record_id"],
        ", byte-identical twice" if case.repeat > 1 else "")


_GRADERS = {
    "verify_record": _grade_verify,
    "canonicalise": _grade_canonicalise,
    "derive_id": _grade_derive,
    "reliance": _grade_boolean("relied"),
    "matches": _grade_boolean("matches"),
    "check_successor": _grade_boolean("accepted"),
    "build_record": _grade_build,
}
