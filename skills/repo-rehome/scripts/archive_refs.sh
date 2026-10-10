#!/usr/bin/env bash
# Copy every branch of a GitHub repo to archive/<branch>, then verify each copy from the
# API before anything destructive is allowed to happen.
#
# The ordering is the whole point. Replacing a repo's default branch is irreversible unless
# the commit it pointed at is still reachable by another name. So: copy first, prove the
# copies landed by reading them back from the server (not from your own push output), and
# only then force-push. Done this way, the destructive step has a documented undo.
#
# Originals are LEFT IN PLACE. Deleting them is a separate decision, needs admin, and
# should wait until a human has reviewed what was archived.
#
# Usage:
#   archive_refs.sh OWNER/REPO [options]
#     --prefix P      ref namespace for the copies (default: archive)
#     --tag NAME      also create an annotated tag at the default branch's commit
#     --only A,B,C    archive just these branches (default: all of them)
#     --workdir DIR   where to clone (default: a mktemp -d, removed on exit)
#     --dry-run       print what would be pushed, push nothing
#
# Exit status: 0 every copy verified, 1 a copy is missing or points at the wrong commit
# (DO NOT PROCEED), 2 usage or a missing tool.
set -euo pipefail

PREFIX=archive
TAG=
ONLY=
WORKDIR=
DRY=0
NWO=

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix)  PREFIX="$2"; shift 2 ;;
        --tag)     TAG="$2"; shift 2 ;;
        --only)    ONLY="$2"; shift 2 ;;
        --workdir) WORKDIR="$2"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
        -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)        echo "unknown option: $1" >&2; exit 2 ;;
        *)         NWO="$1"; shift ;;
    esac
done

[ -n "$NWO" ] || { echo "usage: archive_refs.sh OWNER/REPO [options]" >&2; exit 2; }
for t in git gh; do
    command -v "$t" >/dev/null || { echo "error: \`$t\` is required" >&2; exit 2; }
done

CLEANUP=0
if [ -z "$WORKDIR" ]; then
    WORKDIR=$(mktemp -d) ; CLEANUP=1
fi
trap '[ "$CLEANUP" = 1 ] && rm -rf "$WORKDIR"' EXIT

# A fresh clone, never the working tree: it guarantees the refs pushed are the server's own,
# so a stale local branch cannot be archived by accident under a name that implies otherwise.
CLONE="$WORKDIR/clone"
echo "==> cloning $NWO (fresh, so only server refs can be copied)"
git clone --quiet "https://github.com/$NWO.git" "$CLONE"
git -C "$CLONE" config --local credential.helper '!gh auth git-credential'

DEFAULT=$(gh api "repos/$NWO" -q .default_branch)
mapfile -t BRANCHES < <(git -C "$CLONE" for-each-ref --format='%(refname:strip=3)' refs/remotes/origin \
                        | grep -v '^HEAD$')

if [ -n "$ONLY" ]; then
    IFS=, read -r -a WANT <<< "$ONLY"
    KEEP=()
    for b in "${BRANCHES[@]}"; do
        for w in "${WANT[@]}"; do [ "$b" = "$w" ] && KEEP+=("$b"); done
    done
    BRANCHES=("${KEEP[@]}")
fi

# Never archive the archive. Without this, a second run copies archive/main to
# archive/archive/main, and the nesting grows every time.
KEEP=()
for b in "${BRANCHES[@]}"; do
    case "$b" in
        "$PREFIX"/*) echo "    skip  $b (already under $PREFIX/)" ;;
        *)           KEEP+=("$b") ;;
    esac
done
BRANCHES=("${KEEP[@]}")

[ ${#BRANCHES[@]} -gt 0 ] || { echo "error: no branches selected" >&2; exit 2; }

echo "==> $NWO: default branch '$DEFAULT', ${#BRANCHES[@]} branch(es) to copy under '$PREFIX/'"
declare -A WANTSHA
COLLIDE=0
for b in "${BRANCHES[@]}"; do
    WANTSHA["$b"]=$(git -C "$CLONE" rev-parse "refs/remotes/origin/$b")
    printf '    %s  %s -> %s/%s' "${WANTSHA[$b]:0:8}" "$b" "$PREFIX" "$b"
    # An existing copy is the thing this script exists to protect. Overwriting it with
    # today's branch tip would destroy the only record of where that branch used to point
    # -- the exact failure the archive is for -- so refuse rather than clobber.
    existing=$(gh api "repos/$NWO/branches/$PREFIX/$b" -q .commit.sha 2>/dev/null || true)
    if [ -n "$existing" ] && [ "$existing" != "${WANTSHA[$b]}" ]; then
        printf '  ** EXISTS at %s, would be overwritten **' "${existing:0:8}"
        COLLIDE=1
    elif [ -n "$existing" ]; then
        printf '  (already archived, unchanged)'
    fi
    printf '\n'
done

if [ "$COLLIDE" = 1 ]; then
    echo "==> REFUSING: one or more $PREFIX/ refs already exist and point somewhere else." >&2
    echo "    They are probably the record of an earlier move. Archive under a different" >&2
    echo "    --prefix (e.g. --prefix archive-$(date +%Y%m%d)) rather than overwriting." >&2
    exit 1
fi

if [ "$DRY" = 1 ]; then
    [ -n "$TAG" ] && echo "    tag $TAG -> ${WANTSHA[$DEFAULT]:0:8}"
    echo "==> dry run, nothing pushed"
    exit 0
fi

echo "==> pushing copies"
for b in "${BRANCHES[@]}"; do
    git -C "$CLONE" push origin "refs/remotes/origin/$b:refs/heads/$PREFIX/$b" 2>&1 | sed 's/^/    /'
done

if [ -n "$TAG" ]; then
    echo "==> tagging $DEFAULT at ${WANTSHA[$DEFAULT]:0:8} as '$TAG'"
    git -C "$CLONE" tag -a "$TAG" "${WANTSHA[$DEFAULT]}" \
        -m "$NWO $DEFAULT before the rehome"
    git -C "$CLONE" push origin "$TAG" 2>&1 | sed 's/^/    /'
fi

# Read the copies back from the server. Push output says what was sent, not what is there.
echo "==> verifying from the API"
FAIL=0
for b in "${BRANCHES[@]}"; do
    got=$(gh api "repos/$NWO/branches/$PREFIX/$b" -q .commit.sha 2>/dev/null || echo MISSING)
    if [ "$got" = "${WANTSHA[$b]}" ]; then
        printf '    ok    %s/%-30s %s\n' "$PREFIX" "$b" "${got:0:8}"
    else
        printf '    FAIL  %s/%-30s got %s want %s\n' "$PREFIX" "$b" \
               "${got:0:8}" "${WANTSHA[$b]:0:8}"
        FAIL=1
    fi
done

if [ -n "$TAG" ]; then
    obj=$(gh api "repos/$NWO/git/ref/tags/$TAG" -q .object.sha 2>/dev/null || echo MISSING)
    typ=$(gh api "repos/$NWO/git/ref/tags/$TAG" -q .object.type 2>/dev/null || echo "")
    if [ "$typ" = "tag" ]; then
        obj=$(gh api "repos/$NWO/git/tags/$obj" -q .object.sha 2>/dev/null || echo MISSING)
    fi
    if [ "$obj" = "${WANTSHA[$DEFAULT]}" ]; then
        printf '    ok    tag %-34s %s\n' "$TAG" "${obj:0:8}"
    else
        printf '    FAIL  tag %-34s got %s want %s\n' "$TAG" \
               "${obj:0:8}" "${WANTSHA[$DEFAULT]:0:8}"
        FAIL=1
    fi
fi

if [ "$FAIL" = 1 ]; then
    echo "==> VERIFICATION FAILED. Do not force-push anything: the old commits are not"
    echo "    provably reachable under another name yet." >&2
    exit 1
fi

echo "==> all copies verified. The undo for a force-push of '$DEFAULT' is now:"
echo "      git push --force origin $PREFIX/$DEFAULT:$DEFAULT"
echo "    Originals were left in place; deleting them is a separate, admin-only decision."
