# The palette, and how it was arrived at

Every figure of a campaign comparison lives next to the others, so a colour has to mean the
same thing across a report and ideally across reports. This file records what the four
slots mean, the validator evidence that they are legible, and the candidates that were
rejected — so the next person to need a fifth hue starts from the misses rather than
rediscovering them.

## The accepted palette

| Slot | Hex | cmap | Marker | Meaning |
|---|---|---|---|---|
| blue | `#2176c7` | `Blues` | `o` | best performance — what the report argues for |
| ochre | `#ae8a16` | `YlOrBr` | `s` | lower performance |
| brick | `#9e3f1c` | `OrRd` | `^` | lowest performance |
| magenta | `#993284` | `RdPu` | `X` | did not complete |

Blue is inherited: in the group's campaign plot scripts (`analysis/style.py`) the blue /
`Blues` slot means IMPRESS and orange / `Oranges` means the non-adaptive reference — a
comparison between *pipelines*. A performance report compares *allocations of one pipeline*,
so the blue slot is re-pointed at the best-performing allocation, which keeps the
association a reader already has, and the other three slots are new.

The tiers also carry a marker and a colormap each. A figure that needs a density or a
sequential fill uses the run's cmap; one that needs a scatter uses its marker. Both exist so
that a figure can encode identity twice without inventing anything.

```
$ node <dataviz>/scripts/validate_palette.js "#2176c7,#ae8a16,#9e3f1c,#993284" \
      --mode light --surface "#ffffff" --pairs all

  [PASS] Lightness band         all 4 inside L 0.43–0.77
  [PASS] Chroma floor           all 4 >= 0.1
  [PASS] CVD separation         worst all-pairs #993284↔#2176c7 ΔE 10.9 (deutan) · tritan 4.7
  [PASS] Normal-vision floor    worst all-pairs #993284↔#9e3f1c ΔE 15.8 (normal)
  [PASS] Contrast vs surface    all 4 >= 3:1

  → ALL CHECKS PASS
```

Two things to note in that report. Deutan separation on the worst pair is 10.9 against a
target of 8, with room to spare. **Tritan separation on the same pair is 4.7**, below the
floor — which is why the house rules require every series to carry a direct label or its own
line style. Identity in these figures never rests on hue alone, so the tritan number is a
reason for the labelling rule rather than a reason to re-step the palette.

All four clear 3:1 contrast against white, so no slot depends on a label merely to be *seen*.

## Non-categorical slots

| Name | Hex | Use |
|---|---|---|
| `NEUTRAL_SERIES` | `#5b5b55` | a measure that is not one of the compared entities — e.g. a manager-occupancy trace in a panel whose colour is already spent on the run |
| `CONTRAST["before"]` | `#5b5b55` | a two-state contrast: full-run, before, confounded |
| `CONTRAST["after"]` | `#117a79` | the other state: equal-window, after, controlled |

These are not categorical slots and are not validated as such — `#5b5b55` is near-neutral and
fails the categorical chroma floor by design. The pair separates on chroma as well as hue, so
it survives every CVD simulation, and it always ships with a legend. Keeping them outside
`RUN_STYLES` matters: on a figure that is already comparing two runs' distributions, a run
hue used for a *state* reads as one of those runs.

## Candidates that were rejected

Run against the same white surface with `--pairs all`.

**`#2176c7, #a6761d, #8c5ab8, #b03a3a`** — blue, ochre, violet, muted red.

```
  [FAIL] CVD separation      worst #8c5ab8↔#2176c7 ΔE 3.9 (deutan) · tritan 9.0
  [FAIL] Normal-vision floor worst #8c5ab8↔#2176c7 ΔE 13.7 (normal)
```

A mid violet sits too near blue to survive deutan, and it is not safe for full-colour
readers either. **Any violet near `#8c5ab8` is out while blue holds the first slot** — push
it toward magenta (`#993284`) and the deutan distance nearly triples.

**`#2176c7, #c99a12, #a34725, #9c3587`** — the accepted palette one step lighter.

```
  [PASS] CVD separation      worst #9c3587↔#2176c7 ΔE 10.5 (deutan)
  [WARN] Contrast vs surface below 3:1: [["#c99a12", 2.59]]
```

Passes, but the gold falls under 3:1 on white. A WARN here is not dismissable — it obligates
visible labels or a table view — and darkening the gold to `#ae8a16` clears it outright, so
there was no reason to take the obligation.

**`#2176c7, #cc9a06, #b0532a, #8f3d6b`** — a plum fourth slot instead of magenta.

```
  [FAIL] Normal-vision floor worst #8f3d6b↔#b0532a ΔE 13.6 (normal)
```

Plum against brick is the failure mode to watch at the dark end: two dark warm-ish hues read
as one. Separate them by lightness or by chroma, not by hue alone.

**`#2176c7, #a8800d, #a34725, #9c3587`** — gold darkened too far.

```
  [FAIL] Normal-vision floor worst #a34725↔#a8800d ΔE 14.8 (normal)
```

The mirror of the previous miss, and the reason the accepted gold is `#ae8a16` rather than
anything darker: pushing it down for contrast walks it into the brick. The accepted palette
is the point where contrast and separation are both satisfied, and it is narrow — moving any
slot by much breaks one of the two.

## When a project needs a fifth run

Do not pick one by eye, and do not let a fallback list generate one. Either:

1. **Fold it in.** Two runs that differ in something the figure is not about share a hue and
   separate by line style, with both direct-labelled.
2. **Facet it.** One panel per run, which is usually clearer than five series anyway.
3. **Re-step the palette.** Run the validator with `--pairs all` on the full five and fix
   every FAIL. Expect to move more than the new slot: five categorical hues on a white
   surface inside the L 0.43–0.77 band is a tight fit, and the magenta-blue deutan pair is
   already the binding constraint at four.

Whichever you choose, re-run the validator and paste the report into this file, so the next
change starts from evidence.
