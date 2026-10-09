# skills_mason

Custom [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills), mostly for
working on HPC/SLURM clusters (built and tested on NCSA Delta).

## Skills

| Skill | What it does |
|---|---|
| [code-walk-deck](skills/code-walk-deck/SKILL.md) | Build a technical slide deck that walks an audience through a real codebase: a `.pptx` with native editable diagrams, `file:line` citations checked mechanically, and a speaking script generated from the deck's own notes. |
| [hpc-run-data-review](skills/hpc-run-data-review/SKILL.md) | Inventory a project's run directories, join them to `sacct`, classify each run (smoke test, pipeline, campaign, failure kept as evidence), and plan what to keep, delete, or export as a verified tarball. |
| [plans-backlog](skills/plans-backlog/SKILL.md) | Structure a project's `plans/` dir and `BACKLOG.md`: one evidence-backed row per item linked to a dated plan doc, upstream-defect docs, honest status from open to closed-by-a-run, and a linter for duplicate IDs, broken links/anchors and orphan docs. |
| [repo-sensitive-scan](skills/repo-sensitive-scan/SKILL.md) | Scan a repo's committed or staged content for emails, Slurm accounts and allocations, usernames, cluster paths and secrets; mark each finding as pushed or unpushed, and propose fixes. |
| [slurm-job-watch](skills/slurm-job-watch/SKILL.md) | Watch SLURM jobs from submission to finish: queue position and estimated start, state changes, log errors and progress, silent hangs, and a final `sacct`/`seff` summary. |

`code-walk-deck` is the one skill that needs more than a login node: `node` with
[pptxgenjs](https://gitbrent.github.io/PptxGenJS/) to build the deck, and `soffice`
(LibreOffice) plus `pdftoppm` (poppler-utils) to render it for the layout check. Its Python
scripts are stdlib-only like the rest, and each reports clearly when a tool is missing.
See that skill's Requirements section for what still works without them, and `CLAUDE.md`
for the policy skills follow when they need an external tool.

## Layout

```
skills/<skill-name>/
  SKILL.md       # frontmatter (name, description) + instructions
  scripts/       # executable helpers the skill calls
  references/    # longer docs and examples loaded on demand
```

## Install

Symlink the skills you want into your personal skills directory:

```bash
mkdir -p ~/.claude/skills
for s in skills/*/; do ln -sfn "$PWD/$s" ~/.claude/skills/"$(basename "$s")"; done
```

Remove any existing copy in `~/.claude/skills/<name>` first, because `ln -sfn` will not
replace a real directory. To use a skill in a single project, symlink it into that project's
`.claude/skills/` instead.
