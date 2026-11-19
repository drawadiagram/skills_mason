#!/usr/bin/env bash
# Commit counts per author for each area of a git repository. Read-only.
#
#   authorship_by_area.sh                 every top-level tracked directory
#   authorship_by_area.sh src docs tests  the directories given
#   authorship_by_area.sh -n 8 src        show up to 8 authors per area (default 5)
#
# Names are grouped case-insensitively, so "Jane Doe" and "jane doe" count together. Other
# variants of one person ("jdoe", "Jane D") are NOT merged: they are listed at the end so
# they can be merged by eye. Honours a .mailmap if the repository has one.
#
# Commit counts are a rough measure. They show who worked where, not how much each commit
# was worth, so use them to support a role statement rather than to rank people.

set -euo pipefail

top=5
if [ "${1:-}" = "-n" ]; then
    top="${2:?-n needs a number}"
    shift 2
fi
case "${1:-}" in -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;; esac

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "authorship_by_area.sh: not inside a git repository" >&2
    exit 2
fi
cd "$(git rev-parse --show-toplevel)"

if [ "$#" -gt 0 ]; then
    areas=("$@")
else
    mapfile -t areas < <(git ls-files | awk -F/ 'NF>1 {print $1}' | sort -u)
fi

count() {  # stdin: one author name per line -> "count name", case-insensitive grouping
    awk '{ k = tolower($0); n[k]++; if (!(k in shown)) shown[k] = $0 }
         END { for (k in n) printf "%6d  %s\n", n[k], shown[k] }' | sort -rn
}

for area in "${areas[@]}"; do
    if [ -z "$(git ls-files -- "$area" | head -1)" ]; then
        echo "## $area  (no tracked files)"
        continue
    fi
    total=$(git log --format=%aN -- "$area" | wc -l)
    echo "## $area  ($total commits)"
    git log --format=%aN -- "$area" | count | head -n "$top"
    echo
done

echo "## whole repository"
git log --format=%aN | count
echo
echo "## author names seen (merge variants of one person by eye, or add a .mailmap)"
git log --format='%aN' | sort -fu | sed 's/^/  /'
