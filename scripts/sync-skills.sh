#!/usr/bin/env bash
# Sync this repo's skills into a Claude Code skills directory as symlinks.
#
# Creates a link for every skills/<name>/ in this checkout, repoints links that
# have gone stale, and removes links that point into this checkout at a skill
# that no longer exists (renamed or deleted). Anything in the target that is a
# real file or directory, or a symlink to somewhere else, is left alone and
# reported.
#
# Usage: scripts/sync-skills.sh [-n|--dry-run] [-q|--quiet] [TARGET_DIR]
#        TARGET_DIR defaults to $CLAUDE_SKILLS_DIR, else ~/.claude/skills.

set -uo pipefail

usage() {
    sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

dry_run=0
quiet=0
target=""

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--dry-run) dry_run=1 ;;
        -q|--quiet) quiet=1 ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "sync-skills: unknown option: $1" >&2; usage >&2; exit 2 ;;
        *)
            if [ -n "$target" ]; then
                echo "sync-skills: too many arguments" >&2
                exit 2
            fi
            target="$1"
            ;;
    esac
    shift
done

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
skills_dir="$repo_root/skills"
[ -d "$skills_dir" ] || { echo "sync-skills: no skills/ directory in $repo_root" >&2; exit 1; }

if [ -z "$target" ]; then
    target="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
fi

say() { [ "$quiet" -eq 1 ] || echo "$@"; }
run() { if [ "$dry_run" -eq 1 ]; then say "would: $*"; else "$@"; fi; }

conflicts=0

if [ ! -d "$target" ]; then
    run mkdir -p "$target"
    say "created $target"
fi

# Link every skill in this checkout.
for dir in "$skills_dir"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    src="$skills_dir/$name"
    dest="$target/$name"

    if [ ! -f "$src/SKILL.md" ]; then
        say "skip   $name (no SKILL.md)"
        continue
    fi

    if [ -L "$dest" ]; then
        current="$(readlink -- "$dest")"
        case "$current" in
            /*) resolved="$current" ;;
            *)  resolved="$target/$current" ;;
        esac
        if [ "$(cd -- "$(dirname -- "$resolved")" 2>/dev/null && pwd)/$(basename -- "$resolved")" = "$src" ]; then
            say "ok     $name"
            continue
        fi
        if [ -e "$resolved" ]; then
            echo "CONFLICT $name -> $current (symlink to something else; not touching)" >&2
            conflicts=$((conflicts + 1))
            continue
        fi
        run ln -sfn -- "$src" "$dest"
        say "relink $name (was dangling -> $current)"
        continue
    fi

    if [ -e "$dest" ]; then
        echo "CONFLICT $name (real file or directory in $target; not touching)" >&2
        conflicts=$((conflicts + 1))
        continue
    fi

    run ln -s -- "$src" "$dest"
    say "link   $name"
done

# Drop our own links whose skill is gone from this checkout.
for dest in "$target"/*; do
    [ -L "$dest" ] || continue
    current="$(readlink -- "$dest")"
    case "$current" in
        /*) resolved="$current" ;;
        *)  resolved="$target/$current" ;;
    esac
    case "$resolved" in
        "$skills_dir"/*) ;;
        *) continue ;;
    esac
    [ -e "$resolved" ] && continue
    run rm -- "$dest"
    say "unlink $(basename "$dest") (gone from this checkout)"
done

if [ "$conflicts" -gt 0 ]; then
    echo "sync-skills: $conflicts conflict(s) left in place; remove them by hand and re-run" >&2
    exit 1
fi
