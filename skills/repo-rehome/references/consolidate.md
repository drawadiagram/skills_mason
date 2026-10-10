# Consolidate: fold one repo into another, keeping its history

Use when two repos should become one — a library absorbed into the application that is its
only consumer, several sibling projects gathered into a monorepo — and the incoming history
should stay readable afterwards.

Nothing here is destructive to the destination: it all lands as ordinary commits on a branch
you can review and discard. The decision that matters is made before any of it.

## First, decide whether history should come

Be honest about who will read it. Three outcomes are all legitimate:

- **Full history under a subdirectory.** Every commit of the incoming repo stays reachable
  and `git log -- path/` works. Costs: the destination's history becomes interleaved and
  `git log` without a path is noisier.
- **A single squashed commit** that imports the current state, with the old repo archived and
  linked from the commit message. Much simpler, and usually the right answer when the
  incoming repo's history is a few months of one person's work that nobody will bisect.
- **History left behind entirely**, archiving the source repo read-only as the record. Choose
  this and say so explicitly in the commit, so a later reader does not assume it was lost.

Prefer the squash or the archive unless someone will plausibly `git blame` or `git bisect`
the incoming code. Full-history merges are frequently done out of a sense of duty and then
never used, and they are the option that permanently complicates the destination's log.

## Full history under a subdirectory

The incoming repo's files must end up in a subdirectory, and the cleanest way is to move them
*in its own history* first, so the merge does not need path rewriting:

```bash
# in a scratch clone of the SOURCE
git clone https://github.com/jdoe/widget-lib.git /tmp/widget-lib && cd /tmp/widget-lib
git filter-repo --to-subdirectory-filter lib/widget      # needs git-filter-repo
```

`git-filter-repo` is a separate install (`pipx install git-filter-repo`, or your package
manager). Without it, `git merge -X subtree=` can sometimes infer the shift, but it guesses;
rewriting the source first is predictable, and the source clone is disposable.

Then, in the destination:

```bash
git remote add widget-lib /tmp/widget-lib
git fetch widget-lib
git switch -c consolidate-widget-lib
git merge --allow-unrelated-histories widget-lib/main -m "Fold widget-lib into lib/widget

Its history comes with it, rewritten so every commit touches lib/widget/.
Source repo jdoe/widget-lib is archived at <sha>."
git remote remove widget-lib
```

`--allow-unrelated-histories` is required and is the point: git refuses by default precisely
because merging two unrelated roots is usually a mistake. Being explicit is the safeguard.

Verify before opening the PR:

```bash
git log --oneline -- lib/widget | tail -5      # the incoming history is reachable by path
git log --oneline -1                           # one merge commit on your branch
ls lib/widget                                  # files where you meant them
```

## Squashed import

```bash
git switch -c import-widget-lib
git archive --remote=https://github.com/jdoe/widget-lib.git main | tar -x -C lib/widget
# or just copy from a clone, minus its .git
git add lib/widget && git commit   # message names the source repo and the exact commit
```

Record the source commit SHA in the message. It is the whole audit trail, and it costs one
line.

## After either

- **Archive the source**, do not delete it: `gh repo archive jdoe/widget-lib --yes`. Read-only
  preserves the issues and the history at a stable URL that your commit message points at.
  Before archiving, make sure its HEAD is the state you want frozen.
- **Move the issues you still care about** by hand. Nothing migrates them; `gh issue transfer
  <n> octo-lab/widget` moves one at a time and is worth it for a handful.
- **Redirect the consumers.** Anything that depended on the source as a package or submodule
  now needs the new path. A submodule in particular keeps working while pointing at an
  archived repo, so it fails quietly later rather than loudly now — grep for `.gitmodules`
  and for the old URL across your own repos.
- **Check CI.** Paths moved, so test discovery, coverage config, lint excludes and build
  globs that named the old layout all need updating. This is usually the bulk of the real
  work and is invisible until the first run.
