#!/usr/bin/env bash
# Read-only inventory of HPC run directories, joined to sacct.
#
#   inventory.sh ROOT [--prefix JOBNAME_PREFIX] [--since YYYY-MM-DD]
#
# For every directory under ROOT whose name starts with a SLURM job id, prints one row:
#   job id, dir, size, file count, which of the usual pieces are present, manifest fields,
#   and sacct's partition / nodes / TRES / elapsed / state / exit code.
# With --prefix, it also lists the user's jobs whose name starts with that prefix but that
# have NO directory under ROOT ("no surviving data"). That second list is how you prove
# nothing was missed.
set -euo pipefail
ROOT=${1:?usage: inventory.sh ROOT [--prefix P] [--since DATE]}; shift
PREFIX=""; SINCE=$(date -d '-90 days' +%F)
while [[ $# -gt 0 ]]; do
  case $1 in
    --prefix) PREFIX=$2; shift 2;;
    --since)  SINCE=$2; shift 2;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done

declare -A DIR
for d in "$ROOT"/*/; do
  b=$(basename "$d"); id=${b%%[!0-9]*}
  [[ -n $id ]] && DIR[$id]=$d
done

printf '%s\n' "== run directories under $ROOT"
printf 'job|dir|size|files|pieces|manifest|partition|nodes|tres|elapsed|state|exit\n'
ids=$(printf '%s,' "${!DIR[@]}"); ids=${ids%,}
declare -A ACCT
if [[ -n $ids ]]; then
  while IFS='|' read -r jid part nn tres el st ex; do
    ACCT[$jid]="$part|$nn|$tres|$el|$st|$ex"
  done < <(sacct -X -n -P -j "$ids" --format=JobID,Partition,NNodes,AllocTRES,Elapsed,State,ExitCode 2>/dev/null || true)
fi
for id in $(printf '%s\n' "${!DIR[@]}" | sort -n); do
  d=${DIR[$id]}
  size=$(du -sh "$d" 2>/dev/null | cut -f1)
  files=$(find "$d" -type f 2>/dev/null | wc -l)
  pieces=""
  for p in slurm.out manifest.json work runinfo; do [[ -e $d/$p ]] && pieces+="$p "; done
  compgen -G "$d/*.log" >/dev/null && pieces+="*.log "
  compgen -G "$d/*/provenance" >/dev/null && pieces+="provenance "
  compgen -G "$d/*/jobs/ledger.jsonl" >/dev/null && pieces+="ledger "
  man=""
  if [[ -f $d/manifest.json ]]; then
    man=$(python3 -I -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(" ".join(f"{k}={m[k]}" for k in ("campaign","git_sha","git_dirty","exit_code","backfilled") if k in m))' "$d/manifest.json" 2>/dev/null || echo unreadable)
  fi
  printf '%s|%s|%s|%s|%s|%s|%s\n' "$id" "$(basename "$d")" "$size" "$files" "${pieces% }" "$man" "${ACCT[$id]:-not in sacct}"
done

if [[ -n $PREFIX ]]; then
  printf '\n%s\n' "== jobs named ${PREFIX}* since $SINCE with no directory under $ROOT"
  printf 'job|name|partition|elapsed|state\n'
  sacct -X -n -P -u "$USER" -S "$SINCE" --format=JobID,JobName%40,Partition,Elapsed,State 2>/dev/null \
    | awk -F'|' -v p="$PREFIX" 'index($2,p)==1' \
    | while IFS='|' read -r jid name part el st; do
        if [[ -z ${DIR[$jid]:-} ]]; then printf '%s|%s|%s|%s|%s\n' "$jid" "$name" "$part" "$el" "$st"; fi
      done
fi
