#!/usr/bin/env python3
"""Find personal, account and secret data in a git repository's committed content.

Scopes (pick one; default --tree HEAD):
  --tree REF        every line of every text file at REF
  --range A..B      lines added by the commits in A..B, plus their commit messages
  --staged          lines added in the index (pre-commit check)
  --history         lines added anywhere in history (all refs), with the commit that added them

Categories, reported in this priority order (one row per line per category):
  secret     private keys, provider tokens (ghp_, github_pat_, sk-, xox?-, AKIA, AIza),
             password/secret/token/api_key = "<long literal>"
  email      any email address not allowlisted
  account    HPC/Slurm accounts (auto-detected with sacctmgr/sshare) and --term values
  usage      allocation usage figures: fairshare numbers, "balance is N", "N GPU-hours left"
  user-path  filesystem paths containing the username (/u/USER, /work/x/proj/USER, ...)
  username   the bare username anywhere else
  site-path  heuristic: a concrete cluster path that names a project or a person
             (/scratch/<proj>/<someone>, /work/nvme/<proj>/..., /home/<someone>) even when
             no identity term is known -- e.g. a teammate's or staff member's directory.
             Paths built from variables or placeholders ($USER, <project>, {x}) are skipped.

Slurm account prefixes are searched too: abcd-delta-gpu also yields the bare token "abcd",
which is how allocations appear in paths such as /work/nvme/abcd/$USER.

Each finding in --tree/--range/--staged is marked pushed/unpushed by checking whether the
same line already exists in that file at the upstream ref (default @{u}).  The script warns
when the local tracking ref differs from the remote's real tip (git ls-remote), because a
stale ref silently misclassifies commits.

Allowlist: built-in defaults (noreply addresses, example.* domains, <placeholders>) plus
optional .sensitive-scan-allow at the repo root, or --allow FILE.  Each non-comment line is a
Python regex searched in "PATH:MATCH"; e.g.  ^pyproject\\.toml:.*@  allows author emails there.

Exit status: 0 = clean, 1 = findings, 2 = usage/git error.  Stdlib only.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

DEFAULT_ALLOW = [
    r"noreply@",                         # bot / co-author trailers
    r"@example\.(com|org|net|edu)\b",
    r":you@",                            # placeholder mailbox
    r"<[^<>\n]{1,40}>",                  # <project>, <your-email>, ...
]

SECRET_RES = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bghp_[A-Za-z0-9]{20,}",
    r"\bgithub_pat_[A-Za-z0-9_]{20,}",
    r"\bsk-[A-Za-z0-9_-]{20,}",
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bAIza[0-9A-Za-z_-]{35}\b",
    r"(?i:\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b)"
    r"[\"' ]*[:=][ ]*[\"'][^\"'\s]{8,}[\"']",
]
EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
# Cluster filesystem roots under which the next segment(s) name a project or a person.
SITE_PATH_RE = r"/(?:scratch|projects|home|u|work)/[^\s`'\"),;:]+"
GENERIC_ACCOUNTS = {"noalloc", "default", "none", "root", "general"}
USAGE_RES = [
    r"(?i:\bfair-?share\b)[^0-9\n]{0,15}[0-9]*\.[0-9]+",
    r"(?i:\bbalance\b)[^0-9\n]{0,20}[0-9][0-9,]{2,}",
    r"\b[0-9][0-9,]{2,}\s*(?i:(GPU|CPU|SU|node)[- ]?hours?\s*(left|remaining|balance|allocated))",
]


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       errors="replace")
    if check and p.returncode not in (0, 1):
        sys.exit(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def auto_terms():
    """Identity terms of the person running the scan."""
    accounts, emails = set(), set()
    for scope in ([], ["--global"]):
        e = subprocess.run(["git", "config", *scope, "user.email"], capture_output=True,
                           text=True).stdout.strip()
        if e:
            emails.add(e)
    user = os.environ.get("USER", "")
    if shutil.which("sacctmgr"):
        out = subprocess.run(["sacctmgr", "-nP", "show", "assoc", f"where user={user}",
                              "format=account"], capture_output=True, text=True).stdout
        accounts |= {a.strip() for a in out.split() if a.strip()}
    if not accounts and shutil.which("sshare"):
        out = subprocess.run(["sshare", "-U", "-h", "-o", "Account"], capture_output=True,
                             text=True).stdout
        accounts |= {a.strip() for a in out.split() if a.strip()}
    accounts -= GENERIC_ACCOUNTS
    # The allocation prefix (abcd in abcd-delta-gpu) is what appears in project paths.
    prefixes = {a.split("-")[0] for a in accounts if "-" in a}
    accounts |= {p for p in prefixes if len(p) >= 3 and p not in GENERIC_ACCOUNTS}
    return emails, accounts, (user if len(user) >= 3 and user != "root" else "")


def build_rules(emails, accounts, terms, user):
    rules = [("secret", re.compile("|".join(f"(?:{r})" for r in SECRET_RES)))]
    rules.append(("email", re.compile(EMAIL_RE)))
    acct = sorted(accounts | set(terms), key=len, reverse=True)
    if acct:
        rules.append(("account", re.compile(
            "|".join(rf"(?<![A-Za-z0-9]){re.escape(a)}(?![A-Za-z0-9])" for a in acct))))
    rules.append(("usage", re.compile("|".join(f"(?:{r})" for r in USAGE_RES))))
    if user:
        u = re.escape(user)
        rules.append(("user-path", re.compile(rf"(?:/[A-Za-z0-9._-]+)*/{u}(?=/|\b)")))
        rules.append(("username", re.compile(rf"(?<![A-Za-z0-9]){u}(?![A-Za-z0-9])")))
    rules.append(("site-path", re.compile(SITE_PATH_RE)))
    return rules


def site_path(token):
    """Return the identifying prefix of a concrete cluster path, or None if it is generic."""
    if any(c in token for c in "$<{") or "example" in token:
        return None
    segs = [x for x in token.split("/") if x]
    # /work/nvme/<proj>/... and /work/hdd/<proj>/...: the filesystem layer is not identifying.
    need = 3 if segs[0] == "work" and len(segs) > 1 and segs[1] in ("nvme", "hdd") else 2
    if len(segs) < need:
        return None
    return "/" + "/".join(segs[:need + 1])


def load_allow(repo, extra):
    pats = list(DEFAULT_ALLOW)
    for f in [os.path.join(repo, ".sensitive-scan-allow"), extra]:
        if f and os.path.isfile(f):
            for line in open(f):
                line = line.strip()
                if line and not line.startswith("#"):
                    pats.append(line)
    return [re.compile(p) for p in pats]


def classify(path, text, rules, allow):
    """Yield (category, match) for each category whose first non-allowlisted match is found."""
    hit = set()
    for cat, rx in rules:
        if cat == "username" and "user-path" in hit:
            continue                     # same name already reported inside the path
        if cat == "site-path" and hit & {"user-path", "account"}:
            continue                     # the line is already flagged more specifically
        for m in rx.finditer(text):
            s = m.group(0)
            if cat == "site-path":
                s = site_path(s)
                if s is None:
                    continue
            if any(a.search(f"{path}:{s}") for a in allow):
                continue
            hit.add(cat)
            yield cat, s
            break


def mask(cat, s):
    if cat == "secret":
        return s[:4] + "…(masked)"
    return s if len(s) <= 100 else s[:97] + "..."


# ── content sources ───────────────────────────────────────────────────────────

def lines_tree(repo, ref):
    out = subprocess.run(["git", "-C", repo, "grep", "-n", "-I", "--null", "-e", ".", ref,
                          "--", "."], capture_output=True, text=True, errors="replace").stdout
    for rec in out.splitlines():
        # --null separates both the file name and the line number with NUL.
        name, _, rest = rec.partition("\0")
        lineno, _, text = rest.partition("\0")
        path = name.split(":", 1)[1] if name.startswith(ref + ":") else name
        yield path, lineno, text, None


def lines_diff(repo, args, commit=None):
    out = git(repo, "diff", "-U0", "--no-color", "--no-ext-diff", *args)
    path, newline = None, 0
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            newline = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            yield path, str(newline), line[1:], commit
            newline += 1


def lines_messages(repo, rng):
    out = git(repo, "log", "--format=%x00%h%n%B", rng)
    for block in out.split("\0")[1:]:
        sha, _, body = block.partition("\n")
        for i, text in enumerate(body.splitlines(), 1):
            yield f"(commit message {sha})", str(i), text, sha


def lines_history(repo):
    out = git(repo, "log", "--all", "--reverse", "-p", "-U0", "--no-color",
              "--format=%x00COMMIT %h")
    commit, path, newline = None, None, 0
    for line in out.splitlines():
        if line.startswith("\0COMMIT "):
            commit = line.split()[1]
        elif line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            newline = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            yield path, str(newline), line[1:], commit
            newline += 1


# ── upstream classification ───────────────────────────────────────────────────

def resolve_upstream(repo, arg):
    if arg == "none":
        return None
    ref = arg or "@{u}"
    sha = git(repo, "rev-parse", "--verify", "-q", ref, check=False).strip()
    if not sha:
        print(f"note: no upstream ({ref}); pushed/unpushed not classified", file=sys.stderr)
        return None
    # Warn if the tracking ref is stale versus the real remote tip.
    name = git(repo, "rev-parse", "--abbrev-ref", ref, check=False).strip()
    if "/" in name:
        remote, branch = name.split("/", 1)
        try:
            p = subprocess.run(["git", "-C", repo, "ls-remote", remote, f"refs/heads/{branch}"],
                               capture_output=True, text=True, timeout=20)
            tip = p.stdout.split()[0] if p.stdout.split() else ""
            if tip and tip != sha:
                print(f"WARNING: {name} is {sha[:7]} locally but the remote tip is {tip[:7]}; "
                      f"run `git fetch {remote}` or the pushed/unpushed split is wrong",
                      file=sys.stderr)
        except Exception:
            print("note: could not reach the remote to check the tracking ref is current",
                  file=sys.stderr)
    return sha


class Upstream:
    def __init__(self, repo, sha):
        self.repo, self.sha, self.cache = repo, sha, {}

    def has(self, path, text):
        if self.sha is None:
            return None
        if path.startswith("(commit message"):
            # A message is published iff its commit is already in the upstream history.
            sha = path.split()[-1].rstrip(")")
            return subprocess.run(["git", "-C", self.repo, "merge-base", "--is-ancestor",
                                   sha, self.sha], capture_output=True).returncode == 0
        if path not in self.cache:
            self.cache[path] = set(git(self.repo, "show", f"{self.sha}:{path}",
                                       check=False).splitlines())
        return text in self.cache[path]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-C", "--repo", default=".")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--tree", metavar="REF")
    g.add_argument("--range", metavar="A..B")
    g.add_argument("--staged", action="store_true")
    g.add_argument("--history", action="store_true")
    ap.add_argument("--upstream", metavar="REF", default="",
                    help="ref treated as published (default @{u}; 'none' to skip)")
    ap.add_argument("--term", action="append", default=[],
                    help="extra identifier to flag as 'account' (repeatable)")
    ap.add_argument("--no-auto", action="store_true",
                    help="do not auto-detect git email, $USER or Slurm accounts")
    ap.add_argument("--allow", metavar="FILE", help="extra allowlist file")
    a = ap.parse_args()

    repo = git(a.repo, "rev-parse", "--show-toplevel").strip()
    if not repo:
        sys.exit(2)
    emails, accounts, user = (set(), set(), "") if a.no_auto else auto_terms()
    rules = build_rules(emails, accounts, a.term, user)
    allow = load_allow(repo, a.allow)
    print(f"identity terms: user={user or '-'} accounts={sorted(accounts) or '-'} "
          f"extra={a.term or '-'}", file=sys.stderr)

    if a.history:
        src, up = lines_history(repo), None
    elif a.staged:
        src, up = lines_diff(repo, ["--cached"]), Upstream(repo, resolve_upstream(repo, a.upstream))
    elif a.range:
        def both():
            yield from lines_diff(repo, [a.range])
            yield from lines_messages(repo, a.range)
        src, up = both(), Upstream(repo, resolve_upstream(repo, a.upstream))
    else:
        ref = a.tree or "HEAD"
        src, up = lines_tree(repo, ref), Upstream(repo, resolve_upstream(repo, a.upstream))

    seen, rows = set(), []
    for path, lineno, text, commit in src:
        for cat, s in classify(path, text, rules, allow):
            if a.history:
                key = (cat, s, path)            # first introduction only
                if key in seen:
                    continue
                seen.add(key)
                status = commit
            else:
                pushed = up.has(path, text) if up else None
                status = "-" if pushed is None else ("pushed" if pushed else "unpushed")
            rows.append((cat, status, f"{path}:{lineno}", mask(cat, s)))

    order = ["secret", "email", "account", "usage", "user-path", "username", "site-path"]
    rows.sort(key=lambda r: (order.index(r[0]), r[2]))
    head = ("CATEGORY", "COMMIT" if a.history else "STATUS", "LOCATION", "MATCH")
    if rows:
        print("\t".join(head))
        for r in rows:
            print("\t".join(r))
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print(f"findings: {len(rows)} " + " ".join(f"{k}={v}" for k, v in counts.items()),
          file=sys.stderr)
    sys.exit(1 if rows else 0)


if __name__ == "__main__":
    main()
