#!/usr/bin/env python3
"""Lint a project's plans/ directories and their BACKLOG.md trackers.

Usage:
  check_backlog.py [PLANS_DIR ...]

With no argument, checks every directory named plans/ under the current directory
(skipping .git and other hidden dirs). Read-only.

Errors (exit 1):
  dup-id        the same item ID appears twice in one BACKLOG (open table or Closed)
  bad-link      a relative link points to a file that does not exist
  bad-anchor    a link's #anchor matches no <a id="..."> and no heading in the target

Warnings (exit 0 when there are no errors):
  closed-open   a row in an open table whose Status starts with done/closed/confirmed
  orphan        a .md file under plans/ that BACKLOG.md does not reach, directly or via
                other plan docs it links to
  no-evidence   an open row that cites nothing: no job-ID-like number, commit SHA,
                PR number or link
  escapes-repo  a relative link that resolves outside the repository root

Output: one line per finding, "LEVEL code path:line message", then a summary.
"""

import os
import re
import subprocess
import sys

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
ANCHOR_ID_RE = re.compile(r"""<a\s+(?:name|id)\s*=\s*["']([^"']+)["']""", re.I)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CLOSED_BULLET_RE = re.compile(r"^\s*[-*]\s+\*\*([A-Za-z]*\d+[A-Za-z]?)\*\*")
DONE_STATUS_RE = re.compile(r"^\W*(done|closed|confirmed)\b", re.I)
EVIDENCE_RES = [
    re.compile(r"\b\d{6,10}\b"),  # scheduler job IDs
    re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b"),  # commit SHAs
    re.compile(r"#\d+\b"),  # PR / issue numbers
    LINK_RE,
]
SKIP_FILES = {"BACKLOG.md", "README.md"}


class Report:
    def __init__(self):
        self.findings = []

    def add(self, level, code, path, line, msg):
        self.findings.append((level, code, path, line, msg))

    def count(self, level):
        return sum(1 for f in self.findings if f[0] == level)


def repo_root(start):
    try:
        out = subprocess.run(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return os.path.realpath(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return os.path.realpath(os.getcwd())


def slugify(heading):
    """GitHub-style heading anchor."""
    text = re.sub(r"<[^>]+>", "", heading)
    text = re.sub(r"[`*_~]", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors_of(path, cache={}):
    if path not in cache:
        anchors = set()
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    anchors.update(ANCHOR_ID_RE.findall(line))
                    m = HEADING_RE.match(line)
                    if m:
                        anchors.add(slugify(m.group(2)))
        except OSError:
            pass
        cache[path] = anchors
    return cache[path]


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(cells):
    return all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c)


def clean_id(cell):
    return re.sub(r"[*`]", "", cell).strip()


def links_in(text):
    for target in LINK_RE.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):  # http:, mailto:, ...
            continue
        yield target


def check_link(report, root, src_path, lineno, target):
    """Validate one relative link; return the resolved file path or None."""
    path_part, _, anchor = target.partition("#")
    src_dir = os.path.dirname(src_path)
    resolved = os.path.realpath(os.path.join(src_dir, path_part)) if path_part else src_path
    if path_part and not os.path.exists(resolved):
        report.add("ERROR", "bad-link", src_path, lineno, f"no such file: {target}")
        return None
    if path_part and os.path.commonpath([root, resolved]) != root:
        report.add("WARN", "escapes-repo", src_path, lineno, f"link leaves the repo: {target}")
    if anchor and os.path.isfile(resolved) and anchor not in anchors_of(resolved):
        report.add("ERROR", "bad-anchor", src_path, lineno, f"no anchor #{anchor} in {target}")
    return resolved


def check_backlog(report, root, backlog):
    seen_ids = {}
    in_closed = False
    header = None
    linked = set()

    with open(backlog, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    for lineno, line in enumerate(lines, 1):
        m = HEADING_RE.match(line)
        if m:
            in_closed = "closed" in m.group(2).lower()
            header = None

        for target in links_in(line):
            resolved = check_link(report, root, backlog, lineno, target)
            if resolved:
                linked.add(resolved)

        bullet = CLOSED_BULLET_RE.match(line)
        if in_closed and bullet:
            item_id = bullet.group(1)
            if item_id in seen_ids:
                report.add("ERROR", "dup-id", backlog, lineno,
                           f"ID {item_id} also on line {seen_ids[item_id]}")
            else:
                seen_ids[item_id] = lineno
            continue

        if not line.lstrip().startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = split_row(line)
        if is_separator(cells):
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if not cells or not cells[0]:
            continue

        item_id = clean_id(cells[0])
        if item_id in seen_ids:
            report.add("ERROR", "dup-id", backlog, lineno,
                       f"ID {item_id} also on line {seen_ids[item_id]}")
        else:
            seen_ids[item_id] = lineno

        if in_closed:
            continue
        col = {name: i for i, name in enumerate(header)}
        status = cells[col["status"]] if "status" in col and col["status"] < len(cells) else ""
        if DONE_STATUS_RE.match(status):
            report.add("WARN", "closed-open", backlog, lineno,
                       f"{item_id} looks finished ({status[:40]!r}); move it to Closed")
        if not any(r.search(line) for r in EVIDENCE_RES):
            report.add("WARN", "no-evidence", backlog, lineno,
                       f"{item_id} cites no job ID, commit, PR or doc")

    return linked


def reachable_docs(root, plans_dir, start):
    """Plan docs reachable from the BACKLOG's links, following links between docs."""
    seen = set()
    stack = [p for p in start if p.endswith(".md")]
    while stack:
        path = stack.pop()
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        if os.path.commonpath([plans_dir, path]) != plans_dir:
            continue  # do not crawl outside this plans/ dir
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for target in links_in(text):
            file_part = target.partition("#")[0]
            if file_part:
                stack.append(os.path.realpath(os.path.join(os.path.dirname(path), file_part)))
    return seen


def check_plans_dir(report, plans_dir):
    plans_dir = os.path.realpath(plans_dir)
    root = repo_root(plans_dir)
    backlog = os.path.join(plans_dir, "BACKLOG.md")
    if not os.path.isfile(backlog):
        report.add("WARN", "no-backlog", plans_dir, 0, "plans/ dir has no BACKLOG.md")
        return
    linked = check_backlog(report, root, backlog)
    reached = reachable_docs(root, plans_dir, linked)
    for dirpath, dirnames, filenames in os.walk(plans_dir):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if name.endswith(".md") and name not in SKIP_FILES and path not in reached:
                report.add("WARN", "orphan", path, 0, "not reachable from BACKLOG.md")


def find_plans_dirs(start):
    found = []
    for dirpath, dirnames, _ in os.walk(start):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in ("node_modules",)
        )
        if os.path.basename(dirpath) == "plans":
            found.append(dirpath)
            dirnames[:] = []  # nested dirs belong to this plans/ (e.g. upstream/)
    return found


def main(argv):
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__.strip())
        return 0
    dirs = argv or find_plans_dirs(os.getcwd())
    if not dirs:
        print("no plans/ directory found", file=sys.stderr)
        return 1
    report = Report()
    for d in dirs:
        if not os.path.isdir(d):
            print(f"not a directory: {d}", file=sys.stderr)
            return 1
        check_plans_dir(report, d)
    cwd = os.getcwd()
    for level, code, path, line, msg in report.findings:
        rel = os.path.relpath(path, cwd)
        where = f"{rel}:{line}" if line else rel
        print(f"{level:5} {code:12} {where}  {msg}")
    errors, warns = report.count("ERROR"), report.count("WARN")
    print(f"checked {len(dirs)} plans dir(s): {errors} error(s), {warns} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
