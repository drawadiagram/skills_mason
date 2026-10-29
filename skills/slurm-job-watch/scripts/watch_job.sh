#!/bin/bash
# Watch one SLURM job and print a line only when something worth acting on happens.
# Built to be the command of a streaming monitor (each stdout line = one event), but
# fine to run in a terminal.
#
#   watch_job.sh JOBID [--log GLOB] [--match REGEX] [--interval S] [--stall S]
#                      [--estimate-delta MIN] [--quiet-estimates]
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
#   --estimate-delta MIN
#                  while PENDING, only report a start estimate that has moved more than
#                  MIN minutes from the last one *reported* (so an estimate that
#                  oscillates back to a reported value stays silent). A receding
#                  estimate is rate-limited to one line per MIN minutes as well; an
#                  estimate pulling in is reported at once (default 10; 0 restores a
#                  line per change). The scheduler
#                  re-plans constantly and most of that movement means nothing, so on a
#                  multi-hour queue wait one line per change buries every real event.
#   --quiet-estimates
#                  never report estimate movement at all. The first estimate, and any
#                  change of pending Reason, still get a line. Use it when the job is
#                  known to be queued for hours.
#
# Event lines, all prefixed so a reader can filter:
#   STATE  <state> <elapsed> <reason/nodes>   on every state change, and on a change of
#                                             pending Reason (`Resources` -> `Priority`
#                                             is a demotion, not a relabel)
#   START  est <time> (<reason>)              pending, when the estimate moves enough
#   LOG    <matched line>
#   STALL  no log growth for <n>s while RUNNING (<log>)
#   NOLOG  running 120s+ but no log matches <glob>  (once; jobs create run dirs late)
#   FINAL  <state> exit=<code> elapsed=<t> ...  then exit 0
#   ERROR  <message>                            then exit 1
set -u

JOB=${1:?usage: watch_job.sh JOBID [--log GLOB] [--match REGEX] [--interval S] [--stall S] [--estimate-delta MIN] [--quiet-estimates]}
shift
LOG_GLOB="" ; INTERVAL=30 ; STALL=600 ; EST_DELTA=10 ; QUIET_EST=0
DEFAULT_MATCH='Traceback|Error|ERROR|FAIL|Killed|OOM|oom-kill|CANCELLED|TIME LIMIT|DUE TO|Segmentation|core dumped|timed out|done|finished|complete'
MATCH=$DEFAULT_MATCH
while [ $# -gt 0 ]; do
    case "$1" in
        --log) LOG_GLOB=$2; shift 2 ;;
        --match) MATCH=$2; shift 2 ;;
        --interval) INTERVAL=$2; shift 2 ;;
        --stall) STALL=$2; shift 2 ;;
        --estimate-delta) EST_DELTA=$2; shift 2 ;;
        --quiet-estimates) QUIET_EST=1; shift ;;
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

prev_state="" ; prev_start="" ; prev_reason="" ; prev_est_epoch="" ; last_est_emit=0 ; offset=0 ; cur_log="" ; last_growth=$(date +%s) ; run_since=0
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
                est_time=${est%%|*} ; est_reason=${est##*|} ; now=$(date +%s) ; emit=0
                # A changed Reason is a real event in its own right - a job can be demoted
                # from Resources to Priority when a higher-priority job lands - so it is
                # reported whatever the estimate did, and it carries the estimate with it.
                if [ -n "$prev_reason" ] && [ "$est_reason" != "$prev_reason" ]; then
                    echo "STATE $state $elapsed $est_reason (was $prev_reason)"
                    emit=1
                fi
                [ -z "$prev_start" ] && emit=1
                est_epoch=$(date -d "$est_time" +%s 2>/dev/null) || est_epoch=""
                # Compared against the last estimate *reported*, not the last one seen, so a
                # value that oscillates back to one already reported stays silent.
                if [ $emit -eq 0 ] && [ "$QUIET_EST" -eq 0 ]; then
                    if [ -n "$est_epoch" ] && [ -n "$prev_est_epoch" ]; then
                        d=$(( est_epoch - prev_est_epoch ))
                        if [ $d -lt 0 ]; then
                            # Pulling in: capacity freed. Report without waiting.
                            [ $(( -d )) -gt $(( EST_DELTA * 60 )) ] && emit=1
                        elif [ $d -gt $(( EST_DELTA * 60 )) ] \
                                && [ $(( now - last_est_emit )) -ge $(( EST_DELTA * 60 )) ]; then
                            # Receding: usually the backfill slot being taken again, which
                            # is true but is not progress. At most one line per MIN minutes.
                            emit=1
                        fi
                    else
                        emit=1          # N/A <-> a real time is itself news
                    fi
                fi
                if [ $emit -eq 1 ]; then
                    echo "START est $est_time ($est_reason)"
                    prev_est_epoch=$est_epoch ; last_est_emit=$now
                fi
                prev_start=$est ; prev_reason=$est_reason
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
