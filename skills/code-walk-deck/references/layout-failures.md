# How these decks actually break

pptxgenjs places shapes exactly where it is told. It does not reflow, does not clip, and
does not warn when two shapes occupy the same inches — it just draws the second one on top
of the first. So the build is clean and silent while the slide is unreadable.

Everything below was found by rendering pages to PNG and looking at them. None of it was
caught by the build. That is the argument for step 6 of the workflow, in one paragraph.

```sh
python3 <skill>/scripts/render_check.py slides/<name>.pptx
```

Read the pages back at 50 dpi — enough to see collisions, too little to be tempted into
pixel-polishing.

## The failure modes, in rough order of frequency

### A card heading wraps onto its first bullet

`card()` gives the heading a single 0.3-inch line. A heading that wraps is drawn over the
bullets, which still render — so it looks like a font bug rather than a length problem.

At 13pt, about 30 characters fit in a 3.2-inch card. Either shorten the heading (usually
better — these headings should be terse anyway) or pass `hfs: 11.5`.

Observed: "So cost models must not be tuned to it", "Promotion is mechanical, demotion
immediate", "Cancellation is advisory — measured, not assumed".

### Two stacked tables collide

`rowH` is per row, and a cell whose text wraps makes its row taller than declared, so a
table's real height exceeds the sum you budgeted. The next element overlaps its last row.

Leave 0.2 inches of slack below a table, and remember that a header row plus five rows at
0.34 is 2.04 inches, not 1.7.

### The right-hand rail gets squeezed

Lay a slide out left to right and the rail ends up with whatever is left — which was 1.96
inches on one slide here, enough for about three words per line.

Budget from the right instead: decide the rail width first (**3.5 inches minimum** for
cards with bullets), then give the left column the remainder.

### Rows walk into the cards at the bottom

An accumulator (`y += h + gap`) over five rows, where one gap had to grow to hold a return
arrow, silently pushes the last row past where the footer cards start.

Use explicit `tops[]` and `hs[]` arrays. They make the one irregular gap visible and keep
the last row's bottom edge computable by eye.

### A box's sub-text is clipped

`box()` draws title and sub inside the height it was given. Three lines of sub in a
0.6-inch box renders the first two and silently drops the third — or crops it mid-glyph.

Budget ~0.18 inches per line of sub at 9pt, plus the title's line.

### A slide title wraps and lands on the content

At 28pt Cambria bold, about 60 characters fit across 12.33 inches. A title that wraps to two
lines reaches y ≈ 1.42, which is exactly where a first content band usually starts.

Shorten the title. A code-walk title that needs two lines is usually trying to be a sentence.

### A legend or axis label runs under the next column

Legends laid out as `x = M + i * pitch` happily run past the content column and under the
right-hand rail. Compute the pitch from the available width rather than picking a round
number, and shrink the font before you shrink the gap.

### A code block is set too small to read

The one failure the build *does* catch: `code()` solves line spacing for its box and warns
below 8.5pt. Treat that warning as a build failure. The fix is almost always to cut lines
from the snippet, not to grow the box — if a block needs more than ~12 lines, it is doing
more than one job.

## Converting and rendering

LibreOffice renders slightly differently from PowerPoint — generally tighter line breaking,
so a label that fits in the PDF usually fits in PowerPoint too, but not always the reverse.
Checking the PDF is the right compromise: it catches every collision, and collisions are
what matter.

If the deck will be presented from PowerPoint or Keynote, open it there once before the
talk. Do not re-do the layout pass in two tools; just confirm nothing is grossly different.
