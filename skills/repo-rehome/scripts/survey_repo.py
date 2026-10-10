#!/usr/bin/env python3
"""Survey a GitHub repository for the facts that decide how it can be rehomed.

Usage:
  survey_repo.py OWNER/REPO [OWNER/REPO ...]      # one block per repo
  survey_repo.py OWNER/REPO --json                # machine-readable

Everything printed here is read-only.  The point is to answer, before any plan is written,
the three questions that actually constrain a move:

  1. What can you do on this repo?  `admin` is the difference between "change the default
     branch, set protection, delete a branch" and "push".  A plan that assumes admin and
     then meets `push` has to be rewritten from the start.
  2. What is already there that must survive?  Branches, tags, issues, forks.
  3. Who else is watching?  A fork does not follow a force-push, and its owner is a person.

Exit status: 0 survey printed, 2 gh missing or a repo unreadable.
"""
import argparse
import json
import shutil
import subprocess
import sys


def gh_json(path, allow_fail=False):
    """GET a gh api path and parse it. Returns None when allow_fail and the call fails."""
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if p.returncode != 0:
        if allow_fail:
            return None
        sys.exit(f"error: gh api {path} failed: {p.stderr.strip().splitlines()[-1:] or ''}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        if allow_fail:
            return None
        sys.exit(f"error: gh api {path} did not return JSON")


def survey(nwo):
    repo = gh_json(f"repos/{nwo}")
    perms = repo.get("permissions") or {}
    branches = gh_json(f"repos/{nwo}/branches?per_page=100") or []
    tags = gh_json(f"repos/{nwo}/tags?per_page=100") or []
    forks = gh_json(f"repos/{nwo}/forks?per_page=100") or []
    # open_issues_count includes PRs, so count PRs separately and subtract.
    prs = gh_json(f"repos/{nwo}/pulls?state=open&per_page=100") or []
    return {
        "nwo": repo["full_name"],
        "visibility": repo.get("visibility"),
        "archived": repo.get("archived"),
        "is_fork": repo.get("fork"),
        "parent": (repo.get("parent") or {}).get("full_name"),
        "default_branch": repo.get("default_branch"),
        "permissions": {k: bool(perms.get(k)) for k in
                        ("admin", "maintain", "push", "triage", "pull")},
        "pushed_at": repo.get("pushed_at"),
        "size_kb": repo.get("size"),
        "branches": [{"name": b["name"], "sha": b["commit"]["sha"],
                      "protected": b.get("protected", False)} for b in branches],
        "tags": [t["name"] for t in tags],
        "forks": [f["full_name"] for f in forks],
        "open_prs": len(prs),
        "open_issues": max(0, (repo.get("open_issues_count") or 0) - len(prs)),
    }


def consequences(s):
    """The 'so what' of the survey. Each line is a constraint on the plan, not a comment."""
    out = []
    p = s["permissions"]
    if s["archived"]:
        out.append("ARCHIVED: read-only. Nothing can be pushed until it is unarchived.")
    if not p["admin"]:
        out.append("No admin: you CANNOT change the default branch, set branch protection, "
                   "delete the default branch, or transfer this repo.")
        if p["push"]:
            out.append("You CAN push, including a force-push, to any unprotected branch. If "
                       f"the work must end up on {s['default_branch']!r}, land it THERE rather "
                       "than on a new branch you cannot promote.")
    else:
        out.append("Admin: default branch, protection, deletion and transfer are all available.")
    prot = [b["name"] for b in s["branches"] if b["protected"]]
    if prot:
        out.append(f"Protected, so a force-push will be refused: {', '.join(prot)}")
    if s["visibility"] == "public":
        out.append("PUBLIC: anything pushed here is published. Scan the content for account, "
                   "host and personal identifiers first (see the repo-sensitive-scan skill).")
    if s["forks"]:
        out.append(f"{len(s['forks'])} fork(s) — {', '.join(s['forks'][:5])}"
                   f"{' …' if len(s['forks']) > 5 else ''}. A fork does not follow a "
                   "force-push and will show a divergent default branch. Tell the owners "
                   "BEFORE, not after.")
    if s["open_issues"] or s["open_prs"]:
        out.append(f"{s['open_issues']} open issue(s) and {s['open_prs']} open PR(s) survive "
                   "any content change. They describe the OLD code — triage them, do not "
                   "silently inherit them.")
    if s["is_fork"] and s["parent"]:
        out.append(f"This is itself a fork of {s['parent']}; a fork of a private network "
                   "cannot be transferred.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="+", metavar="OWNER/REPO")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    a = ap.parse_args()

    if not shutil.which("gh"):
        sys.exit("error: `gh` is required. Install the GitHub CLI (https://cli.github.com) "
                 "and run `gh auth login`.")

    surveys = [survey(r) for r in a.repos]
    if a.json:
        print(json.dumps(surveys, indent=2))
        return

    for s in surveys:
        print(f"\n=== {s['nwo']} ===")
        flags = [s["visibility"] or "?"]
        if s["archived"]:
            flags.append("ARCHIVED")
        if s["is_fork"]:
            flags.append(f"fork of {s['parent']}")
        print(f"  {' · '.join(flags)} · {s['size_kb']} KB · last push {s['pushed_at']}")
        have = [k for k, v in s["permissions"].items() if v] or ["(none)"]
        print(f"  your access: {', '.join(have)}")
        print(f"  default branch: {s['default_branch']}")
        print(f"  branches ({len(s['branches'])}):")
        for b in s["branches"]:
            star = " *" if b["name"] == s["default_branch"] else "  "
            lock = " [protected]" if b["protected"] else ""
            print(f"   {star} {b['sha'][:8]}  {b['name']}{lock}")
        print(f"  tags: {', '.join(s['tags']) or '(none)'}")
        print("  consequences:")
        for line in consequences(s):
            print(f"    - {line}")
    print()


if __name__ == "__main__":
    main()
