---
name: slurm-job-watch
description: Watch SLURM/HPC batch jobs from submission to finish. Report queue position and estimated start, notice state changes, surface errors and progress from the job's own log, catch silent hangs, and summarize the outcome with sacct/seff. Use this whenever the user gives a job id and asks to watch, monitor, keep an eye on, check on, babysit, or tell them when a job starts or finishes. Also use it when they ask why a job is pending, whether it is stuck, or what happened to a job, why there is no free GPU capacity, whether to switch partition or resubmit smaller, or which account a job will bill, even if they never say "monitor". Covers squeue/scontrol/sacct/sprio/seff on clusters such as NCSA Delta.
---

# Watching SLURM jobs

A job that is being watched should produce a few messages that each mean something: it
started, it hit an error, it went quiet, it finished. A stream of identical "still running"
lines does not count as watching. The cluster's view (squeue/sacct) tells you *where* a job is.
Only the job's own log tells you whether it is *doing* anything. A hung job and a busy job are
indistinguishable in squeue.

Three bundled scripts do the mechanical part:

| Script | Use for |
|---|---|
| `scripts/job_snapshot.sh JOBID...` or `--mine` | A one-shot answer: state, reason, estimated start, priority, account, log paths. For a finished job: sacct and seff |
| `scripts/watch_job.sh JOBID [--log GLOB] [--match REGEX] [--interval S] [--stall S] [--estimate-delta MIN] [--quiet-estimates]` | A continuous watch that prints only event lines (`STATE`, `START`, `LOG`, `STALL`, `NOLOG`, `FINAL`, `ERROR`) and exits when the job leaves the queue |
| `scripts/gpu_capacity.sh [--partition P] [--min-free N] [--show-unusable]` | Why a GPU job is pending: free GPUs per node, and per partition the free whole nodes, nodes with any free GPU, and pending queue depth |

All three are read-only. Run them by absolute path from this skill's directory.

## Workflow

### 1. Establish what you are watching

- **Confirm the job is the user's.** `squeue -u $USER`, or the job name. A user often runs
  several unrelated workflows on one account. The job name is usually the fastest way to tell
  which project a job belongs to, so do not report on, or act on, a job from a different
  project as if it were the one asked about.
- **Snapshot first** with `job_snapshot.sh JOBID`. That gives the state, the reason, the
  estimated start, the account, and `WorkDir`/`StdOut`.
- **Check which account it bills.** The snapshot's `Account=` (or
  `scontrol show job ID | grep -o 'Account=[^ ]*'`) is the project that pays for the run.
  An inherited `SBATCH_ACCOUNT` in the environment can belong to a different project
  entirely, and nothing warns you, so if a submission is part of the task, compare
  `$SBATCH_ACCOUNT` against the intended project, pass `--account=` explicitly, and confirm
  it on the submitted job. `sacctmgr -nP show assoc user=$USER format=account` lists the
  accounts the user may charge.
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
  arrives, and say that you have done so. A queue wait can need five or more arms, so before
  each re-arm run `job_snapshot.sh JOBID` and report what it says — the state, the reason, the
  current estimate — rather than only that the watch is back up.
- **Interval:** 30s is a good default. Never go below ~15s, because each poll is a request to
  the shared scheduler daemon. While PENDING nothing changes faster than a scheduler pass, so
  widen to 90–120s; tighten again once the job is RUNNING and the log is what you are reading.
- **Estimate noise:** on a long queue wait most `START` lines are the scheduler re-planning and
  mean nothing, and every emitted line becomes a notification. The default
  `--estimate-delta 10` reports only a move of more than ten minutes from the last estimate
  reported. For a wait already known to be hours long, `--quiet-estimates` drops estimate
  movement entirely and still reports the first estimate and any change of pending `Reason`.
- **Stall threshold:** set `--stall` above the longest *normal* quiet period in this job's
  log. If the log emits a heartbeat every 60s, 300s is safe. If a step legitimately runs 20
  silent minutes, use more, or 0. A stall is a reason to look, not proof of a hang.
- **Without a streaming monitor** (another harness, or a plain terminal), run `watch_job.sh`
  in the background, redirected to a file, and read the file periodically.

### 3. While it runs

Each event is either routine or something the user would act on. Say so briefly, and do not
narrate routine lines at length.

- **Routine:** `STATE PENDING`/`RUNNING` and expected progress lines. Give a one-line
  acknowledgement at most.
- **Start estimates: report a change of pattern, never each estimate.** Estimates oscillate,
  recede and snap back constantly, and almost none of that is news; what is diagnostic is
  which of the four patterns in `references/pending-reasons.md` the movement fits. An estimate
  that recedes in step with the wall clock is the job's backfill slot being taken again — it
  is not approaching the front, so do not report it as progress.
- **Worth flagging promptly** (and worth a push notification, if the harness has one): the job
  started after a long wait, any `Traceback`/`ERROR`/`OOM`, `STALL`, `NOLOG`, a `FINAL` state
  other than `COMPLETED`, or an exit code other than `0:0`.
- **Compare against any prediction.** If the conversation stated what the run should do
  (e.g. "promoted after the second cycle"), check each event against it and say when reality
  diverges. That is usually what the user is actually watching for.
- **A changed pending `Reason` is an event.** `Resources` -> `Priority` is a demotion, not a
  relabel: a higher-priority job has landed ahead. `watch_job.sh` emits a `STATE` line for it.
- **Pending for a long time?** See `references/pending-reasons.md` for what each `Reason`
  means, how to read a moving start estimate, and what, if anything, the user can do. For a
  GPU job, answer "why is it pending" with `gpu_capacity.sh`, which counts free *GPUs*; node
  states and idle CPU counts will tell you there is capacity when there is none.

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
  billed state. Before even *suggesting* a resubmit to another partition or a smaller job,
  run the checklist in `references/pending-reasons.md`: the alternative usually has a far
  deeper queue, or no free GPU either, in which case the suggestion costs the user their
  accrued priority for nothing. Even when a job looks hung, report the evidence (the last
  log line, how long it has been quiet) and let the user decide. A job that looks stuck may
  be in a long silent phase.
- **Run the job's workload on a login node** to "check" something. Reading logs and running
  read-only SLURM commands is fine. Starting the science is not.
- **Claim a job is fine because squeue says RUNNING**, or failed because it says
  `CANCELLED`. Check the log and sacct's `State`/`ExitCode`/`Reason` before saying either.
