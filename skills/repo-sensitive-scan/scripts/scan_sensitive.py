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
  host-addr  a public address of a machine you run: IPv4, global IPv6, and the *dashed*
             reverse-DNS spelling (203-0-113-10.ip.example.net), which a dotted-quad
             pattern does not match and which is often the live URL.  Loopback, RFC 1918,
             link-local, CGNAT, multicast and the RFC 5737 documentation ranges are skipped.

Slurm account prefixes are searched too: abcd-delta-gpu also yields the bare token "abcd",
which is how allocations appear in paths such as /work/nvme/abcd/$USER.

Binary files are scanned with container awareness (--no-binary to skip): zip-based formats
(pptx/docx/xlsx) are opened member by member and PDF streams are inflated, because the bytes
on disk are not the text.  A raw byte grep over a compressed blob fails both ways -- it
misses real matches, and a dotted-quad regex matching compressed bytes reports an address
that is not in the document.  Both were seen on the repo this pass came from.

Each finding in --tree/--range/--staged is marked pushed/unpushed by checking whether the
same line already exists in that file at the upstream ref (default @{u}).  The script warns
when the local tracking ref differs from the remote's real tip (git ls-remote), because a
stale ref silently misclassifies commits, and reports each remote's visibility when `gh` is
available: "pushed" to a public repo and to a private one are different findings.

Allowlist: built-in defaults (noreply addresses, example.* domains, <placeholders>) plus
optional .sensitive-scan-allow at the repo root, or --allow FILE.  Each non-comment line is a
Python regex searched in "PATH:MATCH"; e.g.  ^pyproject\\.toml:.*@  allows author emails there.

Exit status: 0 = clean, 1 = findings, 2 = usage/git error.  Stdlib only.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import zipfile
import zlib

DEFAULT_ALLOW = [
    r"noreply@",                         # bot / co-author trailers
    r"@example\.(com|org|net|edu)\b",
    r":you@",                            # placeholder mailbox
    r"<[^<>\n]{1,40}>",                  # <project>, <your-email>, ...
    r"^\.sensitive-scan-allow:",         # the allowlist's own patterns quote what they allow
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
    # scheme://user:password@host -- a credential by position, whatever it looks like.
    r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:@]+:[^\s/@]+@",
]
# The same, for redacting the userinfo out of a line before the lower-priority rules run.
URL_CRED_RE = re.compile(r"(\b[a-zA-Z][a-zA-Z0-9+.-]*://)[^\s/:@]+:[^\s/@]+@")
EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
# Cluster filesystem roots under which the next segment(s) name a project or a person.
SITE_PATH_RE = r"/(?:scratch|projects|home|u|work)/[^\s`'\"),;:]+"
GENERIC_ACCOUNTS = {"noalloc", "default", "none", "root", "general"}
# Ceilings for the binary pass. It decodes whatever a repository contains, which may be a
# repo you have just cloned and do not trust, so a compression bomb has to truncate rather
# than exhaust memory. Generous enough that a real document is read whole.
MAX_PART = 16 << 20      # decompressed bytes per zip member or PDF stream
MAX_BLOB = 128 << 20     # a committed blob larger than this is not decoded at all
MAX_PARTS = 5000         # members or streams examined per blob
# The budget that actually bounds the work. Capping per-part size and part count separately
# leaves their product unbounded: 200 members of 64 MB of zeros is a 12 MB zip that decoded
# to 3200 MB of text, every byte of it regex-scanned, with both other caps respected.
MAX_TOTAL = 64 << 20     # decompressed bytes per blob, across all its parts


def printable(data, limit=MAX_PART):
    """The printable runs of a blob, as `strings` would give them, capped at `limit`.

    Capped because this is the fallback for every unrecognised binary and the PDF tail: a
    128 MB blob would otherwise build a 128 MB string, which defeats the point of MAX_PART.
    """
    out, left = [], min(MAX_PART, limit)
    for run in re.finditer(rb"[\x20-\x7e]{6,}", data):
        s = run.group(0)[:left]
        out.append(s.decode("ascii"))
        left -= len(s) + 1
        if left <= 0:
            break               # truncate the run, never drop it: the cap is on volume,
    return "\n".join(out)       # and a value in the first MAX_PART still has to be found
# A machine's public address, in the three spellings it actually appears in.  The dashed form
# is a reverse-DNS name (203-0-113-10.ip.example.net) and is frequently the live
# URL; no dotted-quad pattern finds it.  IPv6 requires "::" or a full eight groups, so that
# a timestamp like 05:14:33 cannot match.
HOST_RES = [
    r"(?<![0-9A-Za-z.-])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?(?![0-9A-Za-z.-])",
    r"(?<![0-9A-Za-z.-])(?:[0-9]{1,3}-){3}[0-9]{1,3}\.[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
    r"(?<![0-9A-Za-z:])(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}(?![0-9A-Za-z:])",
    r"(?<![0-9A-Za-z:])[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4})*::"
    r"(?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4})*)?(?:/[0-9]{1,3})?",
]
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
    rules.append(("host-addr", re.compile("|".join(f"(?:{r})" for r in HOST_RES))))
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


def host_address(token):
    """Return a public machine address, or None for a private/reserved one or a non-address.

    The quad spellings share one filter: dashes become dots and the same ranges are skipped.
    Everything excluded here is either unroutable (so it names no machine of yours) or
    reserved for documentation (so it is already a placeholder).
    """
    quad = token.split("/")[0]
    if "." in token and token[0].isdigit() and "-" in token.split(".")[0]:
        quad = token.split(".")[0].replace("-", ".")     # the reverse-DNS spelling
    parts = quad.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        o = [int(p) for p in parts]
        if any(x > 255 for x in o):
            return None                                  # a version string, not an address
        if any(len(p) > 1 and p[0] == "0" for p in parts):
            return None                                  # zero-padded: not an address
        if (o[0] in (0, 10, 127) or o[0] >= 224
                or (o[0] == 172 and 16 <= o[1] <= 31)
                or (o[0] == 192 and o[1] == 168)
                or (o[0] == 169 and o[1] == 254)
                or (o[0] == 100 and 64 <= o[1] <= 127)
                or (o[0] == 198 and o[1] in (18, 19))
                or (o[0] == 192 and o[1] == 0 and o[2] == 2)
                or (o[0] == 198 and o[1] == 51 and o[2] == 100)
                or (o[0] == 203 and o[1] == 0 and o[2] == 113)):
            return None
        return token
    if ":" in token:
        head = token.split("/")[0].strip(":").lower()
        if head in ("", "1") or token.lower().startswith(("fe80:", "fc", "fd", "::ffff:")):
            return None                                  # loopback, link-local, ULA, mapped
        if not re.search(r"[0-9A-Fa-f]", head):
            return None
        return token
    return None


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
    """Yield (category, match) for each category whose first non-allowlisted match is found.

    A URL's userinfo is redacted before any rule but `secret` sees the line.  Otherwise the
    password in `https://admin:Hunter2@git.example.org/r` comes back as the `email` match
    `Hunter2@git.example.org` and gets printed in full, because it is only recognisable as a
    credential by its position -- no token prefix, no `password=` to key on.  The `secret`
    rule matches the whole `scheme://user:pass@` and is masked.
    """
    safe = URL_CRED_RE.sub(r"\1***@", text)
    hit = set()
    for cat, rx in rules:
        if cat != "secret":
            text = safe
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
            if cat == "host-addr":
                s = host_address(s)
                if s is None:
                    continue
            if any(a.search(f"{path}:{s}") for a in allow):
                continue
            hit.add(cat)
            yield cat, s
            break


SECRET_ANY = re.compile("|".join(f"(?:{r})" for r in SECRET_RES))


def mask(cat, s):
    """Render a match for the report, never revealing a credential.

    The category is not enough to decide this.  A credentialed remote in a committed file --
    `https://user:ghp_…@github.com/o/r` -- matches EMAIL_RE as `ghp_…@github.com`, so keying
    the mask on cat == "secret" printed the token in full on the `email` row while masking it
    on the `secret` row of the same line.  So every match is checked for a secret.
    """
    if cat == "secret" or SECRET_ANY.search(s):
        return s[:4] + "…(masked)"
    return s if len(s) <= 100 else s[:97] + "..."


# ── content sources ───────────────────────────────────────────────────────────

def git_lines(repo, *args, ok=(0,)):
    """Stream a git command's stdout a line at a time, and fail loudly if it fails.

    Not capture_output: `git grep` over a tree and `git log --all -p` over every commit are
    both as large as the repository, and buffering either into one string makes peak memory a
    property of the repo being scanned rather than of this script.  Line by line, it is flat.

    The exit status is checked because the alternative is the worst failure this tool has: a
    bad ref made `git grep` produce nothing, which was reported as "findings: 0" and exit 0 --
    a clean bill of health from a command that never ran.  A scanner that answers "is this
    safe to publish" must never fail open.
    """
    p = subprocess.Popen(["git", "-C", repo, *args], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, errors="replace", bufsize=1)
    try:
        for line in p.stdout:
            yield line.rstrip("\n")
    finally:
        p.stdout.close()
        err = p.stderr.read()
        p.stderr.close()
        if p.wait() not in ok:
            print(f"error: git {' '.join(args[:2])} failed: {err.strip() or 'no output'}",
                  file=sys.stderr)
            sys.exit(2)                      # 2 = git/usage error, per the module docstring


def lines_tree(repo, ref):
    # git grep exits 1 when nothing matched, which is not an error; 2+ is.
    for rec in git_lines(repo, "grep", "-n", "-I", "--null", "-e", ".", ref, "--", ".",
                         ok=(0, 1)):
        # --null separates both the file name and the line number with NUL.
        name, _, rest = rec.partition("\0")
        lineno, _, text = rest.partition("\0")
        path = name.split(":", 1)[1] if name.startswith(ref + ":") else name
        yield path, lineno, text, None


def decode_binary(data, gaps=None):
    """Yield (part, text) for the readable content of a binary blob.

    The bytes on disk are not the text: a .pptx/.docx/.xlsx is a zip of XML parts and a PDF
    keeps its content in deflate streams, so searching the raw bytes misses every real match
    and reports matches that are only compressed noise.  Anything unrecognised falls back to
    printable runs, which is what `strings` does and the most that can be said about it.

    Capped three ways, because this reads whatever a repository happens to contain, including
    one you have just cloned and do not trust: MAX_PART per part, MAX_PARTS parts, and
    MAX_TOTAL across the blob.  The last is the one that bounds the work -- the first two
    leave their product unbounded.  A truncated part is still worth scanning: a finding in
    the bytes that were read is a finding.

    Every cap and every skipped part appends a reason to `gaps`, because a bound that does
    not announce itself turns incomplete coverage into a clean report -- which is the one
    answer this tool must never give by accident.  The caller prints them.
    """
    note = gaps.append if gaps is not None else (lambda _: None)
    budget = MAX_TOTAL
    if data[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except (zipfile.BadZipFile, OSError) as e:
            note(f"not a readable zip ({e.__class__.__name__}); not scanned")
            return
        members = z.infolist()
        if len(members) > MAX_PARTS:
            note(f"{len(members)} members, only the first {MAX_PARTS} examined")
        for info in members[:MAX_PARTS]:
            if info.is_dir():
                continue
            if budget <= 0:
                note(f"{MAX_TOTAL >> 20} MB decode budget exhausted; "
                     f"remaining members not scanned")
                return
            try:
                with z.open(info) as fh:                 # streamed, so file_size cannot lie
                    chunk = fh.read(min(MAX_PART, budget))
            except Exception as e:
                note(f"member {info.filename!r} unreadable ({e.__class__.__name__})")
                continue
            if len(chunk) >= MAX_PART:
                note(f"member {info.filename!r} truncated at {MAX_PART >> 20} MB")
            budget -= len(chunk)
            yield info.filename, chunk.decode("utf-8", "replace")
        return
    if data[:5] == b"%PDF-":
        # Found with str.find rather than a lazy regex. `stream(.*?)endstream` with re.S is
        # quadratic on a blob holding many `stream` tokens and no `endstream`: the engine
        # rescans to the end from every one of them, and MAX_PART cannot help because the
        # cost is paid before anything is decompressed. 64k tokens did not finish in 300 s.
        pos, found, undecoded = 0, 0, [0]
        while found < MAX_PARTS:
            i = data.find(b"stream", pos)
            if i < 0:
                break
            j = i + 6
            if data[j:j + 2] == b"\r\n":
                j += 2
            elif data[j:j + 1] == b"\n":
                j += 1
            else:
                pos = i + 6
                continue
            end = data.find(b"endstream", j)
            if end < 0:
                break
            pos, found = end + 9, found + 1
            if budget <= 0:
                note(f"{MAX_TOTAL >> 20} MB decode budget exhausted; "
                     f"remaining streams not scanned")
                return
            try:
                raw = zlib.decompressobj().decompress(data[j:end], min(MAX_PART, budget))
            except zlib.error:
                # Not deflate: an encrypted PDF, or LZW/CCITT. Its text is unreadable here,
                # which is not the same as absent.
                undecoded[0] += 1
                continue
            if len(raw) >= MAX_PART:
                note(f"a stream was truncated at {MAX_PART >> 20} MB")
            if raw:
                budget -= len(raw)
                yield "stream", raw.decode("utf-8", "replace")
        if found >= MAX_PARTS:
            note(f"more than {MAX_PARTS} streams; the rest were not examined")
        if undecoded[0]:
            note(f"{undecoded[0]} stream(s) are not deflate (encrypted or another filter) "
                 f"and were not decoded")
        if budget > 0:                      # metadata and names outside the streams
            yield "raw", printable(data, budget)
        return
    yield "raw", printable(data, budget)


def lines_binary(repo, ref):
    """Yield decoded lines of every binary file at REF, located as path:part."""
    def names(*extra):
        out = subprocess.run(["git", "-C", repo, "grep", *extra, "--name-only", "-e", ".",
                              ref, "--", "."], capture_output=True, text=True,
                             errors="replace").stdout
        return {n.split(":", 1)[1] if n.startswith(ref + ":") else n
                for n in out.splitlines() if n}

    binaries = names("-a") - names("-I")
    for path in sorted(binaries):
        size = git(repo, "cat-file", "-s", f"{ref}:{path}", check=False).strip()
        if size.isdigit() and int(size) > MAX_BLOB:
            print(f"note: {path} is {int(size) >> 20} MB; not decoded (--no-binary to silence)",
                  file=sys.stderr)
            continue
        blob = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"],
                              capture_output=True).stdout
        gaps = []
        for part, text in decode_binary(blob, gaps):
            for i, line in enumerate(text.splitlines(), 1):
                yield f"{path} [{part}]", str(i), line, None
        # Incomplete coverage is reported, never implied by silence.
        for g in dict.fromkeys(gaps):
            print(f"INCOMPLETE: {path}: {g}", file=sys.stderr)


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
    src = git_lines(repo, "log", "--all", "--reverse", "-p", "-U0", "--no-color",
                    "--format=%x00COMMIT %h")
    commit, path, newline = None, None, 0
    for line in src:
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

def report_remotes(repo):
    """Print each remote and, when `gh` can say, whether it is public.

    "Pushed" is not the same as "exposed": the same finding is urgent on a public repo and
    merely untidy on a private one, and a repo moving to a more public home republishes
    everything it carries.  Without this the pushed/unpushed split invites the wrong triage.
    """
    for line in git(repo, "remote", "-v", check=False).splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2] != "(fetch)":
            continue
        name, url = parts[0], parts[1]
        # A remote URL may carry credentials as userinfo (https://user:token@host/...).
        # Never print that: this output is pasted into reports and tickets.  Parsed rather
        # than pattern-matched, because a token may contain "/" (so a [^/@]+ class leaks its
        # first half) and a path may contain "@" (so a greedy class masks a clean URL).
        shown = url
        try:
            u = urllib.parse.urlsplit(url)
            if u.hostname and (u.username or u.password):
                host = u.hostname + (f":{u.port}" if u.port else "")
                shown = urllib.parse.urlunsplit(
                    (u.scheme, f"***@{host}", u.path, u.query, u.fragment))
        except ValueError:
            shown = "<unparseable remote URL>"
        vis = ""
        m = re.search(r"github\.com[:/]+([^/]+/[^/\s]+?)(?:\.git)?$", url)
        if m and shutil.which("gh"):
            p = subprocess.run(["gh", "repo", "view", m.group(1), "--json", "visibility",
                                "-q", ".visibility"], capture_output=True, text=True)
            vis = p.stdout.strip() or "unknown"
        print(f"remote: {name} {shown} {vis and '→ ' + vis.upper()}", file=sys.stderr)


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
    def __init__(self, repo, sha, ref="HEAD"):
        self.repo, self.sha, self.ref, self.cache = repo, sha, ref, {}

    def has(self, path, text):
        if self.sha is None:
            return None
        if path.endswith("]") and " [" in path:
            # A decoded binary part. Lines mean nothing across a re-compression, so compare
            # the blob itself: the value is published iff this exact artifact is.
            real = path.rsplit(" [", 1)[0]
            here = git(self.repo, "rev-parse", f"{self.ref}:{real}", check=False).strip()
            there = git(self.repo, "rev-parse", f"{self.sha}:{real}", check=False).strip()
            return bool(here) and here == there
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
    ap.add_argument("--no-binary", action="store_true",
                    help="skip binary files (zip/PDF-aware) in --tree scope")
    a = ap.parse_args()

    repo = git(a.repo, "rev-parse", "--show-toplevel").strip()
    if not repo:
        sys.exit(2)
    emails, accounts, user = (set(), set(), "") if a.no_auto else auto_terms()
    rules = build_rules(emails, accounts, a.term, user)
    allow = load_allow(repo, a.allow)
    print(f"identity terms: user={user or '-'} accounts={sorted(accounts) or '-'} "
          f"extra={a.term or '-'}", file=sys.stderr)
    report_remotes(repo)

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
        up = Upstream(repo, resolve_upstream(repo, a.upstream), ref)

        def tree():
            yield from lines_tree(repo, ref)
            if not a.no_binary:
                yield from lines_binary(repo, ref)

        src = tree()

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

    order = ["secret", "email", "account", "usage", "user-path", "username", "site-path",
             "host-addr"]
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
