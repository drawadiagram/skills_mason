# Templates

`<...>` is a placeholder. Item IDs, SHAs and job IDs below are examples.

## Episode doc — plans/YYYY-MM-DD-<slug>-episode.md

`propose_episode.py --doc N` prints this pre-filled with the items, the paths it resolved and
the items it dropped.

````markdown
# Episode: <the sentence — one clause, imperative, no "and">

**Status:** planned · **Items:** 11, 12 · **Kind:** bug · **Ladder:** bug,feature,other
**Budget:** 1 module / 4 files <· **Over a rail:** 4 files because …>

## Scope

| In scope | Why it is here |
|---|---|
| `skills/<name>/scripts/<file>.js` | item 11: the helper that drops the mark |
| `skills/<name>/SKILL.md` | item 11: the rule the helper is supposed to enforce |

Modules: `skills/<name>`

## Items

- **11** [bug; high] <one line, with its evidence> ([plan](2026-10-12-<slug>.md#i11))
- **12** [bug; high] <one line, with its evidence> ([plan](2026-10-12-<slug>.md#i12))

## Excluded, deliberately

- **6** — same module, but it is a feature, not a defect: it would break the sentence.
- **7** — would take the episode to 4 modules / 7 files.
- **F1** — 12 depends on it; it lands first, in its own episode.
- <anything a reviewer might expect to see here, and why it is not>

## Test

| Check | Pass |
|---|---|
| <the command or run that exercises the change> | <criterion, written before running it> |

## Commit message

```text
<subject = the sentence>

<Why, with the evidence each item cites.>

<What changed, module by module.>

Left out of this commit: <items and the reason>.
Plan: plans/<this doc>.md
```

## Result

<After committing: the SHA, what the gates said, what was surprising. Then update the BACKLOG
rows to `fixed in <sha>, not yet confirmed`.>
````

## Commit messages

Subject: imperative, ~70 characters, no trailing period, no ticket prefix unless the project
uses one. Body wrapped at 72. Add the project's trailers.

**Defect episode** — the symptom is the why, so quote it:

```text
Make the anchor checker refuse the wrong input shape

check_anchors.py read {"anchors": [...]} as an array and reported
"MISSING r (t)", 0/2 verified, for 9 correct anchors (items 11, 12).
A checker that invents failures is worse than none: the author spends
the afternoon fixing anchors that were already right.

- scripts/check_anchors.py: validate the top-level shape, exit 2 with
  the expected form when it is a mapping.
- scripts/deck_lib.js: read o.fidelity in code(), warn when absent.
- SKILL.md: say what the checker accepts.

Left out of this commit: item 6 (a feature in the same module),
item 7 (would double the file count).
Plan: plans/2026-10-13-loud-failures-episode.md
```

**Planned-feature episode** — the why is the plan's evidence, and the criteria go in so the
confirming run can be matched to them later:

```text
Make an export self-sufficient off a login node

Packing an export did not require a sacct snapshot, and inventory read
live sacct only, so every allocation column was blank off-cluster even
when the archive carried the numbers (items 2, 1; job 12345678).
sacct records age out, so the archive is the only copy that survives.

- scripts/package_export.sh: refuse to pack without sacct.json, --no-sacct
  to override.
- scripts/inventory.sh: read $ROOT/sacct.json when sacct is absent.

Acceptance: re-inventory the 2026-10-08 archive off-cluster; every run
shows allocation hours; no row says "sacct unavailable".

Left out of this commit: item 4 (prose, lands with 3 and 10).
Plan: plans/2026-10-13-export-self-sufficient-episode.md
```

**Prose or record-keeping episode** — short, and still says what it rests on:

```text
Say the same thing about evidence in all three skills

Three skills asked for evidence in three different strengths, and the
weakest ("verify the table against known facts") is the one that let a
wrong number through on 2026-10-12 (items 3, 4, 10).

Uniform edit, one paragraph per SKILL.md, no code touched.
Plan: plans/2026-10-13-evidence-wording-episode.md
```

**Mechanical commit** — names the command, and nothing else travels with it:

```text
Rename run_dir to run_root across the scripts

Mechanical, no behaviour change:
  rg -l '\brun_dir\b' | xargs sed -i 's/\brun_dir\b/run_root/g'
Reviewed by reading scripts/inventory.sh; the other 11 files are the
same substitution. The fix that needed the rename is the next commit.
```

**Stack member** — says where it sits and what it promises:

```text
Extract the manifest reader (1/4)

Prep for the self-sufficient export. No behaviour change: the reader
moves out of inventory.sh unchanged so commit 2 can call it from
package_export.sh.

After this commit: read_manifest() is the only path that parses
manifest.json; nothing calls it yet.
Plan: plans/2026-10-13-export-stack.md#c1
```

## How an episode shows up in BACKLOG.md

The tracker stays as `plans-backlog` defines it. Two small additions:

- In **Order**, name the episode instead of listing items: `**Episode 1 — items 11, 12:**
  make the deck tooling fail loudly ([doc](2026-10-13-loud-failures-episode.md)). Then …`
- In each row's **Status**, when the commit lands:
  `fixed in `abc1234` (episode 1), not yet confirmed`.

Nothing closes at commit time. Items close when a run or test confirms them, with the
evidence, in the Closed section — that rule belongs to `plans-backlog` and this skill does not
change it.

An item excluded from an episode keeps its row untouched. If the episode's commit makes an
excluded item unnecessary, say so in the Closed section with the SHA; do not delete the row.
