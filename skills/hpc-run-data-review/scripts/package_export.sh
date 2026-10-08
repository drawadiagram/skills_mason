#!/usr/bin/env bash
# Package selected run data into one tarball with stable relative paths, then verify it.
#
#   package_export.sh OUT.tar.gz BASE PATH [PATH...]
#
# PATHs are relative to BASE and are stored exactly that way, so the archive unpacks into
# the same tree on any machine. Refuses to overwrite OUT. Prints size, sha256, and the
# top two levels of the archive so the contents can be checked against the plan.
set -euo pipefail
OUT=${1:?usage: package_export.sh OUT.tar.gz BASE PATH...}; BASE=${2:?}; shift 2
[[ $# -gt 0 ]] || { echo "no paths given" >&2; exit 2; }
[[ -e $OUT ]] && { echo "refusing to overwrite $OUT" >&2; exit 1; }
for p in "$@"; do [[ -e $BASE/$p ]] || { echo "missing: $BASE/$p" >&2; exit 1; }; done
mkdir -p "$(dirname "$OUT")"
tar czf "$OUT" -C "$BASE" "$@"
tar tzf "$OUT" >/dev/null   # fails loudly on a corrupt archive
echo "size:   $(du -h "$OUT" | cut -f1)  (source: $(cd "$BASE" && du -shc "$@" | tail -1 | cut -f1))"
echo "sha256: $(sha256sum "$OUT" | cut -d' ' -f1)"
echo "contents (top two levels):"
tar tzf "$OUT" | awk -F/ '{print ($2=="" ? $1 : $1"/"$2)}' | sort -u | sed 's/^/  /'
