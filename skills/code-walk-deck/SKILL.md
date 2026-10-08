---
name: code-walk-deck
description: Build a technical slide deck that walks an audience through a real codebase — a code walk, architecture walkthrough, design review, or "show the team how this works" talk — producing a .pptx with native editable diagrams, code blocks whose file:line citations are checked mechanically, and a speaking script generated from the deck's own notes. Use this skill whenever someone asks for slides, a deck, a presentation, or a walkthrough about a repository, a system they built, or code they want to explain to colleagues, even if they do not say "code walk"; also use it when revising or re-deriving an existing deck in a slides/ directory. Not for ordinary business decks with no codebase behind them.
---

# Code-walk deck

A code walk is a deck whose claims are all checkable, delivered to people who can and will
check them. That constraint, not slide design, is what makes it different from a normal
presentation — and nearly all the machinery here exists to serve it.

## Requirements

Unlike the rest of this collection, this skill does not run on a bare login node.

| Tool | Needed for | Install |
|---|---|---|
| `node` + pptxgenjs | building the deck (step 4 on) | `npm install --prefix <scratch> pptxgenjs`, then `NODE_PATH=<scratch>/node_modules` |
| `soffice` (LibreOffice) | rendering for the layout check (step 6) | distro package `libreoffice` |
| `pdftoppm` (poppler-utils) | rendering for the layout check (step 6) | distro package `poppler-utils` |

Install pptxgenjs into a scratch directory, never into the project the deck is about — the
deck is a document, not a dependency of the code it describes.

Steps 1-3 (reading the code, `run_model.py`, the outline) and `check_anchors.py` are
stdlib Python and need none of this. Without LibreOffice and poppler you lose step 6 only,
but that step is where the real layout bugs are, so treat a deck built without it as a draft.

`new_deck.py` writes an absolute path to this skill's `deck_lib.js` into the generated
`build_deck.js`. That is what lets the scaffold resolve the library from any project, but it
means a `slides/` directory shared with someone else will not build until they repoint that
`require`.

## What you produce

In `<project>/slides/`:

| File | Role |
|---|---|
| `build_deck.js` | the deck, as code. Requires `deck_lib.js`; every diagram is native shapes |
| `run_model.py` → `run.json` | every number on a slide, mined from the repo |
| `anchors.json` | every `file:line` the deck prints, checked by `check_anchors.py` |
| `deck.json` | title and running orders, read by `make_script.py` |
| `DECK_OUTLINE.md` | audience, caveats, per-slide intent, delivery notes |
| `CODE_FOR_DECK.md` | each on-slide snippet, anchored and fidelity-marked |
| `DECK_SCRIPT.md` | **generated** — never write it by hand |
| `<name>.pptx` / `.pdf` | the artifacts |

`scripts/new_deck.py` scaffolds the first six. Nothing in the scaffold is precious.

## Three rules that keep the deck true as the code moves

A deck about code goes stale silently: the slide still looks authoritative while the line
it cites has moved 40 lines and the count it quotes is two refactors old. Each rule below
converts a silent failure into a loud one.

**1. Mine every number; label every number you cannot mine.** `run_model.py` derives
figures from the checkout each time it runs — line counts, test counts, a real run of the
thing, whatever the slides quote. Numbers that come from somewhere the script cannot reach
(a log on a cluster, a prior experiment) go in a clearly separate section of `run.json`
with a `source` field, and the slide that shows them repeats the source in its footer. An
unlabelled transcribed number is indistinguishable from a live one, which is exactly how a
stale figure survives three revisions.

**2. Check every citation mechanically.** Put every `file:line` the deck *prints* into
`anchors.json` — not just the ones in code-block captions, but the ones in table cells and
body text, which are the ones that rot unnoticed. `check_anchors.py` prefix-matches the
expected first line, so re-indentation is tolerated and real movement is reported with the
line's new location.

**3. Generate the script from the deck.** The speaker notes in `build_deck.js` are the
single source of the spoken prose; `make_script.py` renders them to `DECK_SCRIPT.md` with
measured timings. Maintaining a script alongside the notes looks harmless and diverges
within a day.

## Workflow

### 1. Read the code, and find the caveats first

Before outlining anything, read the project's own honest documents — `README`, a backlog, a
limitations file, recent commit messages. Commit messages are unusually valuable here
because they record *why*, which is what a walkthrough is mostly made of.

Find the caveats before the achievements. A code walk's credibility rests on the speaker
volunteering what does not work, and if you build the deck around the achievements first,
the caveats end up bolted on as an apology slide. Note the commit you are deriving against
and put it on the title slide.

### 2. Mine the numbers

Write `run_model.py` and run it. Run the system if it can be run cheaply — a real run's
output is far better evidence than a description of what it would do, and the irregular
details (a refused admission, a retry, an out-of-order completion) are what make a slide
specific rather than generic.

Keep generated artifacts out of the repo under test: run things in a temp directory so the
deck build never leaves state behind in the project.

### 3. Outline against a budget, not a slide count

Decide the slot length, then target **about 80% of it in speech** so questions fit. At 155
wpm that is roughly 2,500 words for a 20-minute slot. Write the outline as per-slide intent
— what each slide must make the audience understand — plus which slides are cuttable and
which are protected.

Weight the deck toward whatever this specific room came for. If the authors of a dependency
are present, the seam with their code deserves two slides and the feature tour deserves
none.

### 4. Build the deck in chunks

Write `build_deck.js` a few slides at a time, syntax-checking as you go (`node --check`),
rather than one enormous write. A single huge file write is fragile and a syntax error in
it is miserable to locate.

Keep each slide in its own `{ }` block under a `// ====== <n>. <name>` marker — that marker
is what `make_script.py` parses, and the block scope keeps per-slide geometry variables
from leaking. Name backup slides `B1`, `B2`: they are counted separately and excluded from
running orders.

See `references/slide-archetypes.md` for the slide and figure shapes that recur, with
geometry that fits.

### 5. Wire the anchors and generate the script

Fill `anchors.json` from what you actually read while writing the slides — not from memory.
Run `check_anchors.py` until it is clean, then `make_script.py`.

### 6. Render it and look at it

**This is not optional, and it is where the real bugs are.** pptxgenjs places shapes exactly
where it is told and says nothing when two of them overlap. In the session this skill came
from, the build was clean and silent while eight slides had genuine collisions: a table
running into the one below it, a right-hand rail squeezed to two inches, three card headings
wrapping onto their first bullet.

```sh
python3 <skill>/scripts/render_check.py slides/<name>.pptx
```

Read the PNGs back. Fix collisions and clipping; do not chase kerning. `references/layout-failures.md`
lists the specific ways these decks break and the fix for each.

### 7. Trim against measured timings

A first draft of notes runs long — expect 25% over. Trim by tightening prose, not by
deleting the honest parts, and re-run `make_script.py` until the orders fit. Finish with
two or three running orders in `deck.json` so the presenter picks one rather than
improvising cuts at the podium.

## Honesty is the mechanism, not the garnish

This is the part that separates a code walk from a pitch, and it is worth explaining why
rather than treating it as a style note: this audience can check you. If they catch one
overclaim, every other claim becomes suspect, including the true ones. Volunteering the
weaknesses is therefore not modesty — it is what buys belief in the rest.

Four devices do most of the work:

**Fidelity marks on every quoted snippet.** VERBATIM / TRIMMED / EDITED / ILLUSTRATIVE /
MINED, printed on the slide next to the anchor. Most blocks end up EDITED, because real
signatures carry type annotations that will not fit at a legible size — that is fine and
saying so costs nothing. What is never edited is behaviour: a block must not imply the code
does something it does not.

**A "what this is not" card beside the result card.** Put it on an early slide, in red, at
minute two — not at minute twenty, and not only when asked. If a result is one run, one
configuration, one draw, the card says so.

**A status slide, uncompressed.** Two columns: what genuinely runs, and what has never run.
When the clock is tight this slide is the one people want to cut; protect it.

**End on asks, not a summary.** A code walk's best ending is the questions you actually want
answered — ideally reproducible ones that name a file and a line. A summary slide tells an
audience what they just heard; an asks slide tells them why they are in the room.

## When the deck is for an existing codebase you have just worked in

You will often have the context already. Resist re-deriving from memory anyway: run
`run_model.py`, run `check_anchors.py`. Both exist to catch the specific error of
confidently writing down something that was true last week.

If building the deck surfaces a genuine finding about the code — it happens, because
nothing reads a system like trying to explain it — say so plainly and ask before changing
anything. A finding belongs on a slide; a fix belongs in its own change, with its own
consideration.

## Reference files

- `references/slide-archetypes.md` — the recurring slide and figure types, with geometry
  that fits: the two-lane coroutine diagram, the layer map with forbidden edges, the
  measured-run bar chart, the gate table, the green/red status columns, the asks grid.
- `references/layout-failures.md` — how these decks actually break, and the fix for each.

## Scripts

All take `--help`.

```sh
python3 <skill>/scripts/new_deck.py --project . --name my-codewalk --title "My Project"
python3 <skill>/scripts/check_anchors.py --anchors slides/anchors.json --root .
python3 <skill>/scripts/make_script.py --deck slides/build_deck.js
python3 <skill>/scripts/render_check.py slides/my-codewalk.pptx
NODE_PATH=$(npm root -g) node slides/build_deck.js
```

`deck_lib.js` is required by `build_deck.js`, not run directly. If pptxgenjs is not
installed, `npm install pptxgenjs` into a scratch directory and point `NODE_PATH` at its
`node_modules` — there is no need to add a dependency to the project.
