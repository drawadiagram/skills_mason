#!/bin/bash
# Watch one SLURM job and print a line only when something worth acting on happens.
# Built to be the command of a streaming monitor (each stdout line = one event), but
# fine to run in a terminal.
#
#   watch_job.sh JOBID [--log GLOB] [--match REGEX] [--interval S] [--stall S]
#
#   --log GLOB     the log that shows progress. A glob is re-resolved every poll, because
#                  run directories often do not exist until the job starts. Default: the
#                  job's StdOut from scontrol.
#   --match REGEX  extended regex selecting log lines to emit (default: common
#                  error/failure/finish signatures - see DEFAULT_MATCH).
#   --interval S   poll period in seconds (default 30; below 15 just loads slurmctld).
#   --stall S      while RUNNING, warn once if the log has not grown for S seconds
#                  (default 600; 0 disables). A hung job and a busy job look identical
#                  in squeue - only the log tells them apart.
#
# Event lines, all prefixed so a reader can filter:
#   STATE  <state> <elapsed> <reason/nodes>   on every state change
#   START  est <time> (<reason>)              pending, when the scheduler's estimate moves
#   LOG    <matched line>
#   STALL  no log growth for <n>s while RUNNING (<log>)
#   NOLOG  running 120s+ but no log matches <glob>  (once; jobs create run dirs late)
#   FINAL  <state> exit=<code> elapsed=<t> ...  then exit 0
#   ERROR  <message>                            then exit 1
set -u

JOB=${1:?usage: watch_job.sh JOBID [--log GLOB] [--match REGEX] [--interval S] [--stall S]}
shift
LOG_GLOB="" ; INTERVAL=30 ; STALL=600
DEFAULT_MATCH='Traceback|Error|ERROR|FAIL|Killed|OOM|oom-kill|CANCELLED|TIME LIMIT|DUE TO|Segmentation|core dumped|timed out|done|finished|complete'
MATCH=$DEFAULT_MATCH
while [ $# -gt 0 ]; do
    case "$1" in
        --log) LOG_GLOB=$2; shift 2 ;;
        --match) MATCH=$2; shift 2 ;;
        --interval) INTERVAL=$2; shift 2 ;;
        --stall) STALL=$2; shift 2 ;;
        *) echo "ERROR unknown argument $1"; exit 1 ;;
    esac
done

# Both tools exit 0 for a job they have never heard of, so test for output, not status.
if [ -z "$(squeue -h -j "$JOB" -o %i 2>/dev/null)" ] \
        && [ -z "$(sacct -n -X -j "$JOB" -o JobID 2>/dev/null)" ]; then
    echo "ERROR job $JOB not known to squeue or sacct"; exit 1
fi
if [ -z "$LOG_GLOB" ]; then
    LOG_GLOB=$(scontrol show job "$JOB" 2>/dev/null | sed -n 's/^ *StdOut=//p' | head -1)
fi

prev_state="" ; prev_start="" ; offset=0 ; cur_log="" ; last_growth=$(date +%s) ; run_since=0
stall_warned=0 ; nolog_warned=0

final() {
    # sacct can lag the job leaving squeue by a few seconds; retry briefly.
    local row=""
    for _ in 1 2 3 4 5 6; do
        row=$(sacct -n -X -P -j "$JOB" -o State,ExitCode,Elapsed,NodeList,Reason 2>/dev/null | head -1)
        case "$row" in ""|PENDING*|RUNNING*|COMPLETING*) sleep 10 ;; *) break ;; esac
    done
    IFS='|' read -r st ec el nl rs <<<"$row"
    echo "FINAL ${st:-UNKNOWN} exit=${ec:-?} elapsed=${el:-?} nodes=${nl:-?}${rs:+ reason=$rs}${cur_log:+ log=$cur_log}"
    exit 0
}

while true; do
    line=$(squeue -h -j "$JOB" -o "%T|%M|%R" 2>/dev/null)
    if [ -z "$line" ]; then
        final
    fi
    IFS='|' read -r state elapsed reason <<<"$line"

    if [ "$state" != "$prev_state" ]; then
        echo "STATE $state $elapsed $reason"
        prev_state=$state
        last_growth=$(date +%s)
        [ "$state" = RUNNING ] && run_since=$(date +%s)
    fi

    case "$state" in
        PENDING)
            est=$(squeue -h -j "$JOB" --start -o "%S|%r" 2>/dev/null)
            if [ -n "$est" ] && [ "$est" != "$prev_start" ]; then
                echo "START est ${est%%|*} (${est##*|})"
                prev_start=$est
            fi ;;
        RUNNING|COMPLETING)
            # Re-resolve: the log may only appear once the job has made its run dir.
            # shellcheck disable=SC2086
            resolved=$(ls -1d $LOG_GLOB 2>/dev/null | head -1)
            if [ -n "$resolved" ] && [ "$resolved" != "$cur_log" ]; then
                cur_log=$resolved ; offset=0
            fi
            if [ -n "$cur_log" ] && [ -f "$cur_log" ]; then
                size=$(stat -c %s "$cur_log" 2>/dev/null || echo 0)
                if [ "$size" -lt "$offset" ]; then offset=0; fi      # truncated/rotated
                if [ "$size" -gt "$offset" ]; then
                    tail -c +$((offset + 1)) "$cur_log" | head -c $((size - offset)) \
                        | grep -E -- "$MATCH" | cut -c1-300 | sed 's/^/LOG /'
                    offset=$size ; last_growth=$(date +%s) ; stall_warned=0
                elif [ "$STALL" -gt 0 ] && [ $stall_warned -eq 0 ] \
                        && [ $(( $(date +%s) - last_growth )) -ge "$STALL" ]; then
                    echo "STALL no log growth for $(( $(date +%s) - last_growth ))s while RUNNING ($cur_log)"
                    stall_warned=1
                fi
            elif [ $nolog_warned -eq 0 ] && [ $(( $(date +%s) - run_since )) -ge 120 ]; then
                echo "NOLOG running $(( $(date +%s) - run_since ))s but no log matches ${LOG_GLOB:-<none>}"
                nolog_warned=1
            fi ;;
    esac
    sleep "$INTERVAL"
done
