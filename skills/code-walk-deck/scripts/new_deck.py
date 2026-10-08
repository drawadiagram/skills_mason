#!/usr/bin/env python3
"""Scaffold a code-walk deck into <project>/slides/.

    python3 new_deck.py --project . --name my-codewalk --title "My Project"

Writes the files that are the same every time — a build_deck.js already wired to
deck_lib, a run_model.py with the mined/transcribed split structured, an empty anchor
table, a deck.json, and skeletons for the two authored documents. It deliberately does
not write DECK_SCRIPT.md: that is generated from the deck's own notes by make_script.py.

Nothing here is precious. Delete what does not fit the project; the point is to start
from the shape rather than from a blank file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent / "deck_lib.js"

BUILD_DECK = '''// Builds {out}.
//
//   python3 run_model.py                    # regenerate run.json first
//   NODE_PATH=<dir with pptxgenjs> node build_deck.js
//
// Every diagram is native, editable shapes - never an image. Line style carries status:
//   solid  built, runs end to end for real
//   dotted built and tested, never exercised for real
//   dashed designed for, not implemented
//
// Numbers come from run.json. Anything that could not be mined from the repo is labelled
// with its source there AND on the slide that shows it.
const path = require("path");
const fs = require("fs");
const {{ createDeck }} = require("{lib}");

const R = JSON.parse(fs.readFileSync(path.join(__dirname, "run.json"), "utf8"));

const D = createDeck({{
  title: "{title}",
  author: "{title}",
  // Give each layer of the system one colour and keep it for the whole deck.
  palette: {{ /* a: "3B4E8C", b: "1E6470", c: "2E7D5B", d: "7A4A8C", accent: "D9731A" */ }},
}});
const {{ pres, C, W, H, M, HF, BF, MF, text, title, box, line, label,
        legend, pill, code, footer, card, tbl, save }} = D;

// ================================================================ 1. Title
{{
  const s = pres.addSlide(); s.background = {{ color: C.ink }};
  text(s, "{title}", M + 0.3, 1.5, 7.0, 0.4,
    {{ fontSize: 14, bold: true, color: "8FB8C9", charSpacing: 3 }});
  text(s, "A one-line thesis, not a topic", M + 0.3, 1.95, 7.1, 1.35,
    {{ fontFace: HF, fontSize: 34, bold: true, color: C.white }});
  text(s, `Code walk · main @ ${{R.code.head}}`, M + 0.3, 6.45, 8.5, 0.3,
    {{ fontSize: 12, color: "7E8F9C" }});
  s.addNotes(
`[0:45] Open by saying what this is and what it is not, then the one sentence that makes
the rest of the deck a consequence rather than a tour.`);
}}

// ================================================================ 2. Next slide
{{
  const s = pres.addSlide(); s.background = {{ color: C.white }};
  title(s, "Slide title", "Section");
  s.addNotes(`[1:00] Spoken prose. Bracketed text is direction and is not counted.`);
}}

save(path.join(__dirname, "{out}"));
'''

RUN_MODEL = '''#!/usr/bin/env python3
"""Mine every number the deck prints into run.json.

    python3 run_model.py

A deck about code goes stale silently. The defence is that no number is typed by hand:
each one is derived here from the repository as it is right now, so regenerating is how
you find out the deck has drifted.

Two kinds of number, kept apart on purpose:

  mined        computed from this checkout, every time this runs
  transcribed  copied from somewhere this script cannot reach - a log on a cluster, a
               notebook, a plan document. Say WHERE in the `source` field, and say it on
               the slide too. An unlabelled transcribed number is indistinguishable from
               a mined one, which is how a stale figure survives three revisions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "run.json"


def code_stats() -> dict:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    # Add what this deck actually cites: line counts per package, a test count, the
    # number of whatever this project's unit of work is. Keep it to numbers a slide uses.
    return {"head": head}


TRANSCRIBED = {
    "source": "SAY WHERE THESE CAME FROM — the slide footer should repeat it",
    # "runs": [...],
}


def main() -> int:
    run = {"code": code_stats(), "transcribed": TRANSCRIBED}
    OUT.write_text(json.dumps(run, indent=1) + "\\n")
    print(f"wrote {OUT}")
    print(f"  code: @ {run['code']['head']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

DECK_JSON = '''{{
  "title": "{title} code walk",
  "orders": [
    {{"name": "A · full", "drop": [], "fits": "a 25-minute slot"}},
    {{"name": "B · default", "drop": [], "fits": "a 20-minute slot with questions inline"}}
  ],
  "protect": "**Protect** the slides this room came for, and do not compress the status slide.",
  "say_out_loud": "the caveats that would damage your credibility if someone else found them first"
}}
'''

CODE_FOR_DECK = '''# Code for the deck — staging file

Every code block that appears on a slide, keyed by snippet ID, anchored, and marked for
fidelity. Slide numbers and snippet IDs match across this file, `DECK_OUTLINE.md` and
`build_deck.js`.

Every anchor here is checked mechanically:

```sh
python3 <skill>/scripts/check_anchors.py --anchors slides/anchors.json
```

**Fidelity marking, on every block:**

| Mark | Meaning |
|---|---|
| **VERBATIM** | byte-identical to the source at the cited lines — safe to present as "this is the code" |
| **TRIMMED** | verbatim lines with whole lines removed; nothing rewritten |
| **EDITED** | restructured for legibility — **the slide says so**, and the real file is one grep away |
| **ILLUSTRATIVE** | not from the repo at all; label it, and never let it be quoted as shipped code |
| **MINED** | real output from a real run, not source — `run.json` says which run |

A slide is 13.3 inches wide and the back of the room is far away, so roughly 12 lines at
70 columns is the legible maximum. Most blocks end up EDITED because real signatures carry
type annotations that do not fit. What is never edited is behaviour: no block may say the
code does something it does not do.

| ID | Slide | Source | Fidelity | What changed |
|---|---|---|---|---|
| S?-A | ? | `path.py:10–20` | TRIMMED | — |
'''

DECK_OUTLINE = '''# {title} — code walkthrough

**Format:** ? minutes, code walk · **Audience:** ?

Say who is in the room and what that weights the deck toward. If the authors of something
you depend on are present, the seam with their code is what they came for.

---

## The one thing to be straight about

The caveat that would cost you the room if someone else found it first. Put it on an early
slide and again on the status slide.

---

## Visual vocabulary

```
line style = status      solid   built, runs end to end for real
                         dotted  built and tested, never exercised for real
                         dashed  designed for, not implemented
```

Colour roles: one per layer of the system, held for the whole deck.

---

## Slides

### 1 — Title
### 2 — ...

---

## Delivery notes

- Open a terminal in the repo root. Every anchor on a slide is greppable live, and this
  audience may ask you to.
- Have `run.json` open. "Let me show you where that came from" beats repeating the number.

---

## Before presenting

```sh
python3 slides/run_model.py
python3 <skill>/scripts/check_anchors.py --anchors slides/anchors.json
python3 <skill>/scripts/make_script.py --deck slides/build_deck.js
NODE_PATH=<dir with pptxgenjs> node slides/build_deck.js
```
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="repo root; slides/ is created inside it")
    ap.add_argument("--name", required=True, help="output deck basename, e.g. my-codewalk")
    ap.add_argument("--title", required=True)
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    slides = Path(args.project).resolve() / "slides"
    slides.mkdir(parents=True, exist_ok=True)
    out_name = args.name if args.name.endswith(".pptx") else args.name + ".pptx"

    files = {
        "build_deck.js": BUILD_DECK.format(lib=LIB, title=args.title, out=out_name),
        "run_model.py": RUN_MODEL,
        "anchors.json": "[]\n",
        "deck.json": DECK_JSON.format(title=args.title),
        "CODE_FOR_DECK.md": CODE_FOR_DECK,
        "DECK_OUTLINE.md": DECK_OUTLINE.format(title=args.title),
    }

    wrote, skipped = [], []
    for name, body in files.items():
        p = slides / name
        if p.exists() and not args.force:
            skipped.append(name)
            continue
        p.write_text(body)
        wrote.append(name)

    print(f"scaffolded {slides}")
    for n in wrote:
        print(f"  + {n}")
    for n in skipped:
        print(f"  . {n} (exists, left alone — pass --force to overwrite)")
    print("\nNext: fill in run_model.py and run it, then write the slides. "
          "DECK_SCRIPT.md is generated by make_script.py, so do not write it by hand.")
    print("anchors.json starts empty, and check_anchors.py refuses an empty table on "
          "purpose — add an entry for every file:line a slide prints.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
