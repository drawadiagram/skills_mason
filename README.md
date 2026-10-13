# skills_mason

Custom [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills), mostly for
working on HPC/SLURM clusters (built and tested on NCSA Delta).

## Skills

| Skill | What it does |
|---|---|
| [campaign-plot-style](skills/campaign-plot-style/SKILL.md) | Draw campaign and HPC-performance figures in the group's house style: a CVD-validated performance-tier palette whose blue slot marks the best-performing configuration, the campaign scripts' type scale and recessive grid, and the rules for mean +/- 2 sigma bands, log axes with their zeros handled, and per-run colour identity across a whole report. |
| [code-walk-deck](skills/code-walk-deck/SKILL.md) | Build a technical slide deck that walks an audience through a real codebase: a `.pptx` with native editable diagrams, `file:line` citations checked mechanically, and a speaking script generated from the deck's own notes. |
| [hpc-run-data-review](skills/hpc-run-data-review/SKILL.md) | Inventory a project's run directories, join them to `sacct`, classify each run (smoke test, pipeline, campaign, failure kept as evidence), and plan what to keep, delete, or export as a verified tarball. |
| [plans-backlog](skills/plans-backlog/SKILL.md) | Structure a project's `plans/` dir and `BACKLOG.md`: one evidence-backed row per item linked to a dated plan doc, upstream-defect docs, honest status from open to closed-by-a-run, and a linter for duplicate IDs, broken links/anchors and orphan docs. |
| [repo-rehome](skills/repo-rehome/SKILL.md) | Move a repo, or the work in it, to a new home: survey what your access actually permits, pick the shape (GitHub transfer, replace a default branch with unrelated history, or fold one repo into another), then follow a runbook that proves the old commits are recoverable before the destructive step. |
| [repo-sensitive-scan](skills/repo-sensitive-scan/SKILL.md) | Scan a repo's committed or staged content for emails, Slurm accounts and allocations, usernames, cluster paths, host addresses and secrets — including inside committed `.pptx`/`.pdf` artifacts; mark each finding as pushed or unpushed, report whether each remote is public, and propose fixes. |
| [slurm-job-watch](skills/slurm-job-watch/SKILL.md) | Watch SLURM jobs from submission to finish: queue position and estimated start, state changes, log errors and progress, silent hangs, and a final `sacct`/`seff` summary. |

`campaign-plot-style` is the one skill that is not stdlib-only: its figures need `matplotlib`,
`numpy` and `pandas`, which is what the skill is about, and it reaches for `node` once to
re-run the `dataviz` palette validator if a colour changes.

Two skills need more than a login node. `code-walk-deck` wants `node` with
[pptxgenjs](https://gitbrent.github.io/PptxGenJS/) to build the deck, and `soffice`
(LibreOffice) plus `pdftoppm` (poppler-utils) to render it for the layout check.
`repo-rehome` wants [`gh`](https://cli.github.com), authenticated: it can be done without it,
but `gh` is what reads a ref back from the server, which is the check that makes replacing a
branch reversible. Their Python scripts are stdlib-only like the rest, and each reports
clearly when a tool is missing. See each skill's Requirements section for what still works
without them, and `CLAUDE.md` for the policy skills follow when they need an external tool.

## Layout

```
skills/<skill-name>/
  SKILL.md       # frontmatter (name, description) + instructions
  scripts/       # executable helpers the skill calls
  references/    # longer docs and examples loaded on demand
```

## Install

`scripts/sync-skills.sh` symlinks every skill in this checkout into your personal skills
directory (`~/.claude/skills` by default) and brings existing links back in sync:

```bash
scripts/sync-skills.sh              # link everything into ~/.claude/skills
scripts/sync-skills.sh --dry-run    # show what it would do
scripts/sync-skills.sh .claude/skills   # or into one project
```

It is safe to re-run: it adds links for new skills, repoints links left dangling by a rename,
and removes links to skills no longer in this checkout. It never overwrites a real file or
directory, or a symlink pointing somewhere else — those are reported as conflicts and the
script exits non-zero, so clear them by hand and re-run.

To use a single skill, symlink just that one: `ln -s "$PWD/skills/<name>" ~/.claude/skills/`.
