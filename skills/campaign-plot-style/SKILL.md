---
name: campaign-plot-style
description: Draw matplotlib figures for a protein-design or HPC campaign in this group's house style — the performance-tier palette where the IMPRESS blue slot marks the best-performing configuration and lower-performing ones get their own validated hues, a type scale and recessive grid shared with the campaign plot scripts, and the rules for mean +/- 2 sigma bands, log axes, direct labels and per-run colour identity. Use this whenever making, restyling or reviewing a plot, chart or figure for a campaign comparison, a scaling or throughput study, a design funnel, an occupancy or utilisation trace, or a report or deck that carries such figures — including when the user only says "make a figure", "plot X vs time", "match the other plots", or "update the figures to the new colours". Not for one-off exploratory plots that nobody else will read.
---

# Campaign plot style

A figure in a campaign report is read next to the other figures in that report, and often
next to figures from a different study six months old. What makes the set readable is not
any one chart being pretty — it is that a colour means the same thing everywhere, and that
the reader can tell which claims the figure is actually licensed to make.

This skill is the house style for those figures: the palette with its semantics, the type
scale and axis furniture, and the handful of rules that are easy to break by accident.

## Requirements

`matplotlib`, `numpy` and `pandas` — the thing the skill is about. `node` is optional and
used once, to re-run the `dataviz` palette validator if you change a colour; without it,
do not change colours.

## Start here

1. **Load the `dataviz` skill first** if it is available. This skill is a design-system
   instance; `dataviz` is the method. Everything below supplies its parameters.
2. **Copy the style module into the project**, rather than importing from this skill:

   ```sh
   python3 scripts/new_plot_style.py --out <project>/figures/plot_style.py
   ```

   It writes a self-contained `plot_style.py` with the palette, rcParams and helpers, plus
   the comments explaining where each convention came from. A project that keeps its own
   copy stays reproducible after this skill moves; one that imports from a skill directory
   does not. Edit the copy — add the project's own runs to `RUN_STYLES` — and leave the
   conventions alone.
3. **Every figure script imports that module.** Including scripts written earlier: if a
   project has figures predating the module, repoint them at it (see *Restyling an existing
   set* below) rather than leaving two palettes in one report.

## The palette, and what each slot means

| Slot | Hex | cmap | Meaning |
|---|---|---|---|
| IMPRESS blue | `#2176c7` | `Blues` | **best performance** — the configuration the report is arguing for |
| ochre | `#ae8a16` | `YlOrBr` | lower performance |
| brick | `#9e3f1c` | `OrRd` | lowest performance |
| magenta | `#993284` | `RdPu` | did not complete — a run kept as evidence, never as a rate |
| neutral | `#5b5b55` | — | a measure that is not one of the compared entities |
| contrast pair | `#5b5b55` / `#117a79` | — | a two-state contrast: before/after, full-run vs equal-window |

The blue slot is inherited from the group's campaign scripts, where it means "IMPRESS" in a
comparison against a non-adaptive reference. Re-pointing it at the best-performing
configuration keeps the association a reader already has — blue is the thing that worked —
while freeing the other slots for a comparison between allocations of the same pipeline.

**Colour follows the entity, never its rank on the current axis.** Assign a hue to a run
once and keep it across every figure in the report. Campaign comparisons routinely invert:
per pipeline-hour an unpacked allocation wins, per GPU-hour the packed one wins by 5x. If
the colours move with the ranking, the inversion looks like an error instead of the result.

**Do not add a fifth hue by hand.** `style_for()` raises on an unknown run for that reason.
A fifth run means re-validating:

```sh
node <dataviz>/scripts/validate_palette.js "<hex,hex,...>" \
    --mode light --surface "#ffffff" --pairs all
```

Fix every FAIL before using the result. The four slots above pass on all pairs: worst
separation is magenta-blue at deutan dE 10.9 against a target of 8, and all four clear 3:1
contrast. `references/palette.md` has the full report and the near misses that were rejected.

## Axis furniture

`RCPARAMS` in the module carries all of it; `apply_rcparams()` installs it. In summary:
`font.size` 14 with `x-large` labels, a `#DCD7CC` grid at 0.6 width drawn **under** the data
(`axes.axisbelow`), top and right spines dropped, a framed legend, white surface, 150 dpi.

Mark geometry: 1.8 pt lines, round caps, white-faced markers with a 1.2 pt coloured edge,
bands at alpha 0.15. Z-order is fixed — grid 0, bands 2, bars 3, lines 6, annotations 7 —
so a band never covers a line and an annotation never hides under a bar.

## Rules that are easy to break

**One y-axis.** Never two scales on one panel. Two measures of different magnitude that are
genuinely the same unit (two occupancies, both percentages) go on **one log axis** and the
caption says so; two measures of different units go in two panels.

**A log axis needs its zeros handled.** A zero is not drawable on one, and left in the series
it renders as a spike to the floor that reads as a crash. Lift zeros out of the line, tick
them along the axis floor with their own legend entry, and say in the caption what a tick
means. A bin with no data at all is `NaN` — a gap — not a zero.

**`+/- 2 sigma` is population spread, not uncertainty.** Say which in the caption. With 8 to
32 pipelines the standard error is three to six times narrower than the standard deviation,
so a band silently read as a confidence interval makes runs look far more separated than
they are. Clip a count's band at zero.

**Direct-label every series,** on the mark, in the series' own colour, in addition to the
legend. Identity then never rests on hue, which is what makes the tritan-weak pairs in any
four-colour palette acceptable.

**Cut every cross-run time series to one equal window** — `WINDOW_MIN` in the module — and
say so in the caption. Runs rarely share a wall clock, and a 4-hour run drawn to its own
end is a deeper search, not a different allocation: its slope stops being comparable to a
1-hour run's, and the reader is invited to compare depth while thinking they are comparing
allocations. Pick the window once, from the shortest run, and use it everywhere so the
figures agree with the statistics.

Two things that follow. **Drop out-of-window points, never clip them into the last bin** —
clipping piles three hours of a long run onto minute 60 and draws a vertical spike that
reads as a burst of work. And **a single-run figure is not a cross-run comparison**: an
anatomy of one run keeps its full span, because the window would delete the only thing it
shows. Say which figures were exempted and why, so the exemption is a decision on the
record rather than an inconsistency.

**Explicit margins beat `tight_layout`** for any figure with a suptitle, a figure legend and
a footer caption — four claims on the margins and it resolves them by overlapping the
y-labels. Set `subplots_adjust` by hand and save without a tight bounding box. `tight_layout`
plus `bbox_inches="tight"` is right for a single-axes figure, and `SAVE_TIGHT` is there for
it. Note that `bbox_inches=None` falls back to the rcParam rather than disabling it, which
is why the module does not set `savefig.bbox`.

**One y-label per stack of panels** sharing a measure. Three of them at this type scale run
into each other.

## Render it and look at it

The palette validator checks colour, not layout, and matplotlib places text exactly where it
is told and says nothing when two labels overlap. Save the PNG and **open it**. In the
session this style came from, every figure had at least one collision on first render:
legends over data, captions stretching the canvas instead of wrapping, annotations landing on
the trace they annotate, stacked y-labels touching.

Budget a fix pass. It is not optional and it is where the real bugs are.

## Restyling an existing set

When a project's figures predate the module, do not re-tune every layout by hand. Point the
old script at the module, then scale the geometry that is expressed in points — `figsize`,
every explicit `fontsize`, marker sizes, and `xytext` offsets — by the ratio of the new type
scale to the old one. Positions in data or axes coordinates are invariant to that factor, so
a layout tuned at the old scale comes out correct at the new one. Then render and look,
because the things that are not invariant (a legend frame that was off and is now on, a
heavier grid) still move.

## Reference files

- `references/palette.md` — the validator reports for the accepted palette, the candidates
  that failed, and what to do when a project needs a fifth hue.

## Scripts

```sh
python3 scripts/new_plot_style.py --out <project>/figures/plot_style.py
python3 scripts/new_plot_style.py --out <path> --force   # overwrite an existing copy
```
