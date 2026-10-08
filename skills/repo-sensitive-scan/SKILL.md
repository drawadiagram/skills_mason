---
name: repo-sensitive-scan
description: Check a git repository's committed content for personal and account data before it spreads — personal email addresses, HPC/Slurm account and allocation names, allocation balances or fairshare figures, usernames and home/project paths, and secrets such as tokens or private keys. Classifies every finding as already pushed or still local, finds the commit that introduced it, and proposes fixes (placeholders, disabled #SBATCH lines, history rewrite for unpushed commits only). Use this whenever the user asks to verify, audit, scan, or scrub a repo, branch, commit range, or staged change for PII, emails, accounts, allocations, usernames, paths, credentials or "anything personal", and before a push or PR when they ask whether it is safe to publish — even if they only say "make sure nothing private got committed".
---

# Scanning a repo for personal and account data

The question behind this check is always "what will other people be able to read, and what is
already out of my hands?". So a finding is only useful with two facts attached: **where** it is,
and **whether it has been pushed**. Unpushed content can be cleaned so that it never existed;
pushed content can only be fixed going forward unless someone decides to force-push.

## 1. Get the truth about the remote first

```bash
git fetch <remote>          # or at least: git ls-remote <remote> refs/heads/<branch>
```

A stale remote-tracking ref silently misclassifies commits. In the session this skill came from,
`origin/scaling-wide` was 3 commits behind the real remote tip because the branch had been pushed
from a different checkout; without the check, 8 commits looked unpushed when only 5 were. The
scanner prints a WARNING when the tracking ref differs from `ls-remote`. Do not ignore it.

## 2. Run the scanner

```bash
S=~/.claude/skills/repo-sensitive-scan/scripts/scan_sensitive.py
python3 $S -C <repo>                         # every line at HEAD, pushed/unpushed vs @{u}
python3 $S -C <repo> --range @{u}..HEAD      # only what the unpushed commits add, + their messages
python3 $S -C <repo> --staged                # pre-commit check
python3 $S -C <repo> --history               # all refs; reports the commit that introduced each item
python3 $S -C <repo> --term mylab-gpu --term "Jane Doe"   # extra identifiers
```

It auto-detects the identity to look for — `git config user.email`, `$USER`, and the user's Slurm
accounts (`sacctmgr ... format=account`, falling back to `sshare -U`) — and prints them on stderr
so you can see what was searched. Exit status: 0 clean, 1 findings, 2 error. Secrets are masked in
the output; never print one in full in your reply either.

Categories, in priority order: `secret`, `email`, `account`, `usage` (fairshare numbers,
"balance is N", "N GPU-hours left"), `user-path` (paths containing the username), `username`.

## 3. Triage

Not every hit is a problem. Typical acceptable items:

- package metadata authors (`pyproject.toml`, `setup.cfg`, `package.json`) — deliberate;
- `noreply` co-author trailers, `example.com` addresses, `<placeholder>` values (allowlisted by default);
- job IDs and compute-node hostnames — operational, not personal;
- generic variable names that merely contain "token" (only literal values are flagged).

Identity terms only cover *you on this cluster*. Two things catch the rest, and both matter in
practice — on the repo this skill was built for, the identity scan alone reported 12 findings and
the full scan reported 45:

- **Allocation prefixes** are added automatically (`abcd-delta-gpu` also searches `abcd`), because
  allocations appear bare in paths like `/work/nvme/abcd/$USER`.
- **`site-path`** flags any concrete `/scratch`, `/projects`, `/home`, `/u` or `/work/{nvme,hdd}`
  path that names a project or a person — your own accounts on *other* clusters (a different
  username and allocation ID on each), teammates' directories, support-ticket paths. It is a
  heuristic: review each hit, and skip public references the docs need (a GitHub URL, a public
  container image name).

Content that came from a shared upstream branch is still worth fixing on the feature branch if the
user agrees (it reaches upstream on merge), but say where it came from.

Record acceptable recurring items in `.sensitive-scan-allow` at the repo root (one Python regex per
line, matched against `PATH:MATCH`, e.g. `^pyproject\.toml:.*@`) so the next run is quiet. Ask the
user before allowlisting anything that identifies a person or an allocation.

Use `--history` (or `git log --all -S'<value>' --format='%h %an %ad %s'`) to find which commits
introduced a pushed item — the user needs that to judge exposure.

## 4. Report

One table: category, location, match, pushed/unpushed, introducing commit when known. Then a short
summary in plain words: what is already public, what is only local, what you judged acceptable and
why. Mention if the user's own uncommitted changes (e.g. a personal `#SBATCH --account` line) are
the reason something is *not* committed — those must stay out of commits.

## 5. Offer remediation — do not apply it unasked

Rewriting history and editing many files are the user's call. Lay out the options:

- **Unpushed commits:** can be rewritten so the values never existed (fix on top of the upstream
  tip, then graft and filter the unpushed range). Safe because nobody else has them.
- **Pushed content:** a new commit replaces it going forward; the old values stay in published
  history unless the branch is force-pushed, which needs coordination with everyone who has it.
- **Placeholders** that keep the file working: environment variables (`$WORK_DIR`,
  `SBATCH_ACCOUNT`), `<project>`-style placeholders in docs, `##SBATCH` to disable a directive.

The concrete recipes, including the history-rewrite sequence and pitfalls, are in
`references/remediation.md`. Read it before changing anything.

After any fix, re-run the scanner on the same scope and show that the count is zero (or only
allowlisted items remain).
