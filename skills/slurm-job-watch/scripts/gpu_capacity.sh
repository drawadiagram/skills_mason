#!/bin/bash
# Why is a GPU job pending? Count free *GPUs* per node, not free CPUs or node states.
#
#   gpu_capacity.sh [--partition P] [--min-free N] [--show-unusable]
#
#   --partition P    only nodes in partition P (default: every partition with GPUs).
#   --min-free N     only print NODE lines with at least N free GPUs (default 1).
#   --show-unusable  also print a NODE line for each node skipped as DOWN/DRAIN/etc.
#
# `sinfo` is the wrong tool here. A node in state `mix` with 100 idle CPUs is still
# useless to a whole-node GPU job if all its GPUs are allocated, and Delta has dozens
# of those. The honest question is CfgTRES gres/gpu minus AllocTRES gres/gpu, per node,
# which is what this reads out of `scontrol show node -o`.
#
# Nodes whose State contains DOWN, DRAIN, MAINT, FAIL or INVAL are not counted as
# capacity: their GPUs may read as free but nothing will schedule onto them. That
# filter is deliberately crude, and a crude filter that is slightly too wide returns
# nothing and *looks* like "the cluster is full". So every run ends with a SCAN line
# giving examined/usable/skipped counts - if skipped is implausibly high, suspect the
# filter, not the cluster. States combine (`IDLE+DRAIN+MAINTENANCE+RESERVED` is one
# real node), so each node is matched against the whole State string, not an equality.
#
# Read-only: scontrol, squeue. Output lines, all prefixed so a reader can filter:
#   NODE  <node> free=<n>/<cfg> state=<state> gpu=<model> parts=<list>[ reason=<r>]
#   PART  <partition> nodes=<n> whole_free=<n> any_free=<n> free_gpus=<n> ...
#   SCAN  examined=<n> usable=<n> skipped=<n> (...)  partitions=<n>
set -u

PART_FILTER="" ; MIN_FREE=1 ; SHOW_UNUSABLE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --partition) PART_FILTER=$2; shift 2 ;;
        --min-free) MIN_FREE=$2; shift 2 ;;
        --show-unusable) SHOW_UNUSABLE=1; shift ;;
        *) echo "ERROR unknown argument $1"; exit 1 ;;
    esac
done

if ! command -v scontrol >/dev/null 2>&1; then
    echo "ERROR scontrol not found - run this on a cluster login or compute node"; exit 1
fi

# Pending depth per partition first: a partition with free GPUs and 2000 jobs waiting
# is not an opportunity. A job submitted to several partitions counts in each.
# The PEND marker keeps the two inputs apart: an NR==FNR test would silently treat
# node lines as pending lines on a cluster with an empty pending queue.
squeue -h -t PD -o "PEND %P" 2>/dev/null \
| awk -v part="$PART_FILTER" -v minfree="$MIN_FREE" -v showbad="$SHOW_UNUSABLE" '
function val(line, key,   s) {
    # Values are space-free except Reason=, which runs to end of line; caller handles that.
    if (match(line, key "=[^ ]*")) { s = substr(line, RSTART, RLENGTH); sub(key "=", "", s); return s }
    return ""
}
function addmodel(p, m) {
    if (m != "" && gpu_model[p] !~ ("(^|/)" m "(/|$)"))
        gpu_model[p] = (gpu_model[p] == "" ? m : gpu_model[p] "/" m)
}
function gpus(tres,   s) {
    if (match(tres, /gres\/gpu=[0-9]+/)) { s = substr(tres, RSTART, RLENGTH); sub(/.*=/, "", s); return s + 0 }
    return 0
}
$1 == "PEND" { n = split($2, pp, ","); for (i = 1; i <= n; i++) pending[pp[i]]++; next }

{
    name = val($0, "NodeName"); if (name == "") next
    cfg = gpus(val($0, "CfgTRES")); if (cfg == 0) next     # not a GPU node
    examined++
    state = val($0, "State")
    parts = val($0, "Partitions")
    model = val($0, "Gres"); sub(/^gpu:/, "", model); sub(/:.*/, "", model); sub(/\(.*/, "", model)
    npart = split(parts, pl, ",")
    if (part != "") {
        keep = 0
        for (i = 1; i <= npart; i++) if (pl[i] == part) keep = 1
        if (!keep) { examined--; next }
    }

    if (state ~ /DOWN|DRAIN|MAINT|FAIL|INVAL/) {
        skipped++
        if (state ~ /DOWN/)   s_down++
        if (state ~ /DRAIN/)  s_drain++
        if (state ~ /MAINT/)  s_maint++
        if (state ~ /FAIL/)   s_fail++
        if (state ~ /INVAL/)  s_inval++
        for (i = 1; i <= npart; i++) { seen[pl[i]] = 1; unusable[pl[i]]++; addmodel(pl[i], model) }
        if (showbad) {
            reason = ""
            if (match($0, /Reason=.*/)) reason = substr($0, RSTART + 7)
            printf "NODE %s free=-/%d state=%s gpu=%s parts=%s%s\n", \
                name, cfg, state, model, parts, (reason == "" ? "" : " reason=" reason)
        }
        next
    }

    usable++
    free = cfg - gpus(val($0, "AllocTRES"))
    if (free < 0) free = 0
    for (i = 1; i <= npart; i++) {
        p = pl[i]; seen[p] = 1; nodes[p]++; addmodel(p, model)
        if (free == cfg) whole[p]++
        if (free > 0) { any[p]++; freegpu[p] += free }
    }
    if (free >= minfree) {
        shown++
        printf "NODE %s free=%d/%d state=%s gpu=%s parts=%s\n", name, free, cfg, state, model, parts
    }
}

END {
    if (!shown) print "NODE none - no usable node has " minfree "+ free GPU(s)"
    for (p in seen) {
        if (part != "" && p != part) continue        # sibling partitions share nodes; their counts would be partial
        npartitions++
        printf "PART %s nodes=%d whole_free=%d any_free=%d free_gpus=%d unusable=%d pending=%d gpu=%s\n", \
            p, nodes[p] + 0, whole[p] + 0, any[p] + 0, freegpu[p] + 0, unusable[p] + 0, \
            pending[p] + 0, (gpu_model[p] == "" ? "?" : gpu_model[p]) | "sort"
    }
    close("sort")
    brk = ""
    if (s_down)  brk = brk " DOWN=" s_down
    if (s_drain) brk = brk " DRAIN=" s_drain
    if (s_maint) brk = brk " MAINT=" s_maint
    if (s_fail)  brk = brk " FAIL=" s_fail
    if (s_inval) brk = brk " INVAL=" s_inval
    printf "SCAN examined=%d usable=%d skipped=%d%s partitions=%d\n", \
        examined + 0, usable + 0, skipped + 0, (brk == "" ? "" : " (" substr(brk, 2) ")"), npartitions + 0
}
' - <(scontrol show node -o 2>/dev/null)
