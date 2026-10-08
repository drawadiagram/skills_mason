#!/usr/bin/env python3
"""Verify every code anchor the deck cites still points where it claims.

    python3 check_anchors.py [--anchors slides/anchors.json] [--root .]

Anchors are load-bearing. A slide that says `executor.py:304` and shows code from
somewhere else is worse than a slide with no citation at all, because the citation
invites a check that then fails — and a code-walk audience can and does grep while you
talk. Run this before presenting, and after any edit to the source the deck quotes.

`anchors.json` is a list of entries, each `[path, line, expected_first_line]` with an
optional fourth element for a note:

    [
      ["src/impress_a/exec/dispatch.py", 144, "def _make_task"],
      ["toolkits/rosetta/tools/filter_shape/spec.yaml", 1, "id: filter_shape", "S10-A"]
    ]

Paths are relative to --root (default: the current directory). The check is a prefix
match on the stripped line, so re-indentation is tolerated and real movement is not.
When a line has moved, the script says where it moved to — the point is to fix the deck,
not to paper over the drift.

Every `file:line` the deck PRINTS belongs in the table, whether it is rendered in a code
block's anchor label, a table cell, or body text. A citation is a citation wherever it
appears, and the ones in body text are exactly the ones that rot unnoticed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check(root: Path, rel: str, line_no: int, expected: str, note: str = "") -> bool:
    path = root / rel
    tag = f" ({note})" if note else ""
    if not path.exists():
        print(f"MISSING  {rel}{tag}")
        return False
    lines = path.read_text(errors="replace").splitlines()
    actual = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else "<past EOF>"
    if actual.startswith(expected.strip()):
        return True
    real = next((i + 1 for i, line in enumerate(lines)
                 if line.strip().startswith(expected.strip())), None)
    print(f"DRIFT    {rel}:{line_no}{tag}")
    print(f"         expected {expected!r}")
    print(f"         found    {actual!r}")
    print(f"         now at   {real if real else 'NOT FOUND — the snippet may be gone'}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchors", default="slides/anchors.json")
    ap.add_argument("--root", default=".", help="what the anchor paths are relative to")
    args = ap.parse_args()

    anchors_path = Path(args.anchors)
    if not anchors_path.exists():
        print(f"no anchor table at {anchors_path}", file=sys.stderr)
        return 1
    entries = json.loads(anchors_path.read_text())
    if not entries:
        print("anchor table is empty — every file:line the deck prints should be in it",
              file=sys.stderr)
        return 1

    root = Path(args.root).resolve()
    results = [check(root, e[0], e[1], e[2], e[3] if len(e) > 3 else "") for e in entries]
    ok, total = sum(results), len(results)
    print(f"\n{ok}/{total} anchors verified")
    if ok != total:
        print("Fix the deck to match the code, or the anchor to match where it moved. "
              "Do not present a drifted anchor.")
        return 1
    print("all good")
    return 0


if __name__ == "__main__":
    sys.exit(main())
