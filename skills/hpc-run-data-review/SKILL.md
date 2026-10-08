---
name: hpc-run-data-review
description: Review the run data an HPC project has accumulated: inventory every run directory, join it to sacct, sort runs by completeness, allocation size and what the workflow actually did (smoke test, single pipeline, limited toolset, multi-cycle campaign, failure kept as evidence), then plan what to keep, what to delete and what to export. Optionally build a flat per-task table and a verified tarball for offline analysis. Use this whenever the user wants to clean up, triage, archive, curate, sort, download or export HPC/SLURM run outputs, logs or results, or asks which runs are worth keeping, which were tests, or what data exists from past jobs, even if they never say "review".
---

# Reviewing HPC run data

The goal is a decision the user can trust: a table showing every run, what each one is
worth, and what to keep or delete, backed by evidence rather than by directory names. Two
things go wrong in this kind of review:

- **Deleting something a document still cites.** A failed run is often the only evidence
  for a fix.
- **Repeating a stale claim** from an index or README. In the review this skill was built
  from, the archive's own index said every job ran on one partition, but `sacct` showed
  that seven of the eight ran on another.

So the cluster's accounting is the source of truth for allocation, and the run's own logs
are the source of truth for completeness.

Bundled scripts, all read-only except `package_export.sh`, which writes only its output file.
Run them by absolute path from this skill's directory:

| Script | Use for |
|---|---|
| `scripts/inventory.sh ROOT [--prefix NAME] [--since DATE]` | One row per job dir: size, file count, which pieces exist (slurm.out, manifest, work/, logs, provenance, ledger), manifest fields, and sacct's partition/nodes/TRES/elapsed/state. With `--prefix`, it also lists jobs with that name that have **no** directory, which is how you show nothing was missed |
| `scripts/jsonl_fields.py FILE... [--depth N]` | The key paths in JSON/JSONL logs, how many records carry each one, and an example value. Run it before writing anything that parses logs |
| `scripts/package_export.sh OUT.tar.gz BASE PATH...` | A tarball with paths relative to BASE. It refuses to overwrite, checks the archive reads back, and prints size, sha256 and contents |
| `references/example_task_table.py` | A worked example of flattening per-run ledgers into a one-row-per-task CSV. Adapt it; do not run it blind on another project |

## Workflow

### 1. Scope: whose data, and where

- **Find every location.** Look in:
  - the project's archive or run root;
  - stray run dirs in the checkout (`git status --ignored` finds gitignored ones);
  - scratch or NVMe work dirs;
  - side files such as ledgers or trust and state files that live outside the run dirs.
- **Keep to this project.** One account often runs several workflows, and the job name is
  usually what separates them. Leave other projects' jobs and directories alone, and say
  that you did.
- **Check memory and project docs first** for an earlier cleanup, for example an `INDEX.md`
  or a "deleted on <date>" note. Build on it; do not redo it.

Avoid unbounded `du` over large trees such as model caches, containers or reference repos.
It can take minutes on Lustre. Size only the candidate run dirs.

### 2. Inventory

Run `inventory.sh` on each run root, with `--prefix` set to the project's job-name prefix.
Then look inside one representative directory per kind of run:
- what `work/` holds (structures, scripts, caches);
- what the logs record per task.

For anything parsed later, run `jsonl_fields.py` first. A field present in "5/16" records is
a different kind of event in the same file, and older runs often lack fields that newer ones
have.

### 3. Classify along three axes

- **Completeness**, judged from the logs, not from SLURM state. A `COMPLETED` job can hold a
  failed run, and a `CANCELLED` job can hold the key evidence. Typical tiers:
  1. full workflow, several cycles or designs;
  2. one complete pass, or a pass with stages missing;
  3. failure kept as evidence, logs only;
  4. no surviving data.
- **Allocation:** partition, nodes, GPUs/CPUs/memory (`AllocTRES`), elapsed time, and the
  billing weight if the user cares about cost.
- **Workflow:** what ran, in plain terms. For example: smoke test, single pipeline, limited
  toolset (*which* stage was missing and *why*), multi-cycle campaign, parameter variant.
  Take it from the campaign or config name *and* the logs, because names lie when a run was
  truncated.

Note every contradiction between existing docs or indexes and `sacct` or the logs. Fixing
those is part of the job.

### 4. Plan keep / delete, and get approval before deleting

Present one table: tier, job, workflow, allocation, elapsed, completeness, size, and a
recommendation. Default rules:
- **Keep complete runs in full.** Their outputs (structures, sequences, predictions) are the
  analysis data.
- **Keep cited failures** as logs and provenance. Before you propose deleting a run, grep
  the docs for its job id.
- **Delete** mock/local output that is not real data, empty session dirs, and caches that can
  be regenerated. State the size first, so the user knows whether deleting is worth it.
- **When the data is already small** (MBs), say so. Deleting tiny files buys nothing and
  risks evidence, and a short delete list is a fine outcome.

Deletion is irreversible. Run `rm` only after the user has approved the plan, and never on a
path you have not listed and sized.

### 5. Export for analysis, when asked

- **Flat table first.** One row per task (or per design), with:
  - run context joined in;
  - one column per metric;
  - failed checks with their reason;
  - artifact paths **made relative to the job dir**. Ledgers usually record absolute paths,
    which are wrong after a move and meaningless on a laptop.

  Put the script in a scratch dir unless the user wants it in the repo.
- **Verify the table against known facts** before you trust it:
  - the row count equals the expected number of tasks;
  - per-run states match the index;
  - one value quoted in the docs (a score, a verdict) reads back exactly.
- **Package** with `package_export.sh`: the chosen run dirs, the index, side ledgers and the
  table. Put the archive outside the run root, so a later export never sweeps it up.
- **Hand over** the `scp`/`rsync` command for the user's machine, plus the sha256.

### 6. Update the record

- Fix wrong claims in the index or README.
- Add a dated tiers note naming what was exported and where.
- If the review changed how runs should be stored in future, say so. The code that writes
  runs is the durable fix; a one-time cleanup is not.

## Report

Keep it short:
- the tier table;
- what was deleted, with its size;
- the export path, size, sha256 and download command;
- the corrections made;
- anything the data cannot tell you. For example, "no per-task wall time: the logs only
  timestamp whole runs".
