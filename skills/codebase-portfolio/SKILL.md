---
name: codebase-portfolio
description: Turn an existing codebase into a portfolio item — a showcase a hiring manager, reviewer or collaborator can judge in about five minutes — by planning the narrative and packaging around code that already works rather than re-engineering it. Verifies the owner's pre-plan against the repository, reports what already exists and what never did, asks the few decisions that are the owner's (what evidence, what may be shown, how reviewers will see it), and writes a milestone plan covering a private mirror, publication hygiene, a case-study page with per-audience reading paths, a one-command demo, a guided tour notebook, results pages gated on approval, and small upstream pull requests. Use this whenever the user wants to showcase, present, package or write up a project or repo for a job search, portfolio, resume, case study, application, promotion packet or public launch, asks "how do I show this work off", "make this repo presentable", "build a plan from this portfolio outline", or wants a role statement or demo script for a codebase they contributed to — even if they never say "portfolio". Not for building a personal website, and not for a slide deck about the code (use code-walk-deck).
---

# A portfolio item from a codebase

The person has a working project and a reviewer with five minutes. The gap between those is
almost never missing code. It is that the evidence is scattered: the laptop demo is three
directories down, the result that matters is in a plan doc, and the README describes the
framework rather than the case for the person. So the work is **narrative and packaging, not
engineering**, and the main risk is the opposite of what it looks like — not doing too little,
but rebuilding things, overclaiming, or publishing something that was not the owner's to
publish.

Three things decide the plan, and all three are cheap to check and expensive to assume:

- **The pre-plan is stale in both directions.** Outlines are written from memory. In the
  session this skill came from, the outline asked for a mock backend, an adaptivity figure and
  a runnable demo that the repo already had, and for a resume feature, a tool wrapper and a
  benchmark dataset that existed nowhere. Both lists change the plan more than anything else.
- **The repo is usually shared.** Authorship, licence and what counts as unpublished are
  facts about a group, and a portfolio that gets them wrong costs more than it earns.
- **Reviewers have to be able to reach it.** Where the work ends up visible (public repo,
  upstream pull requests, a private export) shapes every milestone, so it is asked early.

The output of this skill is a **plan for the owner to approve**, then the milestones. Do not
start writing pages or wrappers before the plan is agreed.

## Requirements

`git` is assumed. `gh`, authenticated, is optional enrichment: it reports the licence the host
sees, repository visibility and the owner's permission level. Without it, read those from the
web page or ask. Scripts are bash and need nothing else.

| Script | Use for |
|---|---|
| `scripts/authorship_by_area.sh [DIR…]` | Commit counts per author for each top-level area (or the directories given), with the same person's name variants listed side by side so they can be merged by eye. Read-only. Feeds the contributors table and keeps role claims checkable |

## 1. Explore, read-only

Work through `references/exploration-checklist.md`. It is a list of questions with the
command that answers each. The ones that most often change the plan:

- **What already runs on a laptop?** Mock modes, toy examples, executed notebooks, a CLI with
  a dry run. Each one is a deliverable that is already done.
- **Does every "known fact" in the pre-plan hold?** Check each against the code and sort it
  into *confirmed*, *already built*, or *does not exist*. Search siblings of the repo too:
  analyses, reports and figure scripts often live beside it, not in it.
- **Is there a licence, and what does the host report?** A missing licence blocks any reuse
  outside the repo and is a group decision.
- **What is the owner's permission upstream, and who wrote what?** Run
  `scripts/authorship_by_area.sh`.
- **Is anything sensitive already committed?** Hand this to the `repo-sensitive-scan` skill
  when it is available; a quick grep is a first pass, not a result.
- **Which results are already public?** Numbers committed to a public repo can be shown now.
  Everything else needs someone's approval.

Report the result as one table — **component, location, state, portfolio use, risk** — plus
the two lists: what the pre-plan asked for that already exists, and what it assumed that does
not. Keep it short enough to read in a minute.

## 2. Ask the owner's decisions, once and together

These are the questions exploration cannot answer. Ask them in one round, each with a
recommended default, and name the finding that makes the question necessary.

| Decision | Options | Default |
|---|---|---|
| **What evidence to build on**, when the evidence the pre-plan named cannot be found | the analyses that do exist · the owner points to the missing data · both · demo only, no measured results | the analyses that exist |
| **What results may be shown, and on whose approval** | only what is already public, with the rest prepared privately behind a sign-off · everything is cleared · nothing measured yet | already-public only |
| **Capabilities the pre-plan assumed that do not exist** | reframe to what exists and list the rest as roadmap · add a thin example that touches no core source · build it | reframe |
| **How reviewers will see it** | work privately, make it public at sign-off · stay private and share an export or invitations · private staging, finished pieces go upstream as pull requests | depends on who owns the repo; upstream pieces when it is shared |

Make the smaller calls yourself and say so in the plan: which use case is the centrepiece
(prefer the one with a laptop mode, the most data and the clearest authorship), and whether a
container is worth its upkeep (usually not, when a virtual environment runs the demo).

## 3. Write the plan

Fill in `references/plan-template.md`. Its sections are Context, Decisions, Findings,
Approach, Milestones, Files touched, Risks, Verification, and Dropped from the pre-plan and
why. The last section matters: the owner wrote the pre-plan, and each thing left out of it
deserves one line saying why.

The usual deliverables and their order are in `references/deliverables.md`, with what makes
each one good. In brief:

1. **Private mirror** as a second remote; one branch per future pull request; one private
   branch for what never goes public.
2. **Hygiene**: licence question raised, sensitive findings fixed, stale links repaired.
3. **Case-study page** with three reading paths, an architecture diagram and a contributors
   table.
4. **One-command demo** wrapping commands that already exist, with a CI job that proves it.
5. **Guided tour notebook** that imports existing helpers and adds no logic.
6. **Results**: a public page of already-public numbers, then a gated page.
7. **Private narrative assets**: role statement, demo script, one-page brief.
8. **Upstream pull requests** and a final scan.

Drop or merge milestones to fit the repo. A project with no docs site gets its case study in
the README; a solo project skips the mirror and the gate.

## 4. Principles the plan has to hold to

**Wrap, do not rebuild.** A `make demo` that calls two existing commands is packaging. A new
backend switch is rework, and it is also a new thing to maintain in a repo other people own.
The check is mechanical: the diff against upstream under the core source directories should
be empty on every outgoing branch.

**Never name a capability that does not exist.** If the ledger exists and nothing resumes
from it, the page says "recoverable results" and lists resume under roadmap. A reviewer who
finds one inflated claim discounts the rest, and a limitations section written plainly reads
as judgement rather than weakness.

**Every number carries its provenance.** A job ID, a commit, or a link to the document that
recorded it. A number that cannot be traced is left out.

**Unpublished results live on a branch that is never the base of a public pull request.**
Keeping them out by remembering to is not a control. Record the owner's statement of approval
before that branch moves.

**Hygiene goes first, not last.** A missing licence or a committed account name blocks
everything downstream, and the fixes are small. Leaving them for a final "publication check"
means discovering the blocker when the rest is finished. Rewriting history in a shared repo
is the maintainers' decision; report the finding and let them make it.

**Credit is part of the evidence.** The contributors table is built from `git shortlog`, so
"wrote the agent and the example pipelines; the core is shared" is something a reader can
check. It also protects the owner from an overclaim made by accident.

**A private fork of a public repository is not possible on GitHub.** Create an empty private
repository, add it as a second remote on the existing checkout, and push. Leave `origin`
pointing upstream. The `repo-rehome` skill covers the survey if the layout is less simple.

**Label simulated science on the artefact.** If scores in the demo are seeded random draws,
the figure says so itself, not only its caption — a figure gets pasted into slides without
its caption.

## 5. Build by milestone, verify before sending anything out

One milestone per branch, each small enough to review in ten minutes; the
`commit-episode-plan` skill sizes them. Before any branch leaves the private mirror:

- Clone it fresh somewhere else, run the demo command, and time it.
- Run the project's own lint, docs and notebook checks; test counts and outcomes unchanged.
- Confirm the diff under core source is empty.
- Run `repo-sensitive-scan` on the branch, and check it carries no file from the gated branch.
- Read each reading path cold in the built site: every link resolves, about five minutes.
- Check every number on a results page against the document it cites.

## Related skills

`repo-sensitive-scan` for the scan and its fixes · `repo-rehome` for mirrors and remotes ·
`plans-backlog` if the plan is to be tracked in the repo's `plans/` · `commit-episode-plan`
for sizing each pull request · `campaign-plot-style` (or the project's own plot module) for
regenerated figures · `code-walk-deck` when the owner also wants a talk.
