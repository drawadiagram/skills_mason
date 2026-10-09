# Conventions

## Status vocabulary

Use these words, in this order of progress. Free text may follow after a semicolon.

| Status | Means | Needs |
|---|---|---|
| `open` | Known, nobody has started | evidence in the Item cell |
| `open, needs decision` | Data is in; a human must pick a threshold or trade-off | the options and the data, in the doc |
| `open, upstream` | The fix belongs to a dependency | an `upstream/` doc |
| `in progress` | Someone is changing code | a branch name |
| `fixed, not yet confirmed` | Merged or committed, but no run has exercised it | the commit |
| `submitted: job N` | A confirming run is queued or running | the job ID, also in the doc |
| closed | A run or test confirmed it | move the row to **Closed**, with the evidence |

Never write "done" in the open table. Done means closed, and closed rows move.

## Severity vs tier

- **Severity** (high / medium / low) suits a defect tracker. It answers "what does this cost
  if left alone?". A good high cites lost hours or a failed run.
- **Tier** (1 = do first) suits a work plan. Define it in the BACKLOG header, e.g.
  *(measured impact or failure prevented) × (how many consumers benefit) ÷ effort*.
- Pick one per BACKLOG, and say which in the header.

## Evidence

- Every Item cell and every claim in a doc names the thing it rests on: a scheduler job ID,
  a commit SHA, a PR number, an artifact path, or a `file:line`.
- Numbers carry their job: "0.96 % adaptive occupancy (`12345678`)", not "about 1 %".
- If evidence was inferred rather than measured, say so ("inferred from GPU 0 activity, not
  sampled").
- A correction to an earlier claim goes in as a correction, naming what it corrects.
  Silently editing the old claim loses the record of what was believed and when.

## IDs and scopes

- IDs are integers, or prefixed integers (`F1`) for a second scope in the same repo. They
  are never renumbered or reused.
- Cite another scope's item by short name: "smb 15" or "F4".
- When two scopes cover related items, map them in a line under each BACKLOG's header.

## When to split or merge docs

- **Split** when two items will be fixed, tested or closed independently.
- **Merge** small items into one anchored doc when they ship in the same change set and share
  one test plan.
- One acceptance run gets its own doc, because its result section grows.

## Keeping it current

- Update the row and the doc in the same commit as the code change or job submission.
- After a run, add a **Result** section. Do not rewrite **Why** to match the result.
- Re-verify branch names and `file:line` references whenever the plan is picked up again.
- Keep closed rows in the Closed section until the next release or campaign. Remove them
  after that, since the doc and git history keep the record.

## Public repos

Plans quote job logs, `sacct` output and paths, so they collect account names, allocation
names, usernames and cluster paths. Use placeholders (`<allocation A>`, `$USER`,
`<hdd work dir>`) in committed plans, and scan before pushing.
