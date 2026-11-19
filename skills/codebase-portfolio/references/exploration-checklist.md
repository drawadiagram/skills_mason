# Exploration checklist

Read-only. Nothing here writes to the repository, installs anything, or contacts a service
other than the git host. Each block ends in what to write down. Adapt the commands to the
language and layout; the questions are the point.

## 1. Shape of the repository

```bash
git remote -v
git branch -a
git ls-files | awk -F/ '{print $1"/"$2}' | sort | uniq -c | sort -rn | head -60
git log --oneline | wc -l
git log --reverse --format='%ad %s' --date=short | head -3
```

Then read the README, the package manifest (`pyproject.toml`, `package.json`, `Cargo.toml`),
the docs nav, and any tracker (`plans/BACKLOG.md`, `ROADMAP`, `CHANGELOG`).

Write down: packages and how they depend on each other, how old the project is, which
branches look like unmerged work, and whether the untracked files in the working tree are
scratch that must not be swept up by `git add -A`.

## 2. What already runs without special hardware

```bash
git grep -il -E "mock|dry.?run|toy|quickstart|surrogate|fixture" -- '*.md' '*.py' | head -40
git ls-files | grep -E "\.ipynb$|Makefile|Dockerfile|tox\.ini|noxfile"
```

Read the README of every example directory. Look for a CLI and list its subcommands.

Write down, for each runnable thing: the exact command, what it needs installed, how long it
takes, what it produces, and whether a test covers it. Note honestly what in it is real and
what is simulated. These are the deliverables that are already done.

## 3. Verify the pre-plan, fact by fact

For every claim in the owner's outline, find it in the code or fail to:

```bash
git grep -il -E "<term from the outline>" | head
```

Search **outside the repo as well** — sibling directories often hold the analyses, reports,
figure scripts and manuscript that the outline is remembering. List what is there.

Sort each claim into:

- **Confirmed**, with the path.
- **Already built** — the outline asks for it as new work.
- **Does not exist** — in the repo or anywhere nearby. Check the project's own limitations
  or roadmap page; it often says so in plain words.

## 4. Tests, CI and docs

Read the CI workflow and the test runner config. Count test files per package. Find out
whether the docs build is strict and whether notebooks are executed or committed with outputs.

Write down: the commands that must stay green, and any existing job the demo or the new
notebook can be added to rather than creating another.

## 5. Licence

```bash
ls | grep -i -E "licen[cs]e|copying|notice"
gh repo view OWNER/REPO --json licenseInfo,visibility,isFork,viewerPermission
```

Write down: the licence, or that there is none. None means nothing may be copied out of the
repository, and choosing one is a decision for all the copyright holders. Also note the
licences of any model weights or datasets a demo would download; a demo that downloads
nothing engages none of them.

## 6. People

```bash
scripts/authorship_by_area.sh            # every top-level area
scripts/authorship_by_area.sh src docs   # or named directories
```

Write down: who wrote which areas, in commit counts, with name variants merged. Mark the
areas that are clearly the owner's and the ones that are shared. Note the owner's permission
level upstream (from the `gh` call above): it decides whether they can merge their own
hygiene fixes or must ask.

## 7. Sensitive content

Use the `repo-sensitive-scan` skill if it is installed. As a first pass only:

```bash
git grep -n -I -E "/home/[a-z]+|/u/[a-z]+|/scratch/|--account[= ]|#SBATCH -A|@[a-z]+\.(edu|com)" | cut -c1-160 | head -60
```

Write down: each real finding, its path, and whether it is already on a public remote. A
finding that is already public is fixed by pull request; whether history is rewritten is for
the maintainers.

## 8. Evidence and what is already public

List the figures, tables and reports that exist, in the repo and beside it. For each: where
the data is, how large, which script regenerates it, and whether its numbers already appear
in a public commit.

Write down two lists: **public now** (can be cited immediately, with its source) and
**needs approval** (and whose).

## Report

One table, then two lists.

| Component | Location | State | Portfolio use | Risk |
|---|---|---|---|---|
| … | path | done / partial / missing, with one fact | which reviewer need it serves | what could go wrong |

- **Asked for in the pre-plan and already built:** …
- **Assumed by the pre-plan and not found anywhere:** …
