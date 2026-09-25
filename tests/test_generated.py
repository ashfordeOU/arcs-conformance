#!/usr/bin/env python3
# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""The README's generated blocks and every image, held to their generators.

The statline, the badges, the tables, the run excerpt and the images are
written from the tree by tools/gen_readme.py and tools/gen_assets.py. A
generated file that nobody regenerates is a copy like any other, so this
fails the moment a committed block or image differs from what its generator
writes now: add a case, and this goes red until the README and the chart
say so.

The generators are loaded by path, not imported by name, because `tools` is
a name other projects use too.

Run: python3 tests/test_generated.py
"""

import difflib
import importlib.util
import io
import os
import sys
import unittest
import xml.etree.ElementTree as ElementTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    path = os.path.join(ROOT, "tools", name + ".py")
    spec = importlib.util.spec_from_file_location("arcs_tools_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen_readme = load("gen_readme")
gen_assets = gen_readme.gen_assets
figures = gen_readme.figures


def read(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


class TheGeneratedFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fig = figures.Figures()
        cls.readme = read("README.md")
        cls.images = gen_assets.render(cls.fig)

    def test_the_readme_blocks_are_current(self):
        fresh = gen_readme.render(self.readme, self.fig)
        if fresh != self.readme:
            diff = "".join(list(difflib.unified_diff(
                self.readme.splitlines(True), fresh.splitlines(True),
                "README.md", "generated"))[:60])
            self.fail("README.md is stale; run python3 tools/gen_readme.py"
                      "\n" + diff)

    def test_the_images_are_current(self):
        self.assertEqual(gen_assets.stale(self.images), [])

    def test_the_images_are_deterministic(self):
        self.assertEqual(gen_assets.render(self.fig), self.images)

    def test_every_image_is_well_formed_and_titled(self):
        for path, text in sorted(self.images.items()):
            root = ElementTree.fromstring(text.encode("utf-8"))
            title = root.find("{http://www.w3.org/2000/svg}title")
            self.assertTrue(title is not None and title.text, path)

    def test_every_image_has_both_variants_and_the_readme_shows_them(self):
        for name, _ in gen_assets.FIGURES:
            light = "docs/assets/%s.svg" % name
            dark = "docs/assets/%s-dark.svg" % name
            self.assertIn(light, self.images)
            self.assertIn(dark, self.images)
            picture = ('srcset="%s">\n    <img src="%s"' % (dark, light))
            self.assertIn(picture, self.readme, name)

    def test_the_statline_is_the_reference_run(self):
        held, holds, total = self.fig.reference_holds()
        self.assertEqual(holds, total, "the reference adapter no longer "
                                       "holds every criterion")
        self.assertEqual(held, figures.span(self.fig.criteria))

    def test_the_protocol_blocks_are_current(self):
        with io.open(os.path.join(ROOT, "PROTOCOL.md"),
                     encoding="utf-8") as fh:
            current = fh.read()
        fresh = gen_readme.render(current, self.fig,
                                  gen_readme.PROTOCOL_BLOCKS, "PROTOCOL.md")
        self.assertEqual(fresh, current, "PROTOCOL.md is stale; run "
                                         "python3 tools/gen_readme.py")


if __name__ == "__main__":
    unittest.main()
