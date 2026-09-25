#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""Write every image in docs/assets, in a light and a dark variant.

    python3 tools/gen_assets.py           write them
    python3 tools/gen_assets.py --check   exit 1 if any committed image
                                          differs from what this writes

WHY THE IMAGES ARE GENERATED
----------------------------
An image that states a figure is prose that no search will find. The
statline says how many cases there are; the coverage chart draws one block
per case; the mark carries one tick per criterion. If any of those were
drawn by hand they would be the first thing to go stale. So each is written
here from tools/figures.py, as SVG, by the standard library alone, and the
same tree always writes the same bytes. tests/test_generated.py fails when a
committed image is not what this file writes.

The visual system is the one the other public Ashforde OÜ repositories use:
a navy ground, the cyan, violet, magenta and orange accents, flat fills and
monospaced upper-case labels. A label that a sighted reader sees is written
in words, not in short forms, because the words that spell a short form out
live in the prose and nobody reads an image's alt text. The README shows
the light or the dark variant of each image according to the reader's
theme.
"""

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figures  # noqa: E402

ASSETS = os.path.join(figures.ROOT, "docs", "assets")

THEMES = {
    "light": {
        "ground": "#f6f7fc", "panel": "#ffffff", "tile": "#eef1fb",
        "ink": "#151a33", "muted": "#5a6289", "rule": "#c9cee6",
        "cyan": "#0891b2", "violet": "#7c3aed", "magenta": "#db2777",
        "orange": "#ea580c", "green": "#15803d",
    },
    "dark": {
        "ground": "#0a0d1e", "panel": "#111632", "tile": "#1a1e35",
        "ink": "#edf0fc", "muted": "#8a93c4", "rule": "#2a3160",
        "cyan": "#38bdf8", "violet": "#a78bfa", "magenta": "#f472b6",
        "orange": "#fb923c", "green": "#3fb950",
    },
}

# The wordmark gradient, as the other Ashforde OÜ repositories spell it.
GRADIENT = ("#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f97316",
            "#f59e0b")

STYLE = """  <style>
    .mono { font-family: "JetBrains Mono", "IBM Plex Mono", "Menlo", monospace; }
    .sans { font-family: Poppins, Nunito, "SF Pro Rounded", "Segoe UI", system-ui, -apple-system, sans-serif; }
  </style>
"""

MONO = 0.6  # advance of one monospaced character, in ems


def _f(value):
    """A coordinate, written the same way on every platform."""
    text = "%.1f" % value
    return text[:-2] if text.endswith(".0") else text


def _esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _svg(width, height, title, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" '
            'viewBox="0 0 %s %s" role="img">\n<title>%s</title>\n%s%s'
            '</svg>\n' % (_f(width), _f(height), _f(width), _f(height),
                          _esc(title), STYLE, "".join(body)))


def _mix(a, b, t):
    """The colour a fraction t of the way from a to b."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(round(x + (y - x) * t))
                                   for x, y in zip(ca, cb))


def _along(stops, t):
    """The colour a fraction t of the way along a list of stops."""
    if t <= 0:
        return stops[0]
    if t >= 1:
        return stops[-1]
    scaled = t * (len(stops) - 1)
    i = int(scaled)
    return _mix(stops[i], stops[i + 1], scaled - i)


def _at(stops, offsets, t):
    """The colour at t along stops placed at the given offsets."""
    t = min(max(t, offsets[0]), offsets[-1])
    for i in range(len(offsets) - 1):
        if t <= offsets[i + 1]:
            return _mix(stops[i], stops[i + 1],
                        (t - offsets[i]) / (offsets[i + 1] - offsets[i]))
    return stops[-1]


def _width(text, size, spacing=0.0):
    """The advance of monospaced text: enough to lay out, not to typeset."""
    return len(text) * (size * MONO + spacing)


def _text(x, y, text, size, fill, anchor="start", spacing=0, weight=None,
          cls="mono"):
    extra = ' font-weight="%s"' % weight if weight else ""
    if spacing:
        extra += ' letter-spacing="%s"' % _f(spacing)
    return ('<text class="%s" x="%s" y="%s" text-anchor="%s" font-size="%s" '
            'fill="%s"%s>%s</text>\n' % (cls, _f(x), _f(y), anchor, _f(size),
                                         fill, extra, _esc(text)))


# -- the mark ---------------------------------------------------------------

def mark(fig, c):
    """A seal: a ring in the wordmark gradient, one tick per criterion of
    section 12, a reticle, and a check at its centre."""
    n = len(fig.criteria)
    stops = (c["cyan"], c["violet"], c["magenta"], c["orange"])
    body = ['<defs><linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="%s"/><stop offset="0.4" '
            'stop-color="%s"/><stop offset="0.7" stop-color="%s"/>'
            '<stop offset="1" stop-color="%s"/></linearGradient></defs>\n'
            % stops,
            '<rect x="4" y="4" width="232" height="232" rx="52" '
            'fill="%s"/>\n' % c["tile"],
            '<circle cx="120" cy="120" r="84" fill="none" stroke="url(#ring)"'
            ' stroke-width="9"/>\n',
            '<circle cx="120" cy="120" r="56" fill="%s" stroke="%s" '
            'stroke-width="2"/>\n' % (c["panel"], c["rule"])]
    # Each tick takes the ring's colour beside it: the ring's gradient runs
    # corner to corner across its own box, 120 +/- 88.5 on both axes.
    offsets = (0.0, 0.4, 0.7, 1.0)
    for i in range(n):
        angle = math.radians(-90 + i * 360.0 / n)
        x1, y1 = 120 + 96 * math.cos(angle), 120 + 96 * math.sin(angle)
        x2, y2 = 120 + 107 * math.cos(angle), 120 + 107 * math.sin(angle)
        t = ((x1 - 31.5) + (y1 - 31.5)) / (2 * 177.0)
        body.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
                    'stroke-width="5" stroke-linecap="round"/>\n'
                    % (_f(x1), _f(y1), _f(x2), _f(y2),
                       _at(stops, offsets, t)))
    for x1, y1, x2, y2 in ((120, 44, 120, 60), (120, 180, 120, 196),
                           (44, 120, 60, 120), (180, 120, 196, 120)):
        body.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" '
                    'stroke-width="3" stroke-linecap="round"/>\n'
                    % (x1, y1, x2, y2, c["muted"]))
    body.append('<polyline points="93,121 112,140 148,100" fill="none" '
                'stroke="%s" stroke-width="13" stroke-linecap="round" '
                'stroke-linejoin="round"/>\n' % c["ink"])
    node = math.radians(-38)
    body.append('<circle cx="%s" cy="%s" r="8" fill="%s" stroke="%s" '
                'stroke-width="3"/>\n'
                % (_f(120 + 84 * math.cos(node)),
                   _f(120 + 84 * math.sin(node)), c["cyan"], c["tile"]))
    title = ("Mark of this conformance suite: a seal with %s ticks, one for "
             "each conformance criterion, around a check mark"
             % figures.word(n))
    return _svg(240, 240, title, body)


# -- the title --------------------------------------------------------------

# What the letters stand for, spelled out in the image itself: a reader who
# has never met the specification should not have to look it up to read the
# first thing on the page.
FULL_NAME = "Agent Run Conformance Specification"


def title_alt(fig):
    return ("ARCS-1 Conformance: the test suite for the %s (ARCS-1), by "
            "Ashforde OÜ (osaühing, an Estonian private limited company), "
            "under the Apache License, Version 2.0" % FULL_NAME)


def title(fig, c):
    word = "Conformance"
    letters = "".join('<tspan fill="%s">%s</tspan>'
                      % (_along(GRADIENT, i / float(len(word) - 1)), ch)
                      for i, ch in enumerate(word))
    subtitle = [("TEST SUITE", c["cyan"]), ("BY ASHFORDE OÜ", c["violet"]),
                ("APACHE-2.0", c["orange"])]
    parts = []
    for i, (text, colour) in enumerate(subtitle):
        if i:
            parts.append('<tspan fill="%s" dx="10">·</tspan>' % c["muted"])
        parts.append('<tspan fill="%s"%s>%s</tspan>'
                     % (colour, ' dx="10"' if i else "", _esc(text)))
    body = ['<rect width="960" height="204" rx="22" fill="%s"/>\n'
            % c["ground"],
            '<text class="sans" x="480" y="90" text-anchor="middle" '
            'font-size="70" font-weight="800" fill="%s"><tspan fill="%s">'
            'ARCS-1</tspan> %s</text>\n' % (c["ink"], c["cyan"], letters),
            _text(480, 138, "THE " + FULL_NAME.upper(), 15, c["ink"],
                  anchor="middle", spacing=3),
            '<text class="mono" x="480" y="176" text-anchor="middle" '
            'font-size="14" letter-spacing="4">%s</text>\n' % "".join(parts)]
    return _svg(960, 204, title_alt(fig), body)


# -- the statline -----------------------------------------------------------

def statline_items(fig):
    """(figure, label, colour, words for the alt text), in reading order.

    The alt text is read aloud where the image is not seen, so it spells
    out what the image abbreviates."""
    _, holds, total = fig.reference_holds()
    first, last = fig.criteria[0], fig.criteria[-1]
    pythons = "%s–%s" % (fig.pythons[0], fig.pythons[-1])
    if holds == total:
        verdict = ("the reference adapter holds all %d conformance criteria"
                   % total)
    else:
        verdict = ("the reference adapter holds only %d of the %d "
                   "conformance criteria" % (holds, total))
    return [
        (str(len(fig.cases)), "CASES", "cyan",
         "%d test cases" % len(fig.cases)),
        (str(len(fig.criteria)), "CRITERIA", "violet",
         "%d conformance criteria (%s to %s)" % (len(fig.criteria), first,
                                                 last)),
        (str(len(fig.operations)), "OPERATIONS", "magenta",
         "%d operations" % len(fig.operations)),
        (str(len(fig.readings)), "READINGS", "orange",
         "%d readings of open questions" % len(fig.readings)),
        (pythons, "PYTHON", "cyan",
         "Python %s to %s" % (fig.pythons[0], fig.pythons[-1])),
        ("ALL %d" % total if holds == total else "%d OF %d" % (holds,
                                                               total),
         "CRITERIA HOLD · REFERENCE ADAPTER", "green", verdict),
    ]


def statline_alt(fig):
    return " · ".join(item[3] for item in statline_items(fig))


def statline(fig, c):
    items = statline_items(fig)
    big, small, gap_in, gap_out = 34, 13, 9, 34
    width = 0.0
    for i, (value, label, _, _) in enumerate(items):
        width += (_width(value, big) + gap_in + _width(label, small, 2)
                  + (gap_out if i else 0))
    total = int(width + 96)
    spans = []
    for i, (value, label, colour, _) in enumerate(items):
        spans.append('<tspan%s font-size="%d" fill="%s" font-weight="800">'
                     '%s</tspan>' % (' dx="%d"' % gap_out if i else "", big,
                                     c[colour], _esc(value)))
        spans.append('<tspan dx="%d" font-size="%d" fill="%s" '
                     'letter-spacing="2">%s</tspan>'
                     % (gap_in, small, c["muted"], _esc(label)))
    body = ['<rect width="%d" height="74" rx="16" fill="%s"/>\n'
            % (total, c["ground"]),
            '<text class="mono" x="%s" y="47" text-anchor="middle">%s'
            '</text>\n' % (_f(total / 2.0), "".join(spans))]
    return _svg(total, 74, statline_alt(fig), body)


# -- how a run works --------------------------------------------------------

def _box(x, y, w, h, c, step, head, lines, accent):
    out = ['<rect x="%s" y="%s" width="%s" height="%s" rx="10" fill="%s" '
           'stroke="%s" stroke-width="1.4"/>\n'
           % (_f(x), _f(y), _f(w), _f(h), c["panel"], c[accent]),
           _text(x + 16, y + 28, step, 11, c[accent], spacing=2),
           _text(x + 16, y + 52, head, 14, c["ink"], spacing=1,
                 weight="700")]
    for i, line in enumerate(lines):
        out.append(_text(x + 16, y + 80 + i * 20, line, 11.5, c["muted"],
                         spacing=1))
    return out


def _arrow(x1, y1, x2, y2, c, both=False):
    out = ['<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
           'stroke-width="1.6"/>\n' % (_f(x1), _f(y1), _f(x2), _f(y2),
                                       c["ink"])]

    def head(xa, ya, xb, yb):
        if ya == yb:
            d = 1 if xb > xa else -1
            return ('<path d="M %s %s l %s -5 v 10 Z" fill="%s"/>\n'
                    % (_f(xb), _f(yb), _f(-10 * d), c["ink"]))
        d = 1 if yb > ya else -1
        return ('<path d="M %s %s l -5 %s h 10 Z" fill="%s"/>\n'
                % (_f(xb), _f(yb), _f(-10 * d), c["ink"]))
    out.append(head(x1, y1, x2, y2))
    if both:
        out.append(head(x2, y2, x1, y1))
    return out


def how_it_works(fig, c):
    exits = "EXIT 0 PASS · 1 FAIL · 2 NOT SHOWN · %d SUITE ERROR" % \
        figures.cli.SUITE_ERROR
    body = ['<rect width="1260" height="460" rx="18" fill="%s"/>\n'
            % c["ground"],
            _text(40, 44, "HOW A RUN WORKS", 13, c["muted"], spacing=3)]
    body += _box(40, 80, 220, 170, c, "01", "THE SPECIFICATION",
                 ["ARCS-1, COPIED IN SPEC/", "CHECKSUMS VERIFIED",
                  "PUBLISHED DIGEST PINNED"], "violet")
    body += _box(320, 80, 260, 170, c, "02", "THE SUITE",
                 ["BUILDS %d CASES" % len(fig.cases),
                  "FROM THE SECTION 13 VECTORS", "GRADES EVERY ANSWER",
                  "AGAINST ITS CLAUSE"], "cyan")
    body += _box(800, 80, 210, 170, c, "03", "YOUR ADAPTER",
                 ["ANY LANGUAGE", "ONE PROCESS PER CALL",
                  "SPEAKS PROTOCOL.MD"], "magenta")
    body += _box(1050, 80, 175, 170, c, "04", "YOUR VERIFIER",
                 ["THE IMPLEMENTATION", "UNDER TEST"], "orange")
    body += _box(320, 300, 690, 130, c, "05", "THE REPORT",
                 ["EVERY CASE: PASS · FAIL · ERROR",
                  "EVERY CRITERION: HOLDS · FAILS · NOT SHOWN · NOT RUN",
                  exits], "green")
    body += _arrow(264, 165, 316, 165, c)
    body += _arrow(586, 135, 794, 135, c)
    body.append(_text(690, 124, "REQUEST · STANDARD INPUT", 10.5, c["muted"],
                      anchor="middle", spacing=1))
    body += _arrow(794, 200, 586, 200, c)
    body.append(_text(690, 222, "ANSWER · STANDARD OUTPUT", 10.5,
                      c["muted"], anchor="middle", spacing=1))
    body.append(_text(690, 274, "ONE JSON OBJECT EACH WAY", 10.5,
                      c["muted"], anchor="middle", spacing=1))
    body += _arrow(1014, 165, 1046, 165, c, both=True)
    body += _arrow(450, 254, 450, 296, c)
    return _svg(1260, 460, "How a run works: the suite reads its copy of the "
                "%s (ARCS-1), builds %d cases from the worked examples in its "
                "section 13, sends each to your adapter as one JSON "
                "(JavaScript Object Notation) object on standard input, "
                "grades the answer your adapter writes on standard output "
                "against the clause of ARCS-1 it rests on, and reports every "
                "case and every criterion" % (FULL_NAME, len(fig.cases)),
                body)


# -- coverage ---------------------------------------------------------------

def coverage(fig, c):
    rows = fig.by_criterion()
    most = max(r["normative"] + r["readings"] for r in rows)
    label_w = max(_width("%-4s %s" % (r["criterion"], r["title"]), 12)
                  for r in rows)
    x0 = 40 + label_w + 44
    unit = 26.0
    width = int(x0 + most * unit + 110)
    top, pitch = 108, 30
    height = top + len(rows) * pitch + 30
    kinds = (("own", "OWN TEST IN SECTION 12", "cyan"),
             ("derived", "DERIVED FROM A REQUIREMENT ELSEWHERE", "violet"),
             ("readings", "READING · COUNTS TOWARDS NOTHING", "orange"))
    body = ['<rect width="%d" height="%d" rx="18" fill="%s"/>\n'
            % (width, height, c["ground"]),
            _text(40, 44, "CASES PER CRITERION", 13, c["muted"], spacing=3)]
    x = 40
    for key, label, colour in kinds:
        if key == "readings":
            body.append('<rect x="%s" y="62.8" width="12.4" height="12.4" '
                        'rx="3" fill="none" stroke="%s" stroke-width="1.6"/>'
                        '\n' % (_f(x + 0.8), c[colour]))
        else:
            body.append('<rect x="%s" y="62" width="14" height="14" rx="3" '
                        'fill="%s"/>\n' % (_f(x), c[colour]))
        body.append(_text(x + 22, 74, label, 11, c["muted"], spacing=1))
        x += 22 + _width(label, 11, 1) + 36
    for i, row in enumerate(rows):
        y = top + i * pitch
        # The number and the title are one label, so that a reader, or a
        # check, never meets the number on its own.
        body.append('<text class="mono" x="40" y="%s" font-size="12">'
                    '<tspan fill="%s" font-weight="700">%s</tspan> '
                    '<tspan x="%s" fill="%s">%s</tspan></text>\n'
                    % (_f(y + 15), c["ink"], row["criterion"],
                       _f(40 + _width("C00  ", 12)), c["muted"],
                       _esc(row["title"])))
        x = x0
        for key, _, colour in kinds:
            for _ in range(row[key]):
                if key == "readings":
                    body.append('<rect x="%s" y="%s" width="%s" height="18" '
                                'rx="3" fill="none" stroke="%s" '
                                'stroke-width="1.6"/>\n'
                                % (_f(x + 0.8), _f(y + 0.8), _f(unit - 5.6),
                                   c[colour]))
                else:
                    body.append('<rect x="%s" y="%s" width="%s" height="18" '
                                'rx="3" fill="%s"/>\n'
                                % (_f(x), _f(y), _f(unit - 4), c[colour]))
                x += unit
        count = "%d" % row["normative"]
        if row["readings"]:
            count += " + %d" % row["readings"]
        body.append(_text(x + 8, y + 14, count, 11.5, c["ink"], spacing=1))
    first, last = fig.criteria[0], fig.criteria[-1]
    return _svg(width, height, "Cases per conformance criterion of the %s "
                "(ARCS-1), %s to %s: %d normative cases, split into each "
                "criterion's own test in section 12 and cases derived from a "
                "requirement stated elsewhere in the text, and %d readings of "
                "open questions that count towards nothing"
                % (FULL_NAME, first, last, len(fig.normative),
                   len(fig.readings)), body)


FIGURES = (("mark", mark), ("title", title), ("statline", statline),
           ("how-it-works", how_it_works), ("coverage", coverage))


def render(fig=None):
    """{path relative to the root: SVG text} for every image."""
    fig = fig or figures.Figures()
    out = {}
    for name, draw in FIGURES:
        for theme, suffix in (("light", ""), ("dark", "-dark")):
            path = "docs/assets/%s%s.svg" % (name, suffix)
            out[path] = draw(fig, THEMES[theme])
    return out


def stale(rendered):
    """Paths whose committed bytes differ, and images nobody writes."""
    problems = []
    for path, text in sorted(rendered.items()):
        full = os.path.join(figures.ROOT, *path.split("/"))
        try:
            with open(full, "rb") as fh:
                current = fh.read()
        except (IOError, OSError):
            current = None
        if current != text.encode("utf-8"):
            problems.append("%s is not what tools/gen_assets.py writes"
                            % path)
    if os.path.isdir(ASSETS):
        for name in sorted(os.listdir(ASSETS)):
            if "docs/assets/" + name not in rendered:
                problems.append("docs/assets/%s is written by nothing" % name)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if a committed image is stale")
    args = parser.parse_args(argv)
    rendered = render()
    if args.check:
        problems = stale(rendered)
        for problem in problems:
            sys.stderr.write(problem + "\n")
        if problems:
            sys.stderr.write("run: python3 tools/gen_assets.py\n")
        return 1 if problems else 0
    if not os.path.isdir(ASSETS):
        os.makedirs(ASSETS)
    for path, text in sorted(rendered.items()):
        with open(os.path.join(figures.ROOT, *path.split("/")), "wb") as fh:
            fh.write(text.encode("utf-8"))
    sys.stdout.write("wrote %d images to docs/assets\n" % len(rendered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
