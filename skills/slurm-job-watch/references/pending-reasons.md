# Why is my job pending?

The `Reason` column of `squeue`, and `Reason=` in `scontrol show job`. Most pending time is
`Priority` or `Resources`, which is normal: the job is simply waiting its turn. The rest
usually mean the job *cannot* start as submitted, and someone has to change something.

| Reason | Meaning | What the user can do |
|---|---|---|
| `Priority` | Higher-priority jobs are ahead of it in this partition | Wait. `sprio -j ID` shows the components; age grows the longer it waits |
| `Resources` | It is next in line, waiting for nodes to free up | Wait. `squeue --start -j ID` gives the scheduler's estimate. That estimate assumes running jobs use their full time limit, so the real start is often earlier. It is not a promise: do not tell the user "you are next" on a `Resources` reading alone, because one higher-priority arrival demotes the job back to `Priority` |
| `Dependency` | Waiting on another job (`--dependency`) | Check the parent job. If the parent failed, this shows `DependencyNeverSatisfied` and will never start |
| `DependencyNeverSatisfied` | The dependency can no longer be met | Cancel and resubmit without the dependency (ask first) |
| `QOSMaxJobsPerUserLimit`, `AssocGrpJobsLimit`, `QOSMaxSubmitJobPerUserLimit` | The user or account is at its concurrent-job cap | Wait for their own jobs to finish |
| `AssocGrpBillingMinutes`, `AssocGrpCPUMinutesLimit`, `AssocGrpGRESMinutes` | The account's allocation is exhausted or capped | Nothing on the user's side; the PI or allocation manager has to act. Worth flagging immediately, because it will not clear by waiting |
| `PartitionTimeLimit` | `--time` exceeds the partition maximum | Resubmit with a shorter `--time` or to another partition |
| `PartitionNodeLimit`, `QOSMaxNodePerJobLimit` | More nodes requested than allowed | Resubmit smaller |
| `ReqNodeNotAvail`, `ReqNodeNotAvail, Reserved for maintenance` | The requested or needed nodes are down or reserved, often for an upcoming maintenance window | If `--time` overlaps the reservation, a shorter `--time` may let it start before the window |
| `JobHeldUser`, `JobHeldAdmin` | Held explicitly | `scontrol release ID` for a user hold (ask first). Admin holds need support |
| `BadConstraints`, `InvalidAccount`, `InvalidQOS` | Unsatisfiable as written | Fix the request and resubmit |
| `BeginTime` | Submitted with `--begin` in the future | Expected |
| `None` (briefly) | Just submitted, not yet evaluated | Look again in a minute |

## Reading a moving start estimate

`squeue --start` is re-derived on every scheduler pass, so it moves constantly. Almost none
of that movement is news. The *pattern* is what means something:

| What the estimate does | What it means | Report it? |
|---|---|---|
| Oscillates between two values | The scheduler is re-planning between two candidate slots | No |
| Recedes in step with the wall clock (each poll pushes it out by about one poll) | The job's backfill slot keeps being taken by something shorter. It is **not** moving towards the front | No — and never as progress |
| Pulls in sharply | Something real freed up | Yes, one line |
| Jumps far out | A higher-priority job landed, or a node was lost | Yes, one line, and check `Reason` and the node states |

The operational rule is to report a *change of pattern*, not an estimate. A real watch saw
about 17 estimate changes across two and a half hours of pending and not one of them meant
anything. `watch_job.sh --estimate-delta MIN` / `--quiet-estimates` enforce this in the
script, so the pattern is yours to read and not the user's to wade through.

## A changed `Reason` is an event

`Resources` -> `Priority` is a demotion, not a relabel: the job was next in line and now is
not. Compare priorities when it happens — `sprio -j ID` against the job that overtook it. A
gap of roughly 3x (e.g. 11000 against 3425) is a QoS or partition boost rather than accrued
age, and `age` will never close it: the job waits for the boosted work to drain, not for its
own priority to grow. Say that plainly instead of "it is climbing the queue".

## Useful one-liners

```bash
squeue -j ID --start -o "%i %S %r"          # estimated start and reason
sprio -j ID                                 # priority components
squeue -h -p PARTITION -t PD | wc -l        # how deep the partition's pending queue is
sinfo -p PARTITION -o "%a %D %t"            # node states - see the GPU caveat below
sacct -X -j ID -o JobID,State,ExitCode,Elapsed,Reason   # after it leaves the queue
seff ID                                     # efficiency and memory of a finished job
```

## Interactive or debug partitions

Partitions such as `*-interactive` or `*-debug` usually trade a short maximum `--time` for a
faster start. A job pending with `Resources` there typically starts within minutes. If it
does not, the partition's few nodes are busy, and a regular partition may start sooner
despite the longer queue — but check that against the queue depth and the free-GPU count
below before saying so, because on a busy machine it is usually false.

## Is there actually any free GPU?

For a whole-node GPU job, `sinfo` is the wrong instrument. It will happily show dozens of
`mix` nodes with hundreds of idle CPUs, which looks like capacity and is not: those nodes have
every GPU allocated, and the idle CPUs are unusable to a GPU job. The question is free
*GPUs*, which means `CfgTRES`'s `gres/gpu=N` minus `AllocTRES`'s `gres/gpu=M`, per node:

```bash
scripts/gpu_capacity.sh                       # every GPU partition: free GPUs, free nodes, queue depth
scripts/gpu_capacity.sh --partition PART      # just one
scripts/gpu_capacity.sh --show-unusable       # with the DOWN/DRAIN/MAINT nodes and their Reason
```

On one real check this turned "dozens of `mix` nodes" into exactly one node with any free GPU
across all twelve GPU partitions.

Two traps:

- **The state filter.** Nodes whose `State` contains `DOWN`, `DRAIN`, `MAINT`, `FAIL` or
  `INVAL` are not capacity even when their GPUs read as free. States combine, so a single node
  can be `IDLE+DRAIN+MAINTENANCE+RESERVED`; match against the whole string. A filter that is
  slightly too wide returns nothing, and nothing reads as "the cluster is full" rather than
  "my parse is broken" — which is why `gpu_capacity.sh` ends with a `SCAN examined=/usable=/
  skipped=` line. Read it. An implausible `skipped` is a bug in the filter, not a busy cluster.
- **A node freeing up is not a node becoming yours.** A node that releases all its GPUs and
  pulls the estimate in by half an hour can go `IDLE+DRAIN` with `Reason=NHC:` a minute later
  — a node health check drain — and the estimate snaps straight back out. Health-check drains
  are routine and remove capacity silently. Before telling the user a start is imminent,
  re-check that node: `scontrol show node NODE | grep -E "State|Reason"`.

## Before suggesting another partition, or a smaller job

Both halves have to be checked, and usually the answer is "stay put":

1. **Free GPUs anywhere?** `gpu_capacity.sh`. If no partition has a free GPU, no resubmission
   of any shape starts sooner — and shrinking the job does not help either, because there are
   no part-free nodes to land on.
2. **Queue depth in the alternative.** `squeue -h -p PART -t PD | wc -l`. An interactive
   partition with 26 jobs pending is a far better place to be than the general partition with
   2453, or its preempt sibling with 431, however many nodes those have.
3. **Hardware compatibility.** A partition is only a candidate if the job's software runs on
   its accelerators: `gpuMI100x8` is AMD and is not an option for a CUDA container. The
   `gpu=` column of the `PART` lines names the model.
4. **What a resubmit costs.** The job loses its accrued age priority and goes to the back.

Only if all four favour the move is it worth raising — and it is still the user's call.
