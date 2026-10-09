#!/usr/bin/env python3
"""Regenerate a deck's speaking script from the `addNotes` blocks in build_deck.js.

    python3 make_script.py [--deck slides/build_deck.js] [--out slides/DECK_SCRIPT.md]

The deck is the single source of the spoken prose, so a presenter reading the notes pane
and a presenter reading DECK_SCRIPT.md can never diverge. Run it after editing any slide's
notes. Maintaining the script separately looks harmless and goes wrong within a day.

Word counts are the spoken prose only: anything in [brackets] is a stage direction or a
per-slide budget and is excluded. 155 wpm is a realistic rate for technical material
delivered with pauses — fast enough to be honest about, slow enough to leave room to
breathe.

Slides are found by the `// ===...=== <n>. <name>` comment markers in build_deck.js, and
a slide whose name starts with "B" is treated as a backup: counted separately, never part
of a running order.

Configuration is optional. Drop a `deck.json` beside build_deck.js to set the title, the
three acts and the running orders:

    {
      "title": "IMPRESS-A code walk",
      "acts": [
        {"n": 1, "name": "Functionality", "from": 6,  "slides": "6-10",
         "question": "what new tasks does it make possible?",
         "gap": "the protocol has never run on a cluster"}
      ],
      "orders": [
        {"name": "A · full",   "drop": [],           "fits": "a 25-minute slot"},
        {"name": "B · default","drop": ["6", "10"],  "fits": "a 20-minute slot"}
      ],
      "protect": "Protect 8, 9 and 16 — the seam and the asks."
    }

`from` is the slide that opens the act, and it is the only ordering information here: the
act heading is emitted above that slide, so renumbering the deck cannot leave the script
divided in the wrong places. `gap` is the act's weakest claim, and it belongs in the script
because that is the sentence a presenter is most likely to soften under pressure.

With no config it still runs, reporting the full path and nothing else.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

WPM = 155


def spoken_words(notes: str) -> int:
    """Words actually said. [Bracketed] text is direction, not speech."""
    clean = re.sub(r"\[[^\]]*\]", " ", notes)
    return len([w for w in clean.split() if re.search(r"\w", w)])


def parse_slides(src: str) -> list[tuple[str, str, int]]:
    slides = re.findall(r"// =+ (.+?)\n(.*?)(?=\n// =+ |\n\w+\.writeFile|\nD\.save|\Z)",
                        src, re.S)
    out = []
    for name, body in slides:
        match = re.search(r"\.addNotes\(\s*`(.*?)`\);", body, re.S)
        notes = match.group(1).strip() if match else ""
        out.append((name.strip(), notes, spoken_words(notes)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deck", default="slides/build_deck.js")
    ap.add_argument("--out", default=None, help="default: DECK_SCRIPT.md beside the deck")
    ap.add_argument("--config", default=None, help="default: deck.json beside the deck")
    ap.add_argument("--wpm", type=int, default=WPM)
    args = ap.parse_args()

    deck = Path(args.deck).resolve()
    if not deck.exists():
        print(f"no deck at {deck}", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else deck.parent / "DECK_SCRIPT.md"
    cfg_path = Path(args.config) if args.config else deck.parent / "deck.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    wpm = args.wpm

    entries = parse_slides(deck.read_text())
    if not entries:
        print(f"no slides found in {deck} — expected `// ===...=== 1. Title` markers",
              file=sys.stderr)
        return 1

    main_entries = [e for e in entries if not e[0].startswith("B")]
    backups = [e for e in entries if e[0].startswith("B")]
    total = sum(e[2] for e in main_entries)

    def order_total(drop: list[str]) -> int:
        return total - sum(e[2] for e in main_entries if e[0].split(".")[0] in set(drop))

    title = cfg.get("title") or deck.parent.parent.name
    head: list[str] = [f"# {title} — speaking script\n"]
    head.append(
        """**This file is generated from the `addNotes` blocks in `build_deck.js`.** The deck is the
single source of the spoken prose, so a presenter reading from the notes pane and a presenter
reading from this file never diverge. Regenerate after editing the deck — the command is at the
bottom.

**How to read it.** Plain prose is meant to be *said*. Anything in `[brackets]` is a stage direction
or that slide's budget, and is excluded from the word counts.

**Pacing — measured, not estimated.** Counts are the actual spoken prose at """
        + f"{wpm} words/minute, a\nrealistic rate for technical material delivered with pauses.\n")

    head.append("| Slide | Spoken | | Slide | Spoken |")
    head.append("|---|---|---|---|---|")
    half = (len(main_entries) + 1) // 2
    for i in range(half):
        left = main_entries[i]
        right = main_entries[i + half] if i + half < len(main_entries) else None
        unit = " min" if i == 0 else ""
        row = f"| {left[0]} | {left[2] / wpm:.1f}{unit} |"
        row += f" | {right[0]} | {right[2] / wpm:.1f} |" if right else " | | |"
        head.append(row)

    head.append("")
    head.append(f"**Main path: {total} words = {total / wpm:.1f} minutes of speech.** "
                + (f"Backups add {sum(e[2] for e in backups) / wpm:.1f} min if used.\n"
                   if backups else "\n"))

    acts = cfg.get("acts") or []
    if acts:
        head.append("| Act | The question it answers | Slides | What it concedes |")
        head.append("|---|---|---|---|")
        for a in acts:
            head.append(f"| **{a.get('name', '')}** | {a.get('question', '')} | "
                        f"{a.get('slides', '')} | {a.get('gap', '')} |")
        head.append("")

    orders = cfg.get("orders") or []
    if orders:
        head.append("| Order | What's in | Speech | Fits |")
        head.append("|---|---|---|---|")
        for o in orders:
            drop = o.get("drop") or []
            whats_in = o.get("in") or (
                "every main slide" if not drop else "drop " + ", ".join(drop))
            head.append(f"| **{o['name']}** | {whats_in} | "
                        f"**{order_total(drop) / wpm:.1f}** | {o.get('fits', '')} |")
        head.append("")
    if cfg.get("protect"):
        head.append(cfg["protect"] + "\n")
    if cfg.get("say_out_loud"):
        head.append("**Say these out loud even if nothing prompts them:** "
                    + cfg["say_out_loud"] + "\n")

    # An act's `from` is the number of the slide that opens it, so the heading
    # lands above that slide rather than being maintained as a second ordering.
    opens = {str(a.get("from")): a for a in acts if a.get("from") is not None}

    parts = ["\n".join(head), "---\n"]
    for name, notes, words in entries:
        act = opens.get(name.split(".")[0])
        if act:
            parts.append(f"# Act {act.get('n', '')} — {act.get('name', '')}\n")
        parts.append(f"## {name} — *{words / wpm:.1f} min*\n")
        parts.append(notes + "\n")
    parts.append(f"""---

## Regenerating this file

The prose lives in `{deck.name}`. After editing a slide's `addNotes`:

```sh
python3 make_script.py --deck {args.deck}
```
""")
    out.write_text("\n".join(parts))

    print(f"wrote {out}")
    summary = f"  main path: {total} words = {total / wpm:.1f} min"
    for o in orders:
        summary += f"  ·  {o['name']} = {order_total(o.get('drop') or []) / wpm:.1f} min"
    if backups:
        summary += f"  ·  backups {sum(e[2] for e in backups) / wpm:.1f} min"
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
