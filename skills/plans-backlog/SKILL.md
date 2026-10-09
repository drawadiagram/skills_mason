---
name: plans-backlog
description: Structure and maintain a project's plans/ directory and its BACKLOG.md tracker. One row per open item, each linked to a dated plan doc that holds the evidence, the change, and how it will be tested; upstream defects get their own docs; items close only when a run confirms the fix. Use this whenever the user wants to save, track or write up planned work, e.g. "save the remaining plan items", "track this in the backlog", "add/close a backlog item", "write a plan doc for X", "set up plans/", "what's still open", "record this job's result against the plan", or "triage the backlog", even if they never say "backlog". Also use it before submitting a test or acceptance run for a planned item, so the job ID gets recorded.
---

# Plans and backlog

A backlog is worth keeping only if a reader can trust it six weeks later. Three failures make
one untrustworthy:

- **Claims with no evidence behind them.** "Throughput collapsed" means nothing without the
  job it was measured on.
- **Items marked closed that nothing confirmed.** "Fixed" and "fixed and seen working on a
  real run" are different states, and a tracker that merges them hides regressions.
- **Stale references.** Branch names, `file:line` citations and counts drift quickly. In the
  session this skill came from, a plan targeted a branch that had been merged and deleted
  hours earlier.

So the layout below splits the short answer (the BACKLOG row) from the reasoning (the plan
doc). Every claim names its evidence, and status words have fixed meanings.

## Layout

```
plans/
  BACKLOG.md                      # the tracker: one row per item, links to docs
  YYYY-MM-DD-<topic-slug>.md      # one plan doc per topic, dated when written
  upstream/<component>-<issue>.md # defects in dependencies, written to be filed upstream
```

A project can have more than one `plans/`, e.g. one for the framework at the repo root and
one per example or component. Each keeps its own BACKLOG.

Templates for every file are in `references/templates.md`. Status vocabulary, evidence rules
and multi-scope conventions are in `references/conventions.md`. Read both before writing the
first BACKLOG in a project.

## Workflow

### 1. Find the scope

- Look for existing trackers: `find . -name BACKLOG.md -path '*plans*' -not -path './.git/*'`.
  **Reuse what exists and copy its local conventions.** Its column names, severity words and
  ID style override the defaults here.
- Put the work in the `plans/` of the code that will change. A framework change goes in the
  framework's `plans/`, even if an example motivated it. An example-only fix goes in the
  example's `plans/`.
- With more than one scope, give the newer one an ID prefix (`F1`, `F2`, …) so cross
  references are unambiguous. Cite the other one by short name ("smb 15"). Add a line near
  the top of each BACKLOG that links to the other and maps related items.

### 2. Verify before writing

Plans are written from conversation memory, and memory is stale. Before writing:

- **Branch facts.**
  - `git branch --show-current`;
  - `git ls-remote --symref origin HEAD`, the real default branch (a local `origin/HEAD` can lag);
  - `git merge-base --is-ancestor <branch> origin/<default>` for any branch you name as
    open or as a target.
- **Every `file:line`, count and symbol you cite.** Re-check each one against the checkout
  with `grep -n`. Fix the plan, not the code, if they disagree.
- **Job facts.** Take state, elapsed time and partition from `sacct`, not from memory or an old README.

### 3. Write the plan docs

- **One topic per doc.** A topic is one defect, one change set, or one acceptance run. Name
  the doc `YYYY-MM-DD-<slug>.md`, dated the day it is written, never renamed.
- **Several small items** belonging to one change (e.g. "PR 2") can share a doc. Give each
  its own section with an anchor `<a id="f3"></a>`, so BACKLOG rows can link `doc.md#f3`.
- **Every doc opens with a status line:**
  `**Status:** … · **Evidence:** job/commit · **Items:** …`.
  Then Why (with evidence), Change, and Test. For anything that will be run, the Test
  section has a pass-criteria table *written before the run*.
- **After a run, add a Result section.** Record the job ID, the measured numbers against the
  criteria, and what was surprising. Do not rewrite the plan to match the result.
- **Upstream defects** get `upstream/<component>-<issue>.md`, written so it can be pasted into
  the dependency's issue tracker: version, symptom, cause with `file:line` in *their* code,
  proposed fix, and impact on this project.

### 4. Update the BACKLOG

- Use one row per item: `| # | Item | Severity (or Tier) | Status | Doc |`. The Item cell is
  one line and cites its evidence (job ID, commit, PR). Details go in the doc.
- **Never renumber or reuse an ID.** Closed IDs stay retired.
- Keep an **Order** section: what to do next, and why that order.
- Keep a **Closed** section. Each entry says what closed it and the evidence:
  `- **6** — closed by job 12345678: 15.7/h vs 11.5 baseline, 0 failures. Doc: [..](..)`.
- Write "needs decision" in Status when the data is in and a human has to choose (a
  threshold, a trade-off). Never pick it silently.

### 5. Keep the status honest

An item's status moves: `open` → `in progress` → `fixed, not yet confirmed` → closed. Each
step needs a fact:

- **Fixed** means merged, or committed on a named branch. Name the commit.
- **Closed** means a run or test confirmed the fix. Move the row to Closed with that job or
  commit.
- **When you submit a job for an item,** put the job ID in the row's Status and in the doc's
  status line *in the same step*. Then the tracker never lags the cluster.
- **When a test is designed to exercise a path** (an injected failure, a forced edge case),
  check it really reaches that path before submitting. In the session this skill came from,
  hiding an input file would have failed in-process before the backend was ever involved.
  The injection had to move to a file only the remote tool read.

### 6. Revision history

If the project's (or component's) CLAUDE.md has a revision-history table, add a row: date,
commit or `—`, and one paragraph saying what changed and linking the plan doc. Mark anything
not yet run on the target system as such ("Not yet run on <cluster>").

### 7. Check and commit

- Run the linter:
  ```
  python3 -I <this skill>/scripts/check_backlog.py            # every plans/ under cwd
  python3 -I <this skill>/scripts/check_backlog.py path/to/plans
  ```
  Fix every `ERROR` (duplicate ID, broken link or anchor). Read each `WARN` and fix it unless
  it is deliberate: an orphan doc, an open row with no evidence, a finished item still in
  the open table.
- Commit the plans together with the code they describe, or as their own commit on the same
  branch. Plans are project history, not scratch.
- If the repo is public, check for real account, allocation and user names first (see the
  `repo-sensitive-scan` skill). Plans quote job logs, which are full of them.

## Requirements

Only `git` (environment tool) and Python 3 standard library. Nothing to install.
`check_backlog.py` is read-only.
