#!/usr/bin/env python3
"""Render a built deck to page images so the layout can actually be looked at.

    python3 render_check.py slides/my-deck.pptx [--out <dir>] [--dpi 50] [--pages 4,5,11]

A deck that builds is not a deck that reads. pptxgenjs places shapes exactly where it is
told and says nothing when two of them land on top of each other, so every real layout
bug — a table running into the one below it, a right-hand rail squeezed to two inches, a
card heading that wraps onto its first bullet — is invisible until somebody looks at a
picture of the page.

This converts to PDF via LibreOffice, rasterises the pages, and prints the paths. Read
the PNGs back and scan for collisions and clipping. 50 dpi is deliberate: it is enough to
see overlap and far too little to be tempted into pixel-polishing.

Requires `soffice` (LibreOffice) and `pdftoppm` (poppler-utils) on PATH.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx")
    ap.add_argument("--out", default=None,
                    help="directory for the PNGs (default: a fresh temp dir)")
    ap.add_argument("--dpi", type=int, default=50)
    ap.add_argument("--pages", default=None,
                    help="comma-separated page numbers, or a range like 4-6 (default: all)")
    ap.add_argument("--keep-pdf", action="store_true")
    args = ap.parse_args()

    for tool in ("soffice", "pdftoppm"):
        if not shutil.which(tool):
            print(f"{tool} not on PATH — need libreoffice and poppler-utils", file=sys.stderr)
            return 1

    pptx = Path(args.pptx).resolve()
    if not pptx.exists():
        print(f"no deck at {pptx}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="deck-pages-"))
    out.mkdir(parents=True, exist_ok=True)

    # LibreOffice writes the PDF beside the input unless told otherwise; send it to `out`
    # so a stale PDF never sits next to the deck pretending to be current.
    pdf_dir = pptx.parent if args.keep_pdf else out
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                        "--outdir", str(pdf_dir), str(pptx)],
                       capture_output=True, text=True)
    pdf = pdf_dir / (pptx.stem + ".pdf")
    if not pdf.exists():
        print("conversion failed:\n" + (r.stderr or r.stdout), file=sys.stderr)
        return 1

    cmd = ["pdftoppm", "-png", "-r", str(args.dpi)]
    if args.pages:
        if "-" in args.pages:
            first, last = args.pages.split("-", 1)
        else:
            pages = [int(p) for p in args.pages.split(",")]
            first, last = min(pages), max(pages)
        cmd += ["-f", str(first), "-l", str(last)]
    cmd += [str(pdf), str(out / "p")]
    subprocess.run(cmd, check=True)

    pages = sorted(out.glob("p*.png"))
    print(f"{len(pages)} page(s) at {args.dpi} dpi:")
    for p in pages:
        print(f"  {p}")
    print("\nRead these back and look for: boxes overlapping the thing below them, text "
          "spilling past a card, headings wrapping onto their first bullet, and anything "
          "clipped at a slide edge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
