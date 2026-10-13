---
name: commit-episode-plan
description: Plan work in commit-sized episodes — choose the set of backlog or plan items that fits in one commit a reviewer can read in ten minutes, write down what the episode deliberately excludes, keep the diff inside that scope, and commit it with a message that carries the reasoning. Use this whenever the user asks what to do next from a backlog or plan, what should go in this commit, how to scope, group or split a change, whether a commit, branch or working tree has grown too big, how to break a feature into commits, which items to pick up next, or asks for the commit message for planned work — even if they never say "episode". Also use it before starting work from a plans/BACKLOG.md, so the selection is made against the commit budget rather than discovered at commit time.
---

# Commit-sized planning

The commit is the unit another person reads. Not the plan, not the branch, not the PR
description — the commit, months later, in `git log -p` or a bisect, with no one around to
explain it. A reader gets about ten minutes before they start skimming and approving on
trust.

So the commit budget is an input to planning, not a discovery at commit time. Three failures
come from planning without it:

- **Two themes in one commit.** The reviewer has to hold two sets of invariants at once, and
  `git revert` can no longer separate them. One of the two is always the one that broke.
- **A plan sized to the feature.** The feature is "the export is self-sufficient"; the commit
  is 30 files; the review is a thumbs-up. Nothing was reviewed, and everyone involved knows it.
- **Scope with no statement of what it excludes.** A reader cannot tell a deliberate boundary
  from an oversight. Absent that statement they assume oversight, and re-raise what you
  already decided.

The unit this skill plans in is the **episode**: one commit's worth of items that share one
unifying feature — a defect, a feature, a documented decision — and fit inside the budget.

## Requirements

`git` and Python 3 standard library. Nothing to install.

| Script | Use for |
|---|---|
| `scripts/propose_episode.py [PLANS_DIR…] [--ladder …] [--count N] [--doc N] [--json]` | Reads a `plans/BACKLOG.md`, follows each open row's Doc link (honouring `#anchor`), extracts and resolves the file paths each item cites, infers bug / feature / other, and groups items that share a module and a kind into episodes inside the budget. Prints the items it **dropped** from each episode and why, which is the first draft of the doc's Excluded section. `--doc N` prints the episode doc skeleton. Read-only |

## The episode

Three tests. An episode has to pass all three.

**The sentence.** Write the commit subject *before* the work: one clause, imperative, no
"and", no comma-spliced list. "Make `code-walk-deck` fail loudly instead of silently" is a
sentence and can cover two separate defects. "Fix the anchor checker and add a bar helper" is
not a sentence, it is a bag — two episodes. "Fix several issues in X" is a bag pretending to
be a sentence.

**The budget.** Guide rails, not caps. Crossing one is a signal to stop and justify in the
doc, or split:

| Dimension | Guide rail |
|---|---|
| Modules (components, top-level dirs) | 1, up to 3 |
| Files | ~5 |
| Net changed lines, excluding mechanical | ~400 |
| New ideas the reader must learn | 1 |

**The ten-minute read.** Hand someone the subject line and `git show --stat`; they should be
able to say what changed, why, and one way it could be wrong. If answering "what changed"
needs a third file opened, the commit is too wide. `references/sizing.md` has this in
operational form, plus the carve-out for mechanical changes — a uniform rename across 40
files is fine, in its own commit, because the reader verifies one instance and the command.

## 1. Fix the ladder before looking at items

The ladder is the order in which kinds of work get picked up. **Ask the user for theirs.**
Default when they have no preference:

1. **Known bugs with evidence.** The cost is already being paid, the defect bounds the scope,
   and the defect names the test — the cheapest commit to review that exists.
2. **Rigorously planned features.** A plan doc with a Change and a pass-criteria Test written
   before the run. The commit boundary is already drawn, in writing.
3. **Everything else** — prose, record-keeping, cleanups, nice-to-haves. Last not because
   they do not matter but because their scope is elastic, and elastic scope is what eats a
   commit.

Record the ladder in the episode doc. A ladder that changes silently between episodes makes
the order of the history inexplicable six weeks later.

Three things legitimately jump the ladder, and each is worth one line in the doc: a deadline
or release; a bug whose fix is blocked behind planned work; and a cheap item sitting in a
module you are already opening — but only if it still fits the sentence.

## 2. Propose episodes from the backlog

```bash
python3 -I <this skill>/scripts/propose_episode.py plans                  # next 3 episodes
python3 -I <this skill>/scripts/propose_episode.py plans --ladder order    # follow the BACKLOG's Order section
python3 -I <this skill>/scripts/propose_episode.py plans --max-files 8     # a looser budget, deliberately
```

Read the output as a measurement, not a decision. It measures size and adjacency; it cannot
judge whether two items share one sentence, and every kind it marks `(inferred)` was guessed
from wording. Two outputs matter as much as the grouping:

- **`dropped`** — an adjacent item left out, with the reason. This is the Excluded section.
- **`warn … names no file`** — the item's plan doc cites no path the script could place, so
  nothing can be grouped with it. Fix the doc (cite paths repo-relative) before planning
  around it. An item nobody can locate is an item nobody can scope.

With no backlog, skip to section 8.

## 3. Choose the episode

- **Seed:** the highest item under the ladder.
- **Companions:** items sharing a module with the seed, in ladder order, while the budget
  holds. Two items in one file are cheaper together than apart — one re-read, one test pass.
- **Veto:** an item that breaks the sentence is out, whatever it shares. Same module is not
  same theme.
- **Dependencies:** never select an item whose plan says it depends on an open item that is
  not in this episode. The script warns; believe it.

Then re-check the kinds the script inferred, against the plan docs, by hand.

## 4. Write the episode doc

`plans/YYYY-MM-DD-<slug>-episode.md`, skeleton from `--doc N`, template and commit-message
shapes in `references/templates.md`. It holds the sentence, the ladder, the item IDs, a
Scope table of in-scope paths, **Excluded, deliberately**, the Test, and the message. It is
short — a page — and it is written before the work, because its whole value is being a
boundary you agreed to before you were inside the code.

The Excluded section is the part that makes the rest trustworthy. Name each adjacent item
dropped and why: budget, theme, or dependency.

Link it from the BACKLOG per the `plans-backlog` skill, which owns the tracker, the status
vocabulary and the evidence rules. This skill only decides what goes in one commit.

## 5. Work inside the boundary

Check the boundary while working, not at the end:

```bash
git status --porcelain
git diff --stat          # against the doc's Scope table
```

When the diff escapes the scope there are exactly three honest responses:

1. **Shrink.** Revert the extra, open a backlog item for it.
2. **Split.** Keep the work, commit it separately, in dependency order (the prep commit
   first).
3. **Re-plan.** The sentence was wrong. Rewrite the doc's sentence and Scope, and say in the
   doc that the episode grew and what forced it.

The dishonest fourth is to keep going and let the commit discover its own size. A bug found
while fixing another bug is a new backlog item, not an addition to this commit, unless it is
in the same function — discoveries are the main source of sprawl.

## 6. Commit

- **One episode, one commit.** A mechanical part (rename, reformat, regenerated file) splits
  off into its own commit, with the command that produced it in the message. A refactor plus
  a behaviour change is two commits, refactor first, because "no behaviour change" is cheap
  to verify only when it is alone.
- **Every commit leaves the tree working.** In a stack, each commit passes the project's
  checks, not only the tip.
- **Stage precisely.** Explicit paths from the Scope table, or `git add -p`. Never
  `git add -A` when the tree holds more than the episode. Then read
  `git diff --cached --stat` the way the reviewer will.
- **Run the project's gates first.** Whatever its `CLAUDE.md` or `CONTRIBUTING` names. In
  this collection that is `bash -n` / `python3 -m py_compile` on changed scripts,
  `plans-backlog`'s `check_backlog.py`, the `README.md` skills table when a skill is added or
  renamed, and `repo-sensitive-scan`'s `scan_sensitive.py --staged`.
- **Message:** the subject is the sentence you already wrote. Then why, with the evidence
  each item cites; what changed, module by module; a `Left out:` line naming the items that
  were adjacent and excluded; the plan doc path; and the project's trailers.

## 7. Record the result

Per `plans-backlog`: rows become `fixed in <sha>, not yet confirmed`, and close only when a
run or test confirms them. Add the SHA and what the gates said to the episode doc's Result.

Check that every item the episode excluded is still open. A commit that quietly absorbs an
item's row without doing the work is how a backlog starts lying.

## 8. Without a backlog, and when nothing fits

**Ad-hoc work.** Do sections 3–7 anyway, from memory instead of a tracker: write the sentence
and the in-scope paths first — two minutes — then verify the diff against them and put the
excluded list in the commit message. No doc is needed for a single commit nobody planned.

**Exploration.** When the sentence is genuinely unknowable up front, timebox the explore,
treat that tree as throwaway, and plan episodes *afterwards* by splitting what you learned
out of the dirty tree with `git add -p`. Plan from what the code turned out to be, not from
what you guessed.

**A feature that cannot fit** becomes a stack: ordered commits, each independently reviewable
and green, with a named interface between them, written as one doc with a section per commit.
The budget applies to each commit, not to the stack. Past about five commits the feature wants
a design doc and a PR per group — see `references/sizing.md`.

## References

- `references/sizing.md` — the budgets and why those numbers, the ten-minute read in
  operational form, mechanical vs judgment changes, worked examples from a real backlog, the
  escape responses, and how to split a stack.
- `references/templates.md` — the episode doc, commit-message shapes per kind, and how an
  episode shows up in `BACKLOG.md`.
