#!/bin/bash
# One-shot status for one or more SLURM jobs: where each is, why, and where its output goes.
#
#   job_snapshot.sh JOBID [JOBID...]      # specific jobs
#   job_snapshot.sh --mine                # every queued/running job of $USER
#
# Read-only: squeue, scontrol, sacct, seff. Safe to run as often as you like by hand,
# but do not loop it faster than ~15s - every call is a request to slurmctld.
set -u

if [ "${1:-}" = "--mine" ]; then
    echo "== queue for $USER"
    squeue -u "$USER" -o "%.10i %.28j %.9T %.10M %.10l %.20P %R"
    mapfile -t JOBS < <(squeue -h -u "$USER" -o %i)
else
    JOBS=("$@")
fi
[ ${#JOBS[@]} -eq 0 ] && { echo "no jobs"; exit 0; }

for J in "${JOBS[@]}"; do
    echo
    echo "== $J"
    q=$(squeue -h -j "$J" -o "%j|%T|%M|%l|%P|%R" 2>/dev/null)
    if [ -n "$q" ]; then
        IFS='|' read -r name state el lim part reason <<<"$q"
        echo "  name=$name state=$state elapsed=$el limit=$lim partition=$part reason/nodes=$reason"
        if [ "$state" = "PENDING" ]; then
            echo "  est start: $(squeue -h -j "$J" --start -o '%S (%r)' 2>/dev/null)"
            sprio -h -j "$J" -o "  priority=%Y age=%A fairshare=%F jobsize=%J" 2>/dev/null
        fi
        scontrol show job "$J" 2>/dev/null | grep -oE "(WorkDir|StdOut|StdErr|Command)=[^ ]+" | sed 's/^/  /'
    else
        echo "  not in queue - accounting:"
        sacct -X -j "$J" -o JobID,JobName%28,State,ExitCode,Elapsed,Start,End,NodeList 2>/dev/null | sed 's/^/  /'
        seff "$J" 2>/dev/null | grep -E "State|Wall-clock|CPU Efficiency|Memory Efficiency|Memory Utilized" | sed 's/^/  /'
    fi
done
