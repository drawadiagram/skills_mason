# Why is my job pending?

The `Reason` column of `squeue`, and `Reason=` in `scontrol show job`. Most pending time is
`Priority` or `Resources`, which is normal: the job is simply waiting its turn. The rest
usually mean the job *cannot* start as submitted, and someone has to change something.

| Reason | Meaning | What the user can do |
|---|---|---|
| `Priority` | Higher-priority jobs are ahead of it in this partition | Wait. `sprio -j ID` shows the components; age grows the longer it waits |
| `Resources` | It is next in line, waiting for nodes to free up | Wait. `squeue --start -j ID` gives the scheduler's estimate. That estimate assumes running jobs use their full time limit, so the real start is often earlier |
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

## Useful one-liners

```bash
squeue -j ID --start -o "%i %S %r"          # estimated start and reason
sprio -j ID                                 # priority components
squeue -p PARTITION -t PD | wc -l           # how deep the partition's pending queue is
sinfo -p PARTITION -o "%a %D %t"            # node states in the partition
sacct -X -j ID -o JobID,State,ExitCode,Elapsed,Reason   # after it leaves the queue
seff ID                                     # efficiency and memory of a finished job
```

## Interactive or debug partitions

Partitions such as `*-interactive` or `*-debug` usually trade a short maximum `--time` for a
faster start. A job pending with `Resources` there typically starts within minutes. If it
does not, the partition's few nodes are busy, and a regular partition may start sooner
despite the longer queue.
