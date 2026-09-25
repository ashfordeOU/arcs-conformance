# Copyright 2026 Ashforde OÜ
# SPDX-License-Identifier: Apache-2.0
"""A conformance suite for ARCS-1, runnable against any implementation.

The suite hands an implementation one request per case over a small
language-neutral protocol (PROTOCOL.md), grades each answer against what
ARCS-1 allows, and reports every case and every criterion. It decides
nothing about any record, and a pass is not a certification by anyone.
"""

NAME = "arcs-conformance"
VERSION = "2.0.0"
