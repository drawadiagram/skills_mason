#!/usr/bin/env python3
"""Group a plans/BACKLOG.md tracker's open items into commit-sized episodes.

Usage:
  propose_episode.py [PLANS_DIR_OR_BACKLOG ...] [options]

With no argument, uses every BACKLOG.md under a plans/ directory below the current
directory. Read-only: it never writes to the tracker or the plan docs.

What it does: reads each open row, follows its Doc link (honouring the #anchor so a
multi-item doc contributes only that item's section), pulls out the file paths the item
names, infers whether the item is a bug, a planned feature or neither, then walks the
items in ladder order building episodes out of items that share a module and a kind and
together stay inside the size budget.

Options:
  --ladder LIST     kind order, comma-separated from {bug,feature,other} (default
                    bug,feature,other); or "order" to follow the BACKLOG's own Order
                    section; or "severity" to go by Severity/Tier alone
  --max-modules N   module budget per episode (default 3)
  --max-files N     file budget per episode (default 5)
  --module-depth N  how many leading path components make a module (default 2)
  --count N         how many episodes to print (default 3); 0 for all
  --include-all     also consider rows whose Status is fixed / submitted / closed
  --mix-kinds       let one episode hold items of different kinds
  --doc N           print an episode-doc skeleton for episode N instead of the listing
  --json            machine-readable dump of every episode

Exit status is 0 whenever a tracker was read, 2 when none was found or an option was bad.
It measures size and adjacency. It cannot judge whether two items share one sentence, and
a kind marked (inferred) was guessed from wording, so check both by hand.
"""

import argparse
import json
import os
import re
import subprocess
import sys

TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{2,}")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
ANCHOR_RE = re.compile(r"""<a\s+(?:id|name)\s*=\s*["']([^"']+)["']""", re.I)
ID_RE = re.compile(r"^[A-Za-z]{0,2}\d+[a-z]?$")
DEPENDS_RE = re.compile(r"\*\*Depends on:?\*\*\s*([^\n|·]*)", re.I)
ID_TOKEN_RE = re.compile(r"\b([A-Za-z]{0,2}\d+)\b")

EXTS = (
    "py|sh|bash|zsh|md|rst|txt|js|mjs|cjs|ts|tsx|jsx|json|jsonl|ndjson|ya?ml|toml|ini|"
    "cfg|conf|c|h|cc|cpp|hpp|cu|cuh|f|f90|jl|R|r|rs|go|java|kt|rb|pl|lua|sql|tex|ipynb|"
    "html|css|svg|pptx|docx|xlsx|pdf|csv|tsv|log|out|err|npy|npz|h5|hdf5|pkl|xml|"
    "slurm|sbatch|mk|cmake|lock"
)
# The extension branch ends on a non-word character, so `deck_lib.code()` is not `deck_lib.c`.
PATH_RE = re.compile(
    r"(?<![\w/.~-])"
    r"((?:[\w.@+~-]+/)+[\w.@+~-]+|[\w@+~-]+\.(?:" + EXTS + r")(?!\w))"
    r"(?::\d+(?:[-:]\d+)?)?"
)
NOT_A_PATH = {"and/or", "e.g", "i.e", "n/a", "w/o", "km/h", "gpu-h", "input/output"}

BUG_HEADING_RE = re.compile(
    r"^#{1,6}\s*\d*\.?\s*(symptom|root cause|cause|defect|what we saw|what happens)\b",
    re.I | re.M,
)
BUG_WORD_RE = re.compile(
    r"\b(bug|defect|fails?|failed|failing|failure|crash(es|ed|ing)?|wrong|incorrect|"
    r"silent(ly)?|never (reads?|runs?|fires?|reaches)|broken|breaks?|regress(ion|es|ed)?|"
    r"drops?|dropped|garbage|misparse[sd]?|misread[s]?|misreport[s]?|stale|hangs?|hung|"
    r"leaks?|leaked|race|off-by-one|exits? non-zero|traceback|reports? garbage|"
    r"accepts? an? \w+ instead|instead of \w+ing|blank even when)\b",
    re.I,
)
CHANGE_HEADING_RE = re.compile(
    r"^#{1,6}\s*\d*\.?\s*(change|design|plan|implementation|what will change)\b", re.I | re.M
)
TEST_TABLE_RE = re.compile(r"^\|\s*(check|criterion|criteria|test|pass)\b", re.I | re.M)
SEV_RANK = {"high": 0.0, "critical": 0.0, "medium": 1.0, "med": 1.0, "low": 2.0}
KINDS = ("bug", "feature", "other")


def die(msg):
    sys.stderr.write("propose_episode: %s\n" % msg)
    raise SystemExit(2)


def repo_root(start):
    try:
        out = subprocess.run(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except OSError:
        pass
    return os.path.abspath(start)


def find_backlogs(targets):
    found = []
    if not targets:
        for root, dirs, files in os.walk("."):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "node_modules")
            if os.path.basename(root) == "plans" and "BACKLOG.md" in files:
                found.append(os.path.normpath(os.path.join(root, "BACKLOG.md")))
        return found
    for t in targets:
        if os.path.isdir(t):
            cand = os.path.join(t, "BACKLOG.md")
            if os.path.isfile(cand):
                found.append(os.path.normpath(cand))
            else:
                die("no BACKLOG.md in %s" % t)
        elif os.path.isfile(t):
            found.append(os.path.normpath(t))
        else:
            die("not a file or directory: %s" % t)
    return found


# ---------------------------------------------------------------- tracker parsing

def split_sections(lines):
    """[(section_title, start_index, [lines])] split on level-2 headings."""
    sections, title, start, buf = [], "", 0, []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 2:
            sections.append((title, start, buf))
            title, start, buf = m.group(2).strip(), i, []
        else:
            buf.append(line)
    sections.append((title, start, buf))
    return sections


def parse_rows(path):
    """Every table row under a non-Closed section, as dicts of header -> cell."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    rows, order_text = [], ""
    for title, start, body in split_sections(lines):
        if re.match(r"^closed\b", title, re.I):
            continue
        if re.match(r"^order\b", title, re.I):
            order_text = "\n".join(body)
        header = None
        for off, line in enumerate(body):
            if not line.lstrip().startswith("|"):
                header = None
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if TABLE_SEP_RE.match(line.strip()):
                continue
            low = [c.lower() for c in cells]
            if header is None:
                if any(c in ("#", "id", "item #") for c in low) and any("item" in c for c in low):
                    header = low
                continue
            if len(cells) < 2:
                continue
            row = dict(zip(header, cells))
            row["_line"] = start + off + 1
            row["_section"] = title
            rows.append(row)
    return rows, order_text


def cell(row, *names):
    for n in names:
        for key, val in row.items():
            if key.startswith("_"):
                continue
            if n in key:
                return val
    return ""


def strip_md(text):
    text = LINK_RE.sub(r"\1", text)
    return text.replace("`", "").replace("**", "").strip()


# ---------------------------------------------------------------- doc reading

def doc_section(doc_path, anchor):
    """The slice of the doc that belongs to this item, or the whole doc."""
    try:
        with open(doc_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    if not anchor:
        return "\n".join(lines)
    start = None
    for i, line in enumerate(lines):
        m = ANCHOR_RE.search(line)
        if m and m.group(1).lower() == anchor.lower():
            start = i
            break
        h = HEADING_RE.match(line)
        if h and slug(h.group(2)) == anchor.lower():
            start = i
            break
    if start is None:
        return "\n".join(lines)
    # The anchor usually sits on its own line just above the item's heading, so find that
    # heading first and collect after it; collecting from the anchor line stops at once.
    level, hidx = 9, start
    for j in range(start, min(start + 4, len(lines))):
        h = HEADING_RE.match(lines[j])
        if h:
            level, hidx = len(h.group(1)), j
            break
    out = lines[start:hidx + 1]
    for line in lines[hidx + 1:]:
        h = HEADING_RE.match(line)
        if h and len(h.group(1)) <= level:
            break
        out.append(line)
    return "\n".join(out)


def slug(text):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")


# ---------------------------------------------------------------- extraction

def build_index(root):
    """suffix -> [tracked path], so a doc that cites `scripts/x.py` can be placed."""
    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                             capture_output=True, text=True, check=False)
        tracked = [p for p in out.stdout.split("\0") if p] if out.returncode == 0 else []
    except OSError:
        tracked = []
    index = {}
    if len(tracked) > 50000:
        return index
    for p in tracked:
        parts = p.split("/")
        for i in range(len(parts)):
            index.setdefault("/".join(parts[i:]), []).append(p)
    return index


def cited_paths(text):
    """Every path-shaped token in the text, as written."""
    raws = []
    for m in PATH_RE.finditer(text or ""):
        raw = m.group(1).strip().rstrip(".,;:)")
        if raw.lower() in NOT_A_PATH or "://" in raw or " " in raw:
            continue
        raw = re.sub(r"^\./", "", raw)
        if not raw or raw.endswith("/") or raw in raws:
            continue
        if not re.search(r"[A-Za-z]", raw.rsplit("/", 1)[-1]):
            continue  # "0/2", "1/4": a ratio, not a file
        raws.append(raw)
    return raws


def prefixes_of(paths):
    """{depth: {"a/b/"}} for the directories a set of resolved paths sits in."""
    out = {1: set(), 2: set(), 3: set()}
    for p in paths:
        parts = p.split("/")
        for d in (1, 2, 3):
            if len(parts) > d:
                out[d].add("/".join(parts[:d]) + "/")
    return out


def place(hits, prefs):
    """Narrow an ambiguous path with the most specific prefix that leaves one match."""
    for d in (3, 2, 1):
        if not prefs[d]:
            continue
        near = [h for h in hits if any(h.startswith(x) for x in prefs[d])]
        if len(near) == 1:
            return near[0]
    return None


def resolve_paths(raws, root, index, extra_prefixes=None):
    """(resolved repo-relative paths, [(raw, reason) not placed]).

    Two passes, because plan docs cite paths relative to the component they are about
    ("scripts/deck_lib.js", "SKILL.md"), not to the repo. Pass 1 takes the ones that
    exist or have exactly one match in the index; pass 2 narrows the ambiguous ones to
    the directories pass 1 established, most specific prefix first, so "SKILL.md" in an
    item that also cites "scripts/deck_lib.js" lands in that one skill and not in all
    seven.
    """
    resolved, pending = [], []
    for raw in raws:
        if os.path.exists(os.path.join(root, raw)):
            if raw not in resolved:
                resolved.append(raw)
            continue
        hits = index.get(raw, [])
        if len(hits) == 1:
            if hits[0] not in resolved:
                resolved.append(hits[0])
        else:
            pending.append((raw, hits))
    prefs = prefixes_of(resolved)
    if extra_prefixes:
        for d in (1, 2, 3):
            prefs[d] |= extra_prefixes[d]
    unplaced = []
    for raw, hits in pending:
        if not hits:
            if re.search(r"\.(" + EXTS + r")$", raw.rsplit("/", 1)[-1], re.I):
                unplaced.append((raw, "not in the checkout"))
            continue
        hit = place(hits, prefs)
        if hit:
            if hit not in resolved:
                resolved.append(hit)
        else:
            unplaced.append((raw, "%d files match it; cite it repo-relative" % len(hits)))
    return resolved, unplaced


def module_of(path, depth):
    parts = path.split("/")
    if len(parts) == 1:
        return path
    return "/".join(parts[:min(depth, len(parts) - 1)])


PROSE_START_RE = re.compile(
    r"^\W*(record|document|note|say|mention|explain|clarify|point (at|to)|reword|"
    r"spell out|write up|warn about)\b", re.I)


def infer_kind(item_text, doc_text):
    blob = "%s\n%s" % (item_text, doc_text or "")
    if PROSE_START_RE.match(item_text):
        return "other", True
    if BUG_HEADING_RE.search(doc_text or "") or BUG_WORD_RE.search(item_text):
        return "bug", True
    if CHANGE_HEADING_RE.search(blob):
        return ("feature", True) if TEST_TABLE_RE.search(blob) else ("feature?", True)
    if BUG_WORD_RE.search(blob):
        return "bug", True
    return "other", True


def sev_rank(text):
    t = strip_md(text).lower()
    m = re.search(r"\b(\d+)\b", t)
    if m and "tier" not in t:
        return float(m.group(1))
    for word, rank in SEV_RANK.items():
        if word in t:
            return rank
    return 1.5


SKIP_STATUS_RE = re.compile(r"^\W*(closed|done|confirmed|fixed|merged)\b|submitted", re.I)


class Item:
    def __init__(self, iid, row, backlog, root, index, depth):
        self.id = iid
        self.backlog = backlog
        self.line = row["_line"]
        self.text = strip_md(cell(row, "item", "symptom", "title"))
        self.status = strip_md(cell(row, "status"))
        self.severity = strip_md(cell(row, "severity", "tier", "priority"))
        self.sev = sev_rank(self.severity)
        self.doc, self.anchor, self.doc_text = None, None, None
        m = LINK_RE.search(cell(row, "doc", "plan", "link"))
        if m:
            target = m.group(2)
            self.anchor = target.split("#", 1)[1] if "#" in target else None
            rel = target.split("#", 1)[0]
            if rel:
                self.doc = os.path.normpath(os.path.join(os.path.dirname(backlog), rel))
                self.doc_text = doc_section(self.doc, self.anchor)
        explicit = strip_md(cell(row, "kind", "type"))
        if explicit.lower() in ("bug", "defect"):
            self.kind, self.kind_inferred = "bug", False
        elif explicit.lower() in ("feature", "change", "enhancement"):
            self.kind, self.kind_inferred = "feature", False
        elif explicit.lower() in ("other", "chore", "docs", "prose"):
            self.kind, self.kind_inferred = "other", False
        else:
            self.kind, self.kind_inferred = infer_kind(self.text, self.doc_text)
        self.root, self.index, self.depth = root, index, depth
        self.raws = cited_paths("%s\n%s" % (self.text, self.doc_text or ""))
        self.paths, self.unplaced = resolve_paths(self.raws, root, index)
        self.set_modules()
        self.depends = []
        if self.doc_text:
            dm = DEPENDS_RE.search(self.doc_text)
            if dm:
                self.depends = [t for t in ID_TOKEN_RE.findall(dm.group(1))]

    def set_modules(self):
        self.modules = []
        for p in self.paths:
            mod = module_of(p, self.depth)
            if mod not in self.modules:
                self.modules.append(mod)

    def retry_paths(self, extra_prefixes):
        self.paths, self.unplaced = resolve_paths(
            self.raws, self.root, self.index, extra_prefixes)
        self.set_modules()

    @property
    def base_kind(self):
        return "feature" if self.kind == "feature?" else self.kind

    def label(self):
        bits = [self.kind + ("" if not self.kind_inferred else ", inferred")]
        if self.severity:
            bits.append(self.severity)
        return "[%s]" % "; ".join(bits)


# ---------------------------------------------------------------- selection

def ladder_rank(item, ladder):
    try:
        base = float(ladder.index(item.base_kind))
    except ValueError:
        base = float(len(ladder))
    return base + (0.5 if item.kind == "feature?" else 0.0)


def order_rank(items, order_text):
    seen, rank = {}, 0
    for m in ID_TOKEN_RE.finditer(order_text or ""):
        tok = m.group(1)
        if tok not in seen:
            seen[tok] = rank
            rank += 1
    big = rank + 1
    return {it.id: seen.get(it.id, big) for it in items}


def sort_key(items, mode, ladder, order_text):
    pos = {it.id: i for i, it in enumerate(items)}
    oranks = order_rank(items, order_text)
    if mode == "order":
        return lambda it: (oranks[it.id], ladder_rank(it, ladder), it.sev, pos[it.id])
    if mode == "severity":
        return lambda it: (it.sev, ladder_rank(it, ladder), pos[it.id])
    return lambda it: (ladder_rank(it, ladder), it.sev, pos[it.id])


def build_episodes(items, args, ladder, order_text):
    ranked = sorted(items, key=sort_key(items, args.ladder_mode, ladder, order_text))
    used, episodes = set(), []
    for seed in ranked:
        if seed.id in used:
            continue
        ep = {
            "items": [seed], "modules": list(seed.modules), "files": list(seed.paths),
            "dropped": [], "warnings": [],
        }
        used.add(seed.id)
        if not seed.modules:
            ep["warnings"].append(
                "%s names no file, so nothing can be grouped with it: add the paths to its "
                "plan doc, or treat the episode as this item alone" % seed.id
            )
        oversized = (len(seed.modules) > args.max_modules
                     or len(seed.paths) > args.max_files)
        if oversized:
            ep["warnings"].append(
                "%s alone spans %d modules / %d files, over the %d/%d budget: plan it as a "
                "stack of commits, not one" % (seed.id, len(seed.modules), len(seed.paths),
                                               args.max_modules, args.max_files)
            )
        for cand in ranked:
            if cand.id in used or oversized or not ep["modules"]:
                continue
            shared = [m for m in cand.modules if m in ep["modules"]]
            if not shared:
                continue
            if cand.base_kind != seed.base_kind and not args.mix_kinds:
                ep["dropped"].append((cand, "same module (%s) but kind %s, not %s"
                                      % (shared[0], cand.kind, seed.kind)))
                continue
            mods = ep["modules"] + [m for m in cand.modules if m not in ep["modules"]]
            files = ep["files"] + [p for p in cand.paths if p not in ep["files"]]
            if len(mods) > args.max_modules or len(files) > args.max_files:
                ep["dropped"].append((cand, "would take the episode to %d modules / %d files"
                                      % (len(mods), len(files))))
                continue
            ep["items"].append(cand)
            ep["modules"], ep["files"] = mods, files
            used.add(cand.id)
        here = {it.id for it in ep["items"]}
        for it in ep["items"]:
            for dep in it.depends:
                if dep in here:
                    continue
                if any(dep == o.id for o in items):
                    ep["warnings"].append(
                        "%s depends on %s, which is still open and not in this episode: "
                        "land %s first or pull it in" % (it.id, dep, dep))
        episodes.append(ep)
        if args.count and len(episodes) >= args.count:
            break
    return episodes


# ---------------------------------------------------------------- output

def print_listing(backlog, items, skipped, episodes, args):
    print("%s — %d candidate item%s, ladder %s, budget %d modules / %d files "
          "(module = %d path components)"
          % (backlog, len(items), "" if len(items) == 1 else "s", args.ladder_label,
             args.max_modules, args.max_files, args.module_depth))
    if skipped:
        print("  %d row%s not a candidate (status fixed/submitted/closed): %s"
              % (len(skipped), "" if len(skipped) == 1 else "s",
                 ", ".join("%s (%s)" % (i, s) for i, s in skipped)))
    if not items:
        print("  nothing open to plan")
        return
    for n, ep in enumerate(episodes, 1):
        ids = ", ".join(it.id for it in ep["items"])
        print("\nEpisode %d — items %s · %d module%s · %d file%s · %s"
              % (n, ids, len(ep["modules"]), "" if len(ep["modules"]) == 1 else "s",
                 len(ep["files"]), "" if len(ep["files"]) == 1 else "s",
                 ep["items"][0].kind))
        for it in ep["items"]:
            text = it.text if len(it.text) <= 88 else it.text[:87] + "…"
            print("  %-4s %-26s %s" % (it.id, it.label(), text))
        if ep["modules"]:
            print("  modules  " + ", ".join(ep["modules"]))
        for p in ep["files"]:
            print("  file     %s" % p)
        unplaced = []
        for it in ep["items"]:
            for raw, why in it.unplaced:
                if (raw, why) not in unplaced:
                    unplaced.append((raw, why))
        for raw, why in unplaced[:6]:
            print("  cited    %s — outside the measured scope: %s" % (raw, why))
        for cand, why in ep["dropped"][:6]:
            print("  dropped  %-4s %s" % (cand.id, why))
        for w in ep["warnings"]:
            print("  warn     %s" % w)
    print("\nEpisode 1 is the next commit. The script measured size and adjacency; you still")
    print("have to write the one sentence that covers it and check the kinds marked inferred.")
    print("Skeleton for the doc: --doc 1")


def print_doc(ep, args):
    ids = ", ".join(it.id for it in ep["items"])
    kinds = ", ".join(sorted({it.kind for it in ep["items"]}))
    print("# Episode: <one sentence, no \"and\" — what this commit does>\n")
    print("**Status:** planned · **Items:** %s · **Kind:** %s · **Ladder:** %s\n"
          % (ids, kinds, args.ladder_label))
    print("## Scope\n")
    print("| In scope | Why it is here |")
    print("|---|---|")
    for p in ep["files"]:
        print("| `%s` | <which item needs it> |" % p)
    print("\nModules: %s\n" % (", ".join(ep["modules"]) or "<none cited — fill this in>"))
    print("## Items\n")
    for it in ep["items"]:
        doc = ""
        if it.doc:
            rel = os.path.basename(it.doc) + ("#" + it.anchor if it.anchor else "")
            doc = " ([plan](%s))" % rel
        print("- **%s** %s %s%s" % (it.id, it.label(), it.text, doc))
    print("\n## Excluded, deliberately\n")
    for cand, why in ep["dropped"]:
        print("- **%s** — %s" % (cand.id, why))
    print("- <anything else a reviewer might expect to see here, and why it is not>\n")
    print("## Test\n")
    print("| Check | Pass |")
    print("|---|---|")
    print("| <what proves the change> | <criterion, written before the run> |")
    print("\n## Commit message\n")
    print("```")
    print("<verb> <the one thing>")
    print("")
    print("<Why, with the evidence each item cites.>")
    print("")
    print("<What changed, module by module.>")
    print("")
    print("Left out of this commit: <items and why>.")
    print("Plan: plans/<this doc>.md")
    print("```\n")
    print("## Result\n")
    print("<Added after the commit: SHA, what the checks said, what was surprising.>")


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[0])
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--ladder", default="bug,feature,other")
    ap.add_argument("--max-modules", type=int, default=3)
    ap.add_argument("--max-files", type=int, default=5)
    ap.add_argument("--module-depth", type=int, default=2)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--include-all", action="store_true")
    ap.add_argument("--mix-kinds", action="store_true")
    ap.add_argument("--doc", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.ladder in ("order", "severity"):
        args.ladder_mode, ladder = args.ladder, list(KINDS)
        args.ladder_label = args.ladder
    else:
        ladder = [k.strip().lower() for k in args.ladder.split(",") if k.strip()]
        bad = [k for k in ladder if k not in KINDS]
        if bad or not ladder:
            die("--ladder takes order, severity, or a comma list from %s (got %r)"
                % ("/".join(KINDS), args.ladder))
        args.ladder_mode, args.ladder_label = "kind", ",".join(ladder)
    for name in ("max_modules", "max_files", "module_depth"):
        if getattr(args, name) < 1:
            die("--%s must be at least 1" % name.replace("_", "-"))

    backlogs = find_backlogs(args.targets)
    if not backlogs:
        die("no plans/BACKLOG.md found below %s — set one up first (see the "
            "plans-backlog skill)" % os.path.abspath("."))

    payload = []
    for bi, backlog in enumerate(backlogs):
        root = repo_root(os.path.dirname(backlog) or ".")
        index = build_index(root)
        rows, order_text = parse_rows(backlog)
        items, skipped = [], []
        for row in rows:
            iid = strip_md(cell(row, "#", "id")) or strip_md(row.get("_line", ""))
            if not ID_RE.match(iid or ""):
                continue
            it = Item(iid, row, backlog, root, index, args.module_depth)
            if not args.include_all and SKIP_STATUS_RE.search(it.status or ""):
                skipped.append((iid, it.status))
                continue
            items.append(it)
        by_doc = {}
        for it in items:
            if it.doc:
                by_doc.setdefault(it.doc, []).append(it)
        for group in by_doc.values():
            known = [p for it in group for p in it.paths]
            if not known:
                continue
            prefs = prefixes_of(known)
            for it in group:
                if not it.paths:
                    it.retry_paths(prefs)
        episodes = build_episodes(items, args, ladder, order_text)
        if args.doc:
            if args.doc > len(episodes):
                die("no episode %d (got %d)" % (args.doc, len(episodes)))
            print_doc(episodes[args.doc - 1], args)
            return 0
        if args.json:
            payload.append({
                "backlog": backlog,
                "skipped": [{"id": i, "status": s} for i, s in skipped],
                "episodes": [{
                    "items": [{"id": it.id, "kind": it.kind,
                               "kind_inferred": it.kind_inferred,
                               "severity": it.severity, "text": it.text,
                               "doc": it.doc, "anchor": it.anchor,
                               "paths": it.paths, "modules": it.modules,
                               "unplaced": [{"raw": r, "why": w} for r, w in it.unplaced],
                               "depends": it.depends} for it in ep["items"]],
                    "modules": ep["modules"], "files": ep["files"],
                    "dropped": [{"id": c.id, "why": w} for c, w in ep["dropped"]],
                    "warnings": ep["warnings"],
                } for ep in episodes],
            })
            continue
        if bi:
            print()
        print_listing(backlog, items, skipped, episodes, args)
    if args.json:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
