# Slide and figure archetypes

The shapes that recur in code-walk decks, with geometry that fits a 13.333 × 7.5 inch page
at `M = 0.5` margins. Numbers here are starting points that have survived contact with a
projector, not a grid to obey.

Usable vertical space below a title with a kicker is roughly **y = 1.45 → 7.0**, with the
footer at 7.1.

## Contents

- [Title](#title)
- [What it does / what it is not](#what-it-does--what-it-is-not)
- [The constraint slide](#the-constraint-slide)
- [Two-lane process diagram](#two-lane-process-diagram)
- [Layer map with forbidden edges](#layer-map-with-forbidden-edges)
- [Typed-hop strip](#typed-hop-strip)
- [Gate or rule table](#gate-or-rule-table)
- [Code slide](#code-slide)
- [Measured-run bars](#measured-run-bars)
- [Defect ledger](#defect-ledger)
- [Status columns](#status-columns)
- [Asks grid](#asks-grid)

---

## Title

Dark background. Left half carries an eyebrow, a thesis in ~34pt serif, a one-line subtitle
that states the claim rather than the topic, and a line of real numbers. Right half carries
a motif: a small diagram of the system's actual shape, not a logo.

The subtitle is the slide's work. "An agent that composes its own workflows" is a thesis;
"Project overview" is a topic. If the subtitle could head any deck in the organisation,
rewrite it.

Put the commit on the title slide. It tells the audience exactly what they are being shown
and dates the claims.

## What it does / what it is not

A six-step strip across the top (`box` at y 1.55, h 1.15, width ~1.93 with 0.11 gaps), then
**two cards side by side** at y 3.5, each ~6.25 wide, h ~2.25:

- left, neutral fill: what the system actually produced, with real values
- right, `failTint` fill and `fail` heading: what that does not demonstrate

The right card is the slide's reason to exist. An audience that hears the caveats at minute
two from the speaker trusts the rest; an audience that discovers them at minute twenty does
not.

If the process is a loop rather than a pipeline, draw the back edges under the strip and
label them — that is usually the single most clarifying mark on the slide.

## The constraint slide

The slide to keep if you keep one: it converts the rest of the deck from a tour into a
chain of consequences.

A dark band at y 1.5 (h ~0.95) states the fact or facts that force the design, with the
load-bearing words in the accent and fail colours. Below it, a three-column table:
consequence · what it means in the code · where. Close with the honest inverse — *if the
constraint did not hold, you would not build this* — which is what makes it an argument
rather than an assertion.

## Two-lane process diagram

For anything with two independent actors meeting at an interface: a reasoner and an
executor, a client and a server, a producer and a consumer.

Three vertical bands at y 1.5 (h 0.38): actor A, the interface, actor B. Under each, a small
mono label naming the file. Then rows of boxes down each lane with arrows between them
labelled with **the type that crosses**, not the action.

Two things that matter more than the geometry:

- Never draw one actor inside the other's frame if they are peers. For an audience that
  knows the system, that single containment claims an architecture.
- Use explicit `tops[]` and `hs[]` arrays rather than accumulating `y += h + gap`. One row
  usually needs a wider gap below it — for a return edge and its label — and hand-solving
  that in an accumulator is how rows creep into the cards at the bottom.

## Layer map with forbidden edges

A column of coloured band labels at x = M (w ~1.1) with the contents of each band in a
bordered box beside them. Budget the horizontal space from the right: a right-hand rail of
explanatory cards needs **at least 3.5 inches** to be readable, so the band content column
gets what is left, usually ~5.9.

**Draw the edges that are forbidden**, in red, with ✗. An architectural rule that is merely
absent from a diagram reads as an oversight, and the first question will be whether it is
enforced or merely intended. If it is enforced by a test, say which.

## Typed-hop strip

Six boxes across (w ~1.95, h ~1.25, gaps 0.13) with a mono anchor under each, showing one
unit of work transformed through the system with the type named at every hop. Underneath,
real output from a real run, and a table of what that run did.

Keep box titles short: at 11pt a title longer than about 18 characters breaks mid-word in a
1.95-inch box. Drop to 10pt or shorten the label.

## Gate or rule table

A `tbl` with the rule, what it rejects, and the line. Then a second table for whatever is
*not* a gate but runs in the same path, with a different header fill so the distinction is
visible.

Leave 0.2 inches between stacked tables. `rowH` is per-row and a row whose text wraps needs
more than the default — a table that silently grows is the most common cause of a collision
with whatever sits below it.

## Code slide

Two or three `code` blocks with `anchor` captions, plus cards explaining what to look at.
About **12 lines at 70 columns** is the legible maximum; `code()` warns if the type would
fall below 8.5pt.

Choose the smallest excerpt that still shows the behaviour. Elide bodies to `...` rather
than shrinking the type, mark the block EDITED, and name in `CODE_FOR_DECK.md` exactly what
was changed. A reader who greps the file and finds something different should find the
difference already documented.

## Measured-run bars

Stacked horizontal bars on a shared axis, one row per run, drawn from mined data. Rows at
~0.68 pitch, bar height ~0.26, axis below with ticks, legend under that.

Make the figure about **one variable** if you can. Three rows that differ in one thing beat
eight rows that differ in several. Label each row with the condition, annotate with what it
proves in one line, and put the per-stage legend below the axis — not beside the bars, where
it will collide with a right-hand rail.

## Defect ledger

Full-width rows (h ~1.18), each: a large numeral, a short name, what happened, and what it
is now. Alternate the row fill.

Close with the generalisation in a dark band. The specific defects are interesting; the
pattern across them is what the audience takes away.

## Status columns

Two headed columns, green and red, same number of rows each, one claim per row. The
symmetry is the argument: an equal-length red column reads as candour, a short one reads as
spin.

This is the slide that gets cut when the clock is tight. Protect it.

## Asks grid

Dark background, six boxed questions in two columns (each ~6.03 wide, 1.58 tall, 1.72
pitch), each with a coloured left edge, a numeral, a question as the heading, and three or
four lines of context naming a file and a line.

Group them by audience — the dependency authors, the domain experts, everyone — and make
each one answerable. "Thoughts?" is not an ask; "should this handler catch `Exception` and
fail the one task rather than the sweep?" is.
