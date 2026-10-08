---
name: slurm-job-watch
description: Watch SLURM/HPC batch jobs from submission to finish. Report queue position and estimated start, notice state changes, surface errors and progress from the job's own log, catch silent hangs, and summarize the outcome with sacct/seff. Use this whenever the user gives a job id and asks to watch, monitor, keep an eye on, check on, babysit, or tell them when a job starts or finishes. Also use it when they ask why a job is pending, whether it is stuck, or what happened to a job, even if they never say "monitor". Covers squeue/scontrol/sacct/sprio/seff on clusters such as NCSA Delta.
---

# Watching SLURM jobs

A job that is being watched should produce a few messages that each mean something: it
started, it hit an error, it went quiet, it finished. A stream of identical "still running"
lines does not count as watching. The cluster's view (squeue/sacct) tells you *where* a job is.
Only the job's own log tells you whether it is *doing* anything. A hung job and a busy job are
indistinguishable in squeue.

Two bundled scripts do the mechanical part:

| Script | Use for |
|---|---|
| `scripts/job_snapshot.sh JOBID...` or `--mine` | A one-shot answer: state, reason, estimated start, priority, log paths. For a finished job: sacct and seff |
| `scripts/watch_job.sh JOBID [--log GLOB] [--match REGEX] [--interval S] [--stall S]` | A continuous watch that prints only event lines (`STATE`, `START`, `LOG`, `STALL`, `NOLOG`, `FINAL`, `ERROR`) and exits when the job leaves the queue |

Both are read-only. Run them by absolute path from this skill's directory.

## Workflow

### 1. Establish what you are watching

- **Confirm the job is the user's.** `squeue -u $USER`, or the job name. A user often runs
  several unrelated workflows on one account. The job name is usually the fastest way to tell
  which project a job belongs to, so do not report on, or act on, a job from a different
  project as if it were the one asked about.
- **Snapshot first** with `job_snapshot.sh JOBID`. That gives the state, the reason, the
  estimated start, and `WorkDir`/`StdOut`.
- **Find the log that shows progress.** Often this is not `StdOut`. Many launchers `cd` into a
  per-job run directory and write their real transcript there (e.g.
  `$WORK_DIR/runs/<jobid>_<name>/campaign.log`). Read the batch script (`Command=` in the
  snapshot) to find it. If its directory does not exist until the job starts, pass a **glob**
  to `--log`; the watcher re-resolves it on every poll.
- **Pick a `--match` regex** for the lines that matter in *this* job's log: the error
  signatures, and the progress markers the user cares about. The default catches generic
  failure and finish words. A project-specific one is far better, e.g.
  `--match 'submitted r|reaped|promoted|Traceback|ERROR|WARNING|terminated'`. Keep it
  selective, because every matched line becomes a message.

### 2. Start the watch

Use a streaming background monitor (the Monitor tool in Claude Code), with `watch_job.sh` as
its command, so each event line arrives as a notification while you keep working:

```
command:     /path/to/slurm-job-watch/scripts/watch_job.sh 22726105 \
               --log '/work/nvme/proj/$USER/runs/22726105_*/campaign.log' \
               --match 'reaped|promoted|Traceback|ERROR' --interval 30 --stall 600
description: job 22726105: state changes, errors, progress
timeout_ms:  the window the user asked for ("ten minutes" -> 600000); otherwise the maximum
```

- **Honour the window the user names.** If they say "watch it for ten minutes", the watch
  ends at ten minutes, with one line saying where things stand. Monitors also have a hard
  ceiling (30 minutes in Claude Code). For a longer wait, re-arm when the expiry notice
  arrives, and say that you have done so.
- **Interval:** 30s is a good default. Never go below ~15s, because each poll is a request to
  the shared scheduler daemon. Jobs that queue for hours do not need 30s polls while pending;
  60–120s is fine there.
- **Stall threshold:** set `--stall` above the longest *normal* quiet period in this job's
  log. If the log emits a heartbeat every 60s, 300s is safe. If a step legitimately runs 20
  silent minutes, use more, or 0. A stall is a reason to look, not proof of a hang.
- **Without a streaming monitor** (another harness, or a plain terminal), run `watch_job.sh`
  in the background, redirected to a file, and read the file periodically.

### 3. While it runs

Each event is either routine or something the user would act on. Say so briefly, and do not
narrate routine lines at length.

- **Routine:** `STATE PENDING`/`RUNNING`, a moved `START` estimate, expected progress lines.
  Give a one-line acknowledgement at most.
- **Worth flagging promptly** (and worth a push notification, if the harness has one): the job
  started after a long wait, any `Traceback`/`ERROR`/`OOM`, `STALL`, `NOLOG`, a `FINAL` state
  other than `COMPLETED`, or an exit code other than `0:0`.
- **Compare against any prediction.** If the conversation stated what the run should do
  (e.g. "promoted after the second cycle"), check each event against it and say when reality
  diverges. That is usually what the user is actually watching for.
- **Pending for a long time?** See `references/pending-reasons.md` for what each `Reason`
  means and what, if anything, the user can do.

### 4. When it ends

`watch_job.sh` prints `FINAL <state> exit=<code> elapsed=<t> nodes=<list>` and exits. Follow
up with `job_snapshot.sh JOBID` for seff efficiency and memory, then report:

- the outcome in one line: state, exit code, elapsed against the time limit;
- what the log says happened. Read the tail of the progress log, not just the exit code: a
  job can exit 0 having done nothing useful, and a non-zero exit can come after all the
  useful work was saved;
- anything anomalous: a stall, a `CANCELLED`/`TIMEOUT`, or memory or CPU efficiency far
  below what was requested (useful sizing feedback for the next submission).

## Things not to do without asking

- **`scancel`, `scontrol hold/release/update`, or resubmitting.** These change shared,
  billed state. Even when a job looks hung, report the evidence (the last log line, how long
  it has been quiet) and let the user decide. A job that looks stuck may be in a long silent
  phase.
- **Run the job's workload on a login node** to "check" something. Reading logs and running
  read-only SLURM commands is fine. Starting the science is not.
- **Claim a job is fine because squeue says RUNNING**, or failed because it says
  `CANCELLED`. Check the log and sacct's `State`/`ExitCode`/`Reason` before saying either.
