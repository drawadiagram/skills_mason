# CLAUDE.md

Collection of custom Claude Code skills. No build step or test suite.

## Structure

- `skills/<name>/SKILL.md`: YAML frontmatter with `name` (must equal the directory name) and
  `description` (this is what triggers the skill, so list the phrasings users actually use),
  followed by the instructions.
- `skills/<name>/scripts/`: executable helpers. Bash or stdlib-only Python, so they run on a
  bare cluster login node.
- `skills/<name>/references/`: longer material that SKILL.md points to and that is read only
  when needed.

## Conventions

- When you add, rename or remove a skill, update the skills table in `README.md`.
- This repo is pushed to GitHub. Use placeholders (`abcd`, `jdoe`, `me@uni.edu`, `$USER`) and never real
  usernames, allocation or account names, emails or cluster paths. Before committing, run:
  `python3 -I skills/repo-sensitive-scan/scripts/scan_sensitive.py --staged`.
  Findings in `repo-sensitive-scan`'s own docs that are placeholders are expected.
- Keep scripts executable (`chmod +x`). Check them with `bash -n` or `python3 -m py_compile`.
