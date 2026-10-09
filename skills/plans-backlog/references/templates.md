# Templates

Copy and fill in. `<...>` is a placeholder. Job IDs, commits and paths below are examples.

## plans/BACKLOG.md

```markdown
# <Project or component> — backlog tracker

<One sentence: what this tracker covers.> One line per item; details live in the linked doc.
Keep `Status` current, and delete rows only once the fix is merged **and** a run confirms it.

<If there are other scopes:> Framework-level items are tracked in
[plans/BACKLOG.md](../../plans/BACKLOG.md); items 2 and 20 below have counterparts there (F5, F4).

Source of most entries: <job 12345678 (8 nodes, 12 h, TIMEOUT)>; artifacts at `<archive path>`.

| # | Item | Severity | Status | Doc |
|---|---|---|---|---|
| 1 | <Symptom, one line, with evidence: job `12345678` lost 64 GPU-h to X> | high | open | [<slug>](2026-01-01-<slug>.md) |
| 2 | <...> | medium | fixed in `abc1234`, not yet confirmed on a run | [<slug>](...) |
| 3 | <...> | low | open, needs decision | [<slug>](...) |

## Order

1. <item> first: <why — it blocks X / it is the cheapest win>.
2. <...>

## Closed

- **4**: closed by job `12345679` (<date>): <the measured result that confirms it>. Doc: [<slug>](...).

## Conventions

- Cite the job ID and artifact path behind every claim.
- "needs decision" means the data is in hand and a human has to choose.
```

For a tiered work plan (several PRs), replace `Severity` with `Tier` and define it in the
header (e.g. "Tier = impact × reach ÷ effort; 1 is highest").

## Single-topic plan doc — plans/YYYY-MM-DD-<slug>.md

```markdown
# <What is wrong or what is being built>

**Severity:** <high> · **Status:** <open, design only> · **Evidence:** job `12345678` · **BACKLOG:** <N>

## Symptom
<What was observed, with numbers and the job they came from. A small table is often clearest.>

## Root cause
<Why. Cite `file:line` and the measurement that rules out the alternatives.>

## Change
<What will change, where, and anything it must preserve.>

## Test
<How it will be checked. For a run, a criteria table written before submitting:>

| Check | Pass |
|---|---|
| <throughput> | <within noise of job 12345678 (N/h)> |
| <failures> | <0 apart from the injected one> |

## Result
<Added after the run: job ID, measured values against each criterion, surprises.>
```

## Multi-item doc (one change set)

```markdown
# <Change set name> (Tier 2): <short list>

**Status:** open, design only · **Items:** F2–F7 · **Depends on:** <F1>

<a id="f2"></a>
## F2 — <title>

**Evidence.** <...>
**Change.** <...>
**Test.** <...>

<a id="f3"></a>
## F3 — <title>
...
```

Link rows to `2026-01-01-<slug>.md#f2`. The linter checks that the anchor exists.

## Acceptance-run doc

```markdown
# F1 — <change> acceptance run on <cluster>

**Status:** <submitted YYYY-MM-DD as job `12345678` (<partition>, <nodes>, <time>, from `abc1234`)> · **Blocks:** <merging PR 1>

## Why
<What the offline tests did not cover and why a real run is needed.>

## Run
- Shape: <nodes, time, pipelines>, matching reference job `<id>`.
- Injected failure: <exactly what, and why it reaches the path under test>. Restored by <dependent job / step>.

## Pass criteria
| Check | Pass |
|---|---|

## After
Record the job ID and results here and in the CLAUDE.md revision row, then close F1.
```

## Upstream issue — plans/upstream/<component>-<issue>.md

```markdown
# <component>: <one-line defect>

**Component:** <name version> (`<file>`) · **Severity:** <...> · **Status:** <diagnosed, not reported upstream>
**Evidence:** <job / trace path>

## What we saw
<Observed behaviour with data.>

## Cause
<`file:line` in the dependency's code; the call path.>

## Fix
<The minimal change upstream.>

## Impact on us
<What it costs this project, and any local workaround.>
```

## CLAUDE.md revision row

```markdown
| YYYY-MM-DD | <commit or —> | **<Headline.>** <What changed, the evidence, and where the details are: [<slug>](plans/<doc>.md).> **Not yet run on <cluster>.** |
```
