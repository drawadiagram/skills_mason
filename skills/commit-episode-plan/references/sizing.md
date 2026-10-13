# Sizing an episode

## The budget, and why those numbers

| Dimension | Guide rail | Why this number |
|---|---|---|
| Modules | 1, up to 3 | A reviewer holds one component's invariants in their head at a time. The second module costs a context switch; the fourth means nobody is checking the interfaces between them |
| Files | ~5 | Past five files a reviewer stops reading the diff in order and starts spot-checking |
| Net changed lines | ~400, mechanical excluded | Careful reading runs at roughly 200 lines in ten minutes. 400 lines of diff is ~200 lines of new code plus its context |
| New ideas | 1 | A commit that introduces two new concepts needs a design doc, and the reviewer will accept the second one on the strength of the first |

These are guide rails. Crossing one is not a veto, it is a prompt for three questions:

1. **Is this one sentence?** If yes, a wide commit may be right — see the mechanical carve-out
   below. If no, the budget is not the problem, the selection is.
2. **Can the extra module land separately and leave the tree working?** If yes, it is a
   separate commit, probably before this one.
3. **Would I want to read this?** The honest answer is usually already known before the
   question is finished.

Record the answer in the episode doc. A justified 7-file commit is fine; an unexamined one is
how 30-file commits happen.

## The ten-minute read, operationally

Give someone the subject line and `git show --stat`, then ask for three things:

- **What changed.** If they have to open a third file to answer, the commit is too wide.
- **Why.** If the message does not say, the commit is unreviewable at any size. Evidence —
  the job ID, the failing output, the measurement — belongs in the message, not only the plan.
- **One way it could be wrong.** If they cannot name one, they have not understood it, and
  approval means nothing. This is the test that catches commits that are small but opaque.

Size is the common failure, not the only one. A 20-line commit that changes a shared default
with no stated reason fails the read as badly as a 2000-line one.

## Mechanical vs judgment

A **mechanical** change is one the reader verifies by checking one instance plus the command
that produced the rest: a rename, a formatter run, a regenerated lockfile, a mass import
reshuffle, a bulk path fix. These may cross the module and file rails freely, on two
conditions:

- **It is its own commit.** Never in the same commit as a judgment change — a single
  hand-made exception hiding in 40 mechanical files will not be found.
- **The message names the command.** `rg -l old_name | xargs sed -i 's/old_name/new_name/g'`,
  or the formatter and its version. That line is what makes the commit reviewable at all.

A **judgment** change is everything else, and the budget applies in full.

When one episode needs both — a rename that enables the fix — the rename is the prep commit
and lands first, with no behaviour change.

## Worked examples

These come from running `propose_episode.py` against this collection's own
`plans/BACKLOG.md`, whose Order section had already been written by hand. The proposer and
the hand-written order agreed on the first two and disagreed on the third, which is about the
right hit rate to expect.

**Two defects, one module, one commit.** Items 11 and 12: a deck helper that silently drops a
required mark, and an anchor checker that accepts the wrong shape and reports garbage. Four
files, all under `skills/code-walk-deck`. Different functions, different symptoms — but one
sentence: *make the deck tooling fail loudly instead of silently*. That the sentence exists is
what makes them one commit rather than two; the module they share only makes it cheap.

**A guard and the code that reads it.** Items 2 and 1: a packaging step that does not require
a snapshot, and an inventory step that never reads one. High severity then medium, different
sizes, same module. Together they are *make an export self-sufficient off-cluster*; apart,
each is half a feature and the first one to land is untestable.

**One item that does not fit.** An item naming six files across four modules
(`src/api`, `src/ui`, `src/db`, `docs`) is not an episode, and no grouping rescues it. The
proposer flags it `over the 3/5 budget: plan it as a stack`. Split it before writing a doc —
a plan that promises one commit and lands six has misinformed everyone who read it.

**A deliberate cross-module commit.** Items 3, 4 and 10 are prose fixes in three different
skills' `SKILL.md`. Three modules, three files, one sentence: *make the three skills say the
same thing about evidence*. This is the carve-out working as intended — uniform edit shape,
no logic, verified by reading one instance — and it is worth the line in the doc saying why
three modules was right here. The proposer will not propose it, because it groups on shared
modules and these share none; a human reads the Order section and overrides.

**Where the proposer was wrong.** It put item 3 in its own episode rather than with 1, 2 and
4, because the word "never read" made it look like a bug while the others read as features.
The kind was marked `(inferred)`, and checking inferred kinds against the plan docs is step 3
of the skill for exactly this reason. Adding a `Kind` column to the BACKLOG removes the guess
permanently.

## When the diff escapes the scope

```bash
git diff --stat                       # what is actually touched
git diff --stat -- $(cat scope.txt)   # the part that was planned
git stash push -- <path>              # park an escape while you decide
git checkout -- <path>                # drop it
```

- **Shrink** — park or drop the extra, and open a backlog item for it the same minute. An
  escape that is reverted and not written down comes back as a surprise next week.
- **Split** — `git add -p` the planned part, commit it, then commit the rest with its own
  subject. If the rest depends on the planned part, that order is forced; if the planned part
  depends on the rest, the rest is the prep commit and goes first.
- **Re-plan** — update the doc's sentence and Scope table, and add a line: *the episode grew
  from N to M files because X*. The record of having been wrong is worth more than a doc that
  looks prescient.

## Splitting a stack

A feature too big for one commit becomes an ordered stack. The usual shape:

1. **Prep** — renames, moved files, extracted helpers. No behaviour change.
2. **Core** — the new mechanism, with its test. The one commit that needs real review.
3. **Wiring** — call sites, defaults, config.
4. **Docs and records** — README, plan docs, revision rows.

Rules that make a stack reviewable:

- Each commit is green on the project's own checks. A stack that only works at the tip is one
  commit wearing four hats.
- Each commit has its own sentence. If two commits in the stack would share a subject line,
  they are one commit.
- The interface between commits is named in the doc, so a reviewer who reads only commit 2
  knows what 1 guaranteed.
- Past about five commits, stop: the feature wants a design doc, and the stack wants to be a
  branch or a PR per group. A fifteen-commit stack gets reviewed as a single diff, which is
  the thing the split was meant to avoid.
