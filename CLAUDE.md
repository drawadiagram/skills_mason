# CLAUDE.md

Collection of custom Claude Code skills. No build step or test suite.

## Structure

- `skills/<name>/SKILL.md`: YAML frontmatter with `name` (must equal the directory name) and
  `description` (this is what triggers the skill, so list the phrasings users actually use),
  followed by the instructions.
- `skills/<name>/scripts/`: executable helpers. Bash or stdlib-only Python by default, so
  they run on a bare cluster login node. See Dependencies before reaching for anything else.
- `skills/<name>/references/`: longer material that SKILL.md points to and that is read only
  when needed.

## Dependencies

Default to zero install. A skill that needs more than bash and stdlib Python is allowed, but
it has to declare that and fail legibly. Sort every external tool a skill touches into one of
these three and handle it accordingly.

**Environment tools** — `sacct`, `squeue`, `seff`, `git`. The thing the skill is *about*:
a SLURM skill on a node without `sacct` has nothing to do. Assume them, name them in
SKILL.md, no guard.

**Optional enrichment** — the skill is fully useful without it and better with it. Guard with
`shutil.which` or `command -v` and degrade quietly, the way `scan_sensitive.py` reaches for
`sacctmgr` to learn account names and carries on when it is missing. Do not warn about a tool
whose absence costs the user nothing.

**Installed dependencies** — `node`, pptxgenjs, LibreOffice, poppler. Absent from a login node
and not installed without thought, so these carry real cost:

- List them in a `## Requirements` section near the top of SKILL.md: the tool, the step that
  needs it, and the install line.
- Preflight in the script that uses it. Exit non-zero naming the missing tool and its package
  — never a bare traceback or `MODULE_NOT_FOUND`.
- Say which steps still work without it, so a missing renderer costs one step, not the skill.
- Install into a scratch directory and point the environment at it (`NODE_PATH`, a venv).
  Never add a dependency to the project the skill is being run against.
- Flag it in the `README.md` row. Nobody should meet a heavy dependency for the first time in
  a stack trace.

A scaffolding script may need an absolute path back into this checkout so generated files can
find the skill's own library. That is fine — such output is not committed — but note it in
SKILL.md, because those paths break for anyone the output is shared with.

## Conventions

- When you add, rename or remove a skill, update the skills table in `README.md`.
- This repo is pushed to GitHub. Use placeholders (`abcd`, `jdoe`, `me@uni.edu`, `$USER`) and never real
  usernames, allocation or account names, emails or cluster paths. Before committing, run:
  `python3 -I skills/repo-sensitive-scan/scripts/scan_sensitive.py --staged`.
  Findings in `repo-sensitive-scan`'s own docs that are placeholders are expected.
- Keep scripts executable (`chmod +x`). Check them with `bash -n` or `python3 -m py_compile`.
