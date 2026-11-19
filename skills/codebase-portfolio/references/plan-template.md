# Plan template

Copy, fill in, and delete what does not apply. Keep it scannable: the owner should be able to
approve it in one read. Name real paths and real commands throughout.

```markdown
# <Project> portfolio showcase — plan

## Context

Who the reviewers are and how long they have. Then the two findings that shape everything:

- **Much of it already exists.** <the runnable demos, tests, docs found in exploration>
- **Some of it does not exist anywhere.** <what the pre-plan assumed and nothing provides>

So the work is <narrative and packaging | …>. Constraints from the owner: <no rework of core
code; where the work happens; anything else they said>.

### Decisions already made (<date>)

| Question | Decision |
|---|---|
| Evidence | … |
| What may be shown, and the gate | … |
| Capabilities that do not exist | … |
| Visibility | … |
| Centrepiece (my call) | … and why |

### Exploration findings

| Component | Location | State | Portfolio use | Risk |
|---|---|---|---|---|
| … | `path/` | … | … | … |

Include rows for: licence, sensitive findings, CI, results already public, and evidence held
outside the repository.

## Approach

### 1. Private mirror (M1)
### 2. Publication hygiene, first rather than last (M2)
### 3. Case-study page and reviewer paths (M3)
### 4. One-command demo (M4)
### 5. Guided tour notebook (M5)
### 6. Evidence pages (M6, in two stages)
### 7. Narrative assets (M7, private branch)
### 8. Upstream and sign-off (M8)

Under each: the files created, the existing functions or commands reused (with paths), and
the fallback if something turns out to need new code (usually: drop to prose and link a test).

## Milestones

| # | Milestone | Done when |
|---|---|---|
| M1 | … | a check someone can run |

## Files touched

New: …
Edited lightly: … (one clause each on what changes)
Not touched: <the core source directories>

## Risks

- **Unpublished results leaking.** Where they live, and the check that catches a leak.
- **Overclaiming.** The table and the limitations section that prevent it.
- **Licence.** What is blocked until it is settled.
- **Upstream drift.** Rebase before each pull request.
- **Unverified environments.** Anything advertised but never actually run there.
- **Third-party licences.** Weights or data the demo would download, if any.

## Verification

1. Fresh clone, one command, timed; outputs listed.
2. The project's lint, docs and notebook checks pass; test counts unchanged.
3. `git diff <upstream>/main --stat -- <core dirs>` is empty on each outgoing branch.
4. Sensitive scan on each outgoing branch; no file from the gated branch.
5. Cold read of each reading path in the built site.
6. Every number on the results page checked against its cited source.

## Dropped from the pre-plan, and why

- <item>: <one line — already exists as X / does not exist, shown as roadmap / would be rework>
```
