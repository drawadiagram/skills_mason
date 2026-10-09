---
name: repo-sensitive-scan
description: Check a git repository's committed content for personal and account data before it spreads — personal email addresses, HPC/Slurm account and allocation names, allocation balances or fairshare figures, usernames and home/project paths, public addresses of self-hosted machines (IPv4, IPv6 and the dashed reverse-DNS spelling), and secrets such as tokens or private keys. Scans binary build artifacts too (.pptx/.docx/.xlsx/.pdf) by decoding their containers. Classifies every finding as already pushed or still local, reports whether each remote is public, finds the commit that introduced it, and proposes fixes (placeholders, disabled #SBATCH lines, rotation, history rewrite for unpushed commits only). Use this whenever the user asks to verify, audit, scan, or scrub a repo, branch, commit range, or staged change for PII, emails, accounts, allocations, usernames, paths, IP addresses, credentials or "anything personal"; before a push or PR when they ask whether it is safe to publish; and whenever a repository is being moved, renamed, open-sourced, or migrated to a public or organisational home — even if they only say "make sure nothing private got committed".
---

# Scanning a repo for personal and account data

The question behind this check is always "what will other people be able to read, and what is
already out of my hands?". So a finding is only useful with two facts attached: **where** it is,
and **whether it has been pushed**. Unpushed content can be cleaned so that it never existed;
pushed content can only be fixed going forward unless someone decides to force-push.

## 1. Get the truth about the remote first

```bash
git fetch <remote>          # or at least: git ls-remote <remote> refs/heads/<branch>
gh repo view <owner/repo> --json visibility     # the scanner prints this for every remote
```

A stale remote-tracking ref silently misclassifies commits. In the session this skill came from,
`origin/scaling-wide` was 3 commits behind the real remote tip because the branch had been pushed
from a different checkout; without the check, 8 commits looked unpushed when only 5 were. The
scanner prints a WARNING when the tracking ref differs from `ls-remote`. Do not ignore it.

**Then ask where "pushed" goes.** Pushed and exposed are not the same thing, and the pushed/unpushed
split invites the wrong triage on its own: a finding is urgent on a public repo and merely untidy on
a private one. On the repo the host-address rule came from, every identifier was already
world-readable because the remote was public — which did not make the findings less real, but it did
change the remedy from "rewrite the history" to "rotate the value and stop re-introducing it".
The scanner masks any userinfo in a remote URL before printing it, because `https://user:token@host/…`
is a real way people store credentials and this output gets pasted into reports; do the same by hand
if you quote a remote anywhere.

**A repo changing homes is a publication event.** Moving a tree from a personal or private repo into
a public or organisational one republishes everything it carries, including anything a previous pass
judged acceptable for a narrower audience. Scan against the *destination's* readers, not the
source's, and re-judge the accepted items — ask before the push, not after.

## 2. Run the scanner

```bash
S=~/.claude/skills/repo-sensitive-scan/scripts/scan_sensitive.py
python3 $S -C <repo>                         # every line at HEAD, pushed/unpushed vs @{u}
python3 $S -C <repo> --range @{u}..HEAD      # only what the unpushed commits add, + their messages
python3 $S -C <repo> --staged                # pre-commit check
python3 $S -C <repo> --history               # all refs; reports the commit that introduced each item
python3 $S -C <repo> --term mylab-gpu --term "Jane Doe"   # extra identifiers
python3 $S -C <repo> --no-binary             # skip the zip/PDF-aware pass over binary blobs
```

It auto-detects the identity to look for — `git config user.email`, `$USER`, and the user's Slurm
accounts (`sacctmgr ... format=account`, falling back to `sshare -U`) — and prints them on stderr
so you can see what was searched. Exit status: 0 clean, 1 findings, 2 error. Secrets are masked in
the output; never print one in full in your reply either.

Masking does not key on the category, because the category does not know. A credentialed URL in a
committed file matches `EMAIL_RE` as `ghp_…@github.com`, so it used to be masked on the `secret` row
and printed in full on the `email` row of the same line; and a password recognisable only by its
position — `https://admin:Hunter2@git.example.org` — had no token prefix to catch at all. Userinfo is
now redacted from a line before any rule but `secret` sees it, and every match is checked against the
secret patterns whatever reported it.

Categories, in priority order: `secret`, `email`, `account`, `usage` (fairshare numbers,
"balance is N", "N GPU-hours left"), `user-path` (paths containing the username), `username`,
`site-path`, and `host-addr` — a public address of a machine you run.

`host-addr` matters more than it sounds, because a self-hosted VM's address is the one identifier
that is both operational and personal, and it hides in **three** spellings:

- dotted IPv4, `203.0.113.10`;
- global IPv6, including a `/64` the provider assigned;
- the **dashed reverse-DNS name**, `203-0-113-10.ip.example.net`, which no dotted-quad pattern
  matches and which is very often the live URL with the certificate issued for it. On the repo this
  came from, a hand-written dotted-quad grep found 8 occurrences and missed 5 of these.

Unroutable and documentation ranges are skipped (loopback, RFC 1918, link-local, CGNAT, multicast,
RFC 5737), so a finding is an address that names a real machine. A CIDR suffix travels with the
match, so an allow-list rule reports as `198.51.100.0/24` rather than a bare address.

**Use RFC 5737 ranges in your own examples** — `203.0.113.0/24`, `198.51.100.0/24` — and never a
real value. Writing up a redaction is a place the value comes back: this skill and the plan doc that
recorded the work both quoted the live reverse-DNS name while explaining why it is easy to miss, in
two repositories that are themselves public. Neither was pushed, and a scan would not have caught
it, because the prose had only just been written. The documentation ranges are excluded by the
filter above, so an example can never read as a finding.

The one false positive left is a **four-part version string**: `1.2.3.4` is indistinguishable from an
address, and nothing in the line reliably says which it is. Three-part versions (`3.12.13`) and
timestamps (`05:14:33`) are already excluded. Allowlist the few that come up rather than widening
the filter — guessing from context is how a real address gets skipped.

**The binary pass is container-aware, and that is the whole point.** A `.pptx`, `.docx` or `.xlsx` is
a zip of XML parts and a PDF keeps its text in deflate streams, so the bytes on disk are not the
text. Grepping the blob raw fails in both directions, and both were seen in one session: `git grep`
reported a committed `.pptx` as matching a dotted-quad regex, which read as "the address is baked
into the deck" and bought an hour of scoping a rebuild — the document does not contain it, the match
was compressed noise. Had the address really been in there, a scan passing `git grep -I` would have
said nothing at all. Report what the *decoded* content says, and name the part (`deck.pptx [slide3.xml]`).

It decodes whatever a repository contains, including one just cloned and not trusted, so the pass is
bounded: **64 MB of decoded text per blob**, plus 16 MB per part, 5000 parts, and blobs over 128 MB
skipped. The per-blob budget is the one that does the work — capping part size and part count
separately leaves their *product* unbounded, and a 12 MB zip of 200 members decoded to 3200 MB with
both of the others respected. When a cap truncates something it says so on stderr: **do not read
that as clean**, and re-check the file by hand if it matters. Every cap, unreadable member and
non-deflate PDF stream prints an `INCOMPLETE:` line naming the file and the reason, so partial
coverage is stated rather than implied by silence.

**It fails closed, and so should your reading of it.** A git failure now exits 2 with git's own
message. That matters more than it sounds: a mistyped ref made `git grep` produce nothing, which was
reported as `findings: 0` and exit 0 — a clean bill of health from a command that never ran. Check
the exit status (0 clean, 1 findings, 2 error) rather than eyeballing the output, and never report
"nothing found" from a run that printed an error or an `INCOMPLETE:` line.

Two more bounds exist because the obvious implementation defeats them: a `stream(.*?)endstream` regex
over a blob with many `stream` tokens and no `endstream` rescans to the end from each one (64k tokens
did not finish in 300 s, and no decompression cap helps, because the regex cost comes first — use
`str.find`), and a `strings`-style fallback over a 128 MB blob builds a 128 MB string. In the same
family, the tree and history readers stream git's output rather than buffering it, so peak memory is
a property of this script and not of the repository being scanned.

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

**A colleague's identifier is the one an identity scan cannot see**, and it is usually the one that
has spread furthest, because it got there as an *example*. On the repo the host-address rule came
from, another person's cluster account was the example value in a form the application **prints on
screen**, and from there into 28 test fixtures: 30 occurrences, every one invisible to a scan keyed
on `git config user.email` and `$USER`. So:

- pass collaborators' usernames and account ids with `--term` — ask the user for them by role
  ("whose netids appear in this repo?"), not by guessing;
- read example, placeholder and fixture values as carefully as live ones. "It's only a test fixture"
  is about *blast radius*, not about whether it identifies someone;
- when you replace one, keep the shape valid. A fixture that asserts on a rendered path needs a
  substitute the validator accepts, or the test starts lying about what the code produces.

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
