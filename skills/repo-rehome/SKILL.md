---
name: repo-rehome
description: Move a git repository, or the work inside it, to a new home — transfer a repo to another user or organisation, land a rewrite on an existing repo's default branch while archiving what was there, or fold one repo into another keeping its history. Surveys both ends first, because whether you hold admin or only push decides which of those is even possible, then works through a runbook that proves the old commits are recoverable before anything destructive runs. Use this whenever the user wants to move, migrate, rehome, relocate, transfer, consolidate, merge or retire a repository, hand a project over to a lab or team account, replace a repo's contents with a rewrite while keeping its URL and issue tracker, archive old branches before overwriting a branch, or swap which remote a checkout points at — even if they only say "we want to use the same repo" or "put this on main instead".
---

# Moving a repository to a new home

A rehome looks like a git problem and is mostly a permissions-and-people problem. Two things
decide the whole plan, and both are cheap to check and expensive to assume:

- **Do you hold `admin` on the destination, or only `push`?** Admin lets you change the
  default branch, set protection, delete a branch and transfer a repo. Push lets you write
  to unprotected refs and nothing else. A plan that assumes admin and meets push has to be
  redesigned, not patched — in the move this skill was built from, the discovery that the
  token had `push` only is what selected the shape, because it ruled out "create a branch,
  then promote it" entirely.
- **Who else is holding this repo?** Forks do not follow a force-push. Issues outlive a
  content swap and go on describing code that no longer exists. Both are people, and both
  are owed notice *before* the change rather than an explanation after it.

So: survey, choose the shape, then follow that shape's runbook. Do not start pushing.

## Requirements

`git` is assumed. `gh` ([cli.github.com](https://cli.github.com), authenticated with
`gh auth login`) is needed for the survey, the API verification and any transfer; without it
you can still do the git half by hand, but you lose the read-back check that makes the
destructive step safe, so install it rather than skipping it. Everything else is bash and
stdlib Python.

| Script | Use for |
|---|---|
| `scripts/survey_repo.py OWNER/REPO [OWNER/REPO…] [--json]` | The facts that constrain the move: your access, default branch, visibility, every branch and its SHA, protection, tags, forks, open issues and PRs — each followed by its consequence ("no admin: you CANNOT change the default branch"). Read-only. Run it on the destination *and* the source before writing a plan |
| `scripts/archive_refs.sh OWNER/REPO [--prefix P] [--tag NAME] [--only A,B] [--dry-run]` | Copies every branch to `archive/<branch>` from a fresh clone, optionally tags the default branch, then **reads every copy back from the API** and exits non-zero if any is missing or wrong. Prints the exact undo command for the force-push it has just made safe. Originals are left in place |

## 1. Survey both ends

```bash
python3 -I scripts/survey_repo.py octo-lab/widget jdoe/widget-rewrite
```

Write the answers down — the SHA of the destination's default branch especially, because it
becomes the lease that makes the force-push refusable. Then answer three questions:

- **Is there content at the destination that must survive?**
- **Do the two histories share any commits?** (`git log` on both, or just ask: is this a
  rewrite from scratch or a continuation?)
- **Do you want the repository itself to move, or only the work inside it?** A transfer keeps
  issues, stars, watchers and URL redirects. Pushing content keeps nothing but the URL.

## 2. Choose the shape

| If… | Shape | Runbook |
|---|---|---|
| You own the repo, want its issues/stars/URL to travel with it, and the destination has no repo of that name | **transfer** | `references/transfer.md` |
| The destination repo already exists and must keep its identity (URL, issue tracker, default branch), and your history is unrelated to its | **replace** | `references/replace.md` |
| One repo should become part of another, with its history preserved under a subdirectory | **consolidate** | `references/consolidate.md` |
| The histories share commits and the destination is just a different remote | none of the above — this is an ordinary `git remote set-url` and `git push`. Say so and stop | — |

Transfer is the strongest option when it is available, because GitHub moves the issues,
stars, watchers, webhooks and redirects for you and you write no git at all. It is often
unavailable: it needs admin on the source, create rights at the destination, and a free name.
Check that before designing around it.

## 3. Invariants, whatever the shape

**A move to a more public home is a publication event.** The audience changes, so content
judged fine for the old one has to be re-judged for the new: host addresses of machines you
run, cluster accounts and allocation ids, colleagues' usernames, home and project paths,
tokens. Run the `repo-sensitive-scan` skill against the tree *and* decide about history before
the first push, not after. Redaction after publication is hygiene, not recall.

**Prove the undo before you need it.** `archive_refs.sh` exists because the only thing that
makes replacing a branch reversible is the old commit still being reachable under another
name, verified by reading the server rather than trusting your own push output. Non-destructive
steps first, destructive last, and a gate between them.

**Pin the lease to the SHA you surveyed.** `git push --force-with-lease=main:<surveyed-sha>`
is refused if anyone pushed in the meantime; a bare `--force` silently overwrites them. Use
the full SHA.

**Check that the local ref actually holds the work.** A push of `main:main` sends your local
`main`, not the branch you did the work on. If the rename, the redaction or the fix is sitting
on a feature branch, you will publish the state you were trying to replace. This is the easiest
mistake in the whole procedure to make and the hardest to notice, because every command
succeeds. Confirm with `git log -1 main` immediately before pushing.

**Acceptance happens in a fresh clone, not your working tree.** Your checkout has build
artifacts, ignored vendor directories and local config that a new reader will not have. Clone
the published result somewhere else and build it there. Expect a gitignored dependency
directory to make that fail — that failure is real information about the repo, not a hitch in
the move.

**Retire the old remote last, and push to it before you freeze it.** Until the new home is
verified, the old one is your only live copy, and an archived GitHub repo is read-only. So:
verify the new home, push the final state to the old repo, *then* archive it — otherwise its
permanently-frozen HEAD is whatever state you were moving away from. Afterwards, retarget
local clones (`git remote set-url origin …`) or the next push goes nowhere useful.

**Names are layered, and only one layer moves cheaply.** See `references/renaming.md`. The
short version: the name on the screen, the package/identifier name in the code, and the
repository name are three different things, the one users read is usually not the one you
would find by grepping for the repo's name, and paths recorded in deployment docs are
descriptions of a running system — editing those does not rename the service.

## 4. Credentials, when a push cannot authenticate

If `git push` reports `could not read Username` and `ssh -T git@github.com` is denied, the
session has no key. Prefer wiring git to the `gh` login **for that repository only**:

```bash
git config --local credential.helper '!gh auth git-credential'
```

Repo-local keeps it out of the user's global config, and it stores no token anywhere — unlike
putting one in a remote URL, which writes it into `.git/config` and the reflog.

## 5. Record what the run returned

A rehome is done once and relied on for years, so the useful artifact is a record of what each
step actually returned — the archived SHAs, the force-push line, the acceptance results, and
anything deliberately skipped. The `plans-backlog` skill's plan-doc-with-an-acceptance-ladder
shape fits this well: write the rungs first, fill in results as you go, and mark a skipped rung
**skipped** rather than leaving it blank. A blank cell reads as "not reached"; the distinction
matters when the skipped rung was telling a fork owner.
