# Slide and figure archetypes

The shapes that recur in code-walk decks, with geometry that fits a 13.333 × 7.5 inch page
at `M = 0.5` margins. Numbers here are starting points that have survived contact with a
projector, not a grid to obey.

Usable vertical space below a title with a kicker is roughly **y = 1.45 → 7.0**, with the
footer at 7.1.

## Contents

- [Title](#title)
- [What it does / what it is not](#what-it-does--what-it-is-not)
- [The framing slide](#the-framing-slide)
- [Dimension divider](#dimension-divider)
- [The constraint slide](#the-constraint-slide)
- [Two-lane process diagram](#two-lane-process-diagram)
- [Layer map with forbidden edges](#layer-map-with-forbidden-edges)
- [Typed-hop strip](#typed-hop-strip)
- [Gate or rule table](#gate-or-rule-table)
- [Code slide](#code-slide)
- [Measured-run bars](#measured-run-bars)
- [Defect ledger](#defect-ledger)
- [Measured and not measured](#measured-and-not-measured)
- [Status columns](#status-columns)
- [Status columns by dimension](#status-columns-by-dimension)
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

## The framing slide

Three columns at x = `M + i*4.28`, each 4.0 wide: a headed band in the column's colour (y 1.5,
h 0.42), a tinted definition panel under it (h ~1.0), then three evidence rows at 0.78 pitch,
alternating fill. Close with a full-width dark band at y ~5.8, h ~1.05.

The columns are the three dimensions — functionality, performance, usability — with the definition
you are using for each, because "performance" means four different things in a room of four people.
The dark band is the slide's work: **name the weak column here**, with the reason, in the first three
minutes. Everything the deck later concedes becomes a promise kept rather than an admission
extracted.

Caption each column with what it answers. Caption the weak one with "what it answers · and what it
does not", which is a half-second of honesty for free.

## Dimension divider

`deck_lib.js::divider()`. Dark slide: an `ACT n OF 3` eyebrow at y 0.85, the dimension in ~46pt
serif at y 1.2, the definition in italic at y 2.3, three claim rows at 0.86 pitch from y 3.2 (each a
0.06-wide accent rule, a bold heading, one line of evidence under it), and a red-bordered band at
y 6.1 holding the act's weakest claim.

Three claims is the budget — a fourth pushes the caveat band into the footer, and a divider that
needs four claims is a content slide wearing a divider's clothes. Keep all three dividers
geometrically identical: three identical dividers read as a structure, three artful ones read as
three unrelated slides.

Twenty seconds of speech each. That is the whole cost, and it is why they are the last thing to cut.

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

## Measured and not measured

The slide that makes a performance act honest. Left half: the one real figure, with its axes
labelled in the units that matter and any declared limits drawn as lines. Right half: two stacked
cards — `panel` fill, "Measured, and in this deck"; `failTint` fill with a `fail` heading, "Not
measured — so not claimed". Four or five rows each. Close with a dark band naming the place where
the dimension stops being a systems question.

Rules that make it work:

- **Every row on the left names where the number came from**, and the footer names the host, the
  date and whether anything was simulated. A measurement taken on the presenter's laptop is still a
  measurement; an unlabelled one is a liability.
- **The right card is written as refusals, not apologies.** "No serial baseline, so nothing above
  divides into a speedup" is a fact about the evidence. "We did not have time to benchmark" is an
  excuse, and invites the follow-up.
- If a declared limit and the real cost are in different units — a cap on raw bytes against a cost
  paid in compressed ones — that asymmetry is usually the most interesting thing on the slide. Draw
  both.

## Status columns

Two headed columns, green and red, same number of rows each, one claim per row. The
symmetry is the argument: an equal-length red column reads as candour, a short one reads as
spin.

This is the slide that gets cut when the clock is tight. Protect it.

## Status columns by dimension

The same slide in three columns of two blocks instead of two columns of one. Per dimension (x =
`M + i*4.28`, w 4.0): a headed band in the dimension's colour, a green band with three rows, a red
band with three rows. Rows at 0.6 pitch, h 0.58, heading 10pt over a 8.5pt line — anything taller
collides with the closing paragraph, which is the failure this layout fails into.

Three rows each is not a formatting choice. It forces you to decide which three things actually run
and which three do not, per dimension, and an audience can see at a glance whether your candour is
evenly distributed or concentrated in the dimension you were least invested in.

## Asks grid

Dark background, six boxed questions in two columns (each ~6.03 wide, 1.58 tall, 1.72
pitch), each with a coloured left edge, a numeral, a question as the heading, and three or
four lines of context naming a file and a line.

Group them by audience — the dependency authors, the domain experts, everyone — or, better when the
deck has three acts, **by what each finding costs**: one column for the ones that produce a wrong
answer or burn real time, one for the ones paid by whoever adopts the stack next. Tag each with its
dimension. Grouping this way answers "why should I care about number six" before it is asked, and it
lets you keep the original numbering while changing the order, which matters because the numbers are
cited in the companion files.

Make each one answerable. "Thoughts?" is not an ask; "should this handler catch `Exception` and
fail the one task rather than the sweep?" is.

With eight items in two columns of four, use a ~1.0 pitch and start at y ~1.84 if the columns have
headings; the question box at the foot wants y ~5.86, and the collision between the last item and
that box is the one this layout actually fails into.
