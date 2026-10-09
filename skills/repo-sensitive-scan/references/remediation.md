# Remediation recipes

## Placeholders that keep things working

| Item | Replace with | Why |
|---|---|---|
| `#SBATCH --mail-user=me@uni.edu` | `##SBATCH --mail-user=you@example.edu` | `##` disables the directive. Do **not** leave an active `#SBATCH --mail-user=<your e-mail>`: sbatch parses the space and treats `e-mail>` as a directive (`Invalid directive found in batch script`), so the script cannot be submitted at all |
| `#SBATCH --account=abcd-delta-gpu` | `##SBATCH --account=<project>-delta-gpu` and rely on `SBATCH_ACCOUNT` / `sbatch --account=` | sbatch honours `SBATCH_ACCOUNT` and the CLI flag over the script; scripts can warn when neither is set |
| `export SBATCH_ACCOUNT=abcd-delta-gpu` in docs/echo | `<project>-delta-gpu` | |
| `/work/nvme/abcd/jdoe/...`, `/scratch/abcd/jdoe` | `$WORK_DIR/...`, `/scratch/<project>/$USER` | keeps the example runnable |
| `/u/jdoe`, `/home/jdoe` | `~` or `$HOME` | |
| allocation balance / fairshare numbers | drop the number ("the allocation balance", "higher / lower fairshare") | usage figures are account data even without the name |
| two named allocations being compared | `<allocation A>` / `<allocation B>` | keeps the comparison, drops the identifiers |

**Never put `<placeholder>` in an executable shell line.** In `source /x/<project>/$USER/env` or
`DIR=/x/<project>/y`, bash reads `<project` as input redirection and `>/...` as output redirection
— `bash -n` accepts it, and running it can create or truncate files. In executed lines use a
variable that fails loudly when unset: `/x/${PROJECT:?set PROJECT to your allocation}/$USER/env`,
and `$HOME` instead of a literal home directory. `<...>` is fine in comments, quoted `echo`
strings, Markdown prose, Python string constants and requirements files.

**Scan your own fix commit, message included** (`--range UP..HEAD`): it is easy to quote the very
value being removed in the commit message ("replace /work/nvme/abcd/... with ..."). Amend while it
is unpushed.

A user's personal working-copy edit (e.g. their own `#SBATCH --account=` line) must stay
uncommitted. If a commit has to include other changes to that file, temporarily restore the
committed line, `git add`, then put their line back — and say so.

## Rewriting only the unpushed commits

Precondition: the remote tip is known (`git ls-remote`). Call it `UP`; the unpushed commits are
`UP..BRANCH`. If `UP` is not an ancestor of `BRANCH`, stop and ask.

1. Save the user's uncommitted changes as a patch (`git diff > /tmp/x.patch`), then
   `git checkout -- <those files>`; the tree must be clean.
2. Write the scrub as an **idempotent** script `S` (ordered regex replacements over tracked text
   files; a `--stdin` mode for commit messages). Idempotent matters: it runs on every commit.
3. Fix commit on top of the published tip, in a separate worktree so the user's checkout is
   untouched:
   ```bash
   git worktree add /tmp/fix UP && (cd /tmp/fix && python3 S && git commit -qam "Remove personal email, allocation names and user paths")
   F=$(git -C /tmp/fix rev-parse HEAD)
   ```
4. Re-parent and filter the unpushed range onto `F`:
   ```bash
   git filter-branch -f \
     --parent-filter "sed s/$(git rev-parse UP)/$F/" \
     --tree-filter 'python3 S' \
     --msg-filter 'python3 S --stdin' \
     -- BRANCH --not UP
   ```
   Because every rewritten tree is fully scrubbed and `F` already is, each commit's diff stays its
   own change. Merge commits inside the range are handled; their other parents are kept.
5. Verify: scanner on `--range UP..BRANCH` (includes messages) and `--tree HEAD` → zero findings;
   `git diff <old-HEAD> HEAD` shows only the replacements; compile/lint anything touched.
6. Clean up: `git update-ref -d refs/original/refs/heads/BRANCH`, `git worktree remove /tmp/fix`,
   re-apply the user's patch. The old commits remain only in the local reflog, which is never pushed.

Do not push. Report old → new SHAs.

## Pushed history

A new commit fixes HEAD; the old values remain readable in published commits and in every clone and
fork. Removing them means rewriting the published branch (e.g. `git filter-repo --replace-text`)
and force-pushing, which breaks everyone else's checkouts and does not reach forks or caches. That
is a decision for the repository owner; describe it, never do it unasked. If a **secret** was
pushed, rotating the secret matters more than rewriting history.

## Build artifacts (`.pptx`, `.docx`, `.xlsx`, `.pdf`)

**Regenerate it from redacted sources; never edit the blob.** These are containers — a zip of XML
parts, or deflate streams — so a byte-level substitution either corrupts the archive (a replacement
of a different length invalidates the entry's stored sizes and CRC) or silently misses the value
because it is compressed. Find the generator, fix the string there, re-run it, and commit the new
artifact. Then re-scan: the pass over binaries decodes containers, so it reads what the document
actually says.

Also check whether the artifact belongs in git at all. A regenerable file that carries identifiers
is worth `.gitignore`-ing and attaching to a release instead, so the next regeneration cannot
re-publish something.

## Host addresses

Rotating beats rewriting. An address in published history cannot be recalled, and unlike a token it
is also a fact about infrastructure other people can observe — so the fix that actually reduces
exposure is a firewall rule, a new address, or putting the host behind a name you control, not a
`filter-repo` run. Do both only if the owner wants the history clean for its own sake.

Replace with a placeholder that keeps the document usable: `<linode-ip>`, `<campus-block>`. Give the
doc **one key** defining every placeholder, in the file a deployer reads, so the substitution is
mechanical for whoever has the real values. Remember all three spellings — dotted, IPv6, and the
dashed reverse-DNS name — and that the reverse name is often the URL in the docs and the subject of
the TLS certificate.
