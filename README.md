# skills_mason

Custom [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills), mostly for
working on HPC/SLURM clusters (built and tested on NCSA Delta).

## Skills

| Skill | What it does |
|---|---|
| [hpc-run-data-review](skills/hpc-run-data-review/SKILL.md) | Inventory a project's run directories, join them to `sacct`, classify each run (smoke test, pipeline, campaign, failure kept as evidence), and plan what to keep, delete, or export as a verified tarball. |
| [repo-sensitive-scan](skills/repo-sensitive-scan/SKILL.md) | Scan a repo's committed or staged content for emails, Slurm accounts and allocations, usernames, cluster paths and secrets; mark each finding as pushed or unpushed, and propose fixes. |
| [slurm-job-watch](skills/slurm-job-watch/SKILL.md) | Watch SLURM jobs from submission to finish: queue position and estimated start, state changes, log errors and progress, silent hangs, and a final `sacct`/`seff` summary. |

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
