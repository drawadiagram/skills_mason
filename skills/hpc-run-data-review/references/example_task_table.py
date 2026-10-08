"""Worked example: flatten one project's run ledgers into a one-row-per-task CSV.

Written for IMPRESS-A (`<jobid>_<campaign>/<campaign>-D/jobs/ledger.jsonl`, whose
`outcome.tasks[]` hold per-task metrics, QC gates and output artifacts; plus
`provenance/graphs.jsonl` for trust and `provenance/results.jsonl` for node verdicts).
Another project's logs will differ - run scripts/jsonl_fields.py first and adapt the
field names, but keep the pattern:

  * join per-run context (trust, verdict, duration) onto per-task rows;
  * one `m_<name>` column per metric, the union across all rows, blank where absent;
  * failed gates as `gate(role)=observed`, so the CSV says *why*, not just *that*;
  * artifact paths made relative to the job dir (ledgers record absolute paths, which
    are wrong after a move and meaningless on a laptop), with sha256 alongside.

    python3 -I example_task_table.py ROOT OUT.csv JOBDIR [JOBDIR...]
"""
import csv, json, sys
from datetime import datetime
from pathlib import Path

root = Path(sys.argv[1]); out = Path(sys.argv[2]); jobs = sys.argv[3:]

def rel(p):
    return "work/" + p.rsplit("/work/", 1)[1] if p and "/work/" in p else p

rows, mkeys = [], []
for jd in jobs:
    d = root / jd
    job, campaign = jd.split("_", 1)
    cd = next(d.glob("*-D"))
    trusted, verdict = {}, {}
    gp, rp = cd / "provenance/graphs.jsonl", cd / "provenance/results.jsonl"
    for l in gp.read_text().splitlines() if gp.exists() else []:
        e = json.loads(l)
        if "run" in e and "trusted" in e: trusted[e["run"]] = e["trusted"]
    for l in rp.read_text().splitlines() if rp.exists() else []:
        e = json.loads(l)
        if "run" in e: verdict[e["run"]] = e.get("qc")
    submitted = {}
    for l in (cd / "jobs/ledger.jsonl").read_text().splitlines():
        e = json.loads(l)
        if e.get("status") == "submitted":
            submitted[e["job_id"]] = (e["ts"], e.get("cycle"), e.get("signature"))
        o = e.get("outcome")
        if not o: continue
        t0, cyc, sig = submitted.get(o["run_id"], (None, None, o.get("signature")))
        dur = (datetime.fromisoformat(e["ts"]) - datetime.fromisoformat(t0)).total_seconds() if t0 else ""
        for t in o.get("tasks", []):
            gates = t.get("qc", {}).get("gates", [])
            failed = [f'{g["gate"]}({g.get("role","?")})={g.get("observed")}' for g in gates if g.get("outcome") == "fail"]
            outs = t.get("outputs", {}) or {}
            r = {"job": job, "campaign": campaign, "run": o["run_id"], "cycle": cyc,
                 "signature": sig, "trusted": trusted.get(o["run_id"], ""),
                 "run_state": o.get("state"), "run_seconds": dur,
                 "node_verdict": verdict.get(o["run_id"], o.get("qc", {}).get("verdict", "")),
                 "lineage": t["task_id"].split("_")[0].lstrip("r"), "task_id": t["task_id"],
                 "tool": t["tool"], "task_qc": t.get("qc", {}).get("verdict"),
                 "failed_gates": "; ".join(failed),
                 "gpu_hours_est": t.get("cost", {}).get("gpu_hours", ""),
                 "outputs": "; ".join(f'{k}={rel(v.get("path"))}' for k, v in outs.items() if isinstance(v, dict)),
                 "sha256": "; ".join(f'{k}={v.get("sha256")}' for k, v in outs.items() if isinstance(v, dict))}
            for k, v in (t.get("metrics") or {}).items():
                r["m_" + k] = v
                if "m_" + k not in mkeys: mkeys.append("m_" + k)
            rows.append(r)
base = list(rows[0].keys() - set(mkeys)) if rows else []
cols = [c for c in ["job","campaign","run","cycle","signature","trusted","run_state","run_seconds","node_verdict",
        "lineage","task_id","tool","task_qc","failed_gates","gpu_hours_est"]] + mkeys + ["outputs","sha256"]
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
print(len(rows), "rows")
