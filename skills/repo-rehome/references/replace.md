# Replace: unrelated history onto an existing repo's default branch

Use when the destination repo must keep its identity — same URL, same issue tracker, same
default branch — but its *contents* are being replaced by work that shares no history with
it. A rewrite landing on the repo it rewrites.

The shape is: **archive every existing ref, verify the copies from the API, then force-push
the default branch with a pinned lease.** It needs no admin, which is the reason to prefer it
over anything that creates a branch and promotes it — promotion is a default-branch change,
and that is admin-only. If the destination's default branch is already the branch you want
the work on, you need nothing but `push`.

## Why this order

Replacing a branch is irreversible unless the commit it pointed at stays reachable under
another name. So every non-destructive step runs first and is *verified from the server*
before the destructive one is allowed to run. After the archive copies verify, the force-push
has a one-line undo. Before they verify, it does not.

## The ladder

Write it out before running it, fill in what each rung returned, and keep it. Rungs 0–5 are
all reversible; 6 is the one that is not.

| # | Step | Expected |
|---|---|---|
| 0 | `survey_repo.py DEST SOURCE` | your access; note the destination default branch's **full SHA** |
| 0b | `git log -1 <local-branch-to-publish>` | the commit you actually mean to publish |
| 0c | **the work is on the ref you will push** — merge the feature branch into local `main` | `git log -1 main` is that commit, not the old one |
| 0d | sensitive scan of the tree you are about to publish | clean, or every finding a decision you have recorded |
| 1 | tell each fork owner the force-push is coming | acknowledged |
| 2 | `archive_refs.sh DEST --tag <name>-v1` | copies pushed, originals untouched |
| 3 | the script's own API read-back | every copy verified; **stop here if not** |
| 4 | `git log <prefix>/<default>` in a fresh clone | the old history, ending at the surveyed SHA |
| 5 | the tag dereferences to the surveyed SHA | a second, independent pointer |
| 6 | force-push with the lease | accepted |
| 7 | fresh clone + build | passes, or fails for a reason you understand |
| 8 | fresh clone + test suite | passes |
| 9 | the thing a user sees says what it should | checked |
| 10 | triage the destination's open issues | each closed or re-filed |
| 11 | push the final state to the old remote | its HEAD is the state you want frozen |
| 12 | archive the old remote | read-only, **only after rung 9** |
| 13 | `git remote set-url origin <dest>` | later pushes reach the new home |

## The commands

Rungs 2–5, which `archive_refs.sh` does and verifies in one go:

```bash
python3 -I scripts/survey_repo.py octo-lab/widget          # note the default branch SHA
bash scripts/archive_refs.sh octo-lab/widget --tag widget-v1
```

Rung 6, from the repo holding the work:

```bash
git remote add dest https://github.com/octo-lab/widget.git
git push --force-with-lease=main:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2 dest main:main
```

The lease is the rail. If anyone pushed to the destination between your survey and now, the
push is **refused** rather than quietly discarding their work. Never substitute `--force`.

Rungs 11–13:

```bash
git push origin main                                   # old remote, while still writable
gh repo archive jdoe/widget-rewrite --yes               # now read-only
git remote set-url origin https://github.com/octo-lab/widget.git
```

## What this does not move

Pushing content moves content. The destination keeps its own issues, PRs, stars, watchers,
webhooks and settings, and gains nothing from the source repo. If the issues and stars should
travel, you wanted a transfer (`transfer.md`), not this.

## Traps found by doing it

**The push sends your local branch, not your work.** `main:main` publishes local `main`. Work
done on a feature branch and not merged means you publish exactly the state you were trying
to replace — and every command succeeds, so nothing warns you. That is rung 0c, and it earns
its place as a separate rung.

**Verify from the server, not from the push output.** Push output reports what was sent. A
read-back via `gh api repos/.../branches/<ref>` reports what is there. They are different
claims and only the second one is a gate.

**Archive from a fresh clone.** Pushing `refs/remotes/origin/<b>` out of a scratch clone
guarantees the copies are the server's refs. From a working tree, a stale local branch can be
archived under a name implying it is the server's state.

**A fresh clone may not build, and that is the repo's problem surfacing.** Gitignored vendor
or dependency directories are absent from a clone by definition. Copy them in and note it;
do not conclude the move broke something.

**Expected test counts can be environment-dependent.** A suite that passes N in your checkout
may pass N−2 in a scratch clone because some tests skip on a sibling checkout being absent. A
skip that names its own reason is information, not a failure — read the reason before treating
the number as a regression.

**Leave the originals.** `archive_refs.sh` copies and does not delete, so the old branch names
stay where a reviewer expects them. Deleting them is admin-only and should wait for a human
to have actually reviewed what was archived. The default branch cannot be deleted at all while
it is the default.

**Telling the fork owners is a real rung.** It is the one step with no technical gate, which is
exactly why it gets skipped. If it does get skipped, record it as skipped — a fork pointing at
a commit that is no longer on the default branch is confusing, and the owner deserves to hear
it from you rather than from a diff of thousands of commits.
