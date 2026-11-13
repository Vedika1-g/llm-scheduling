"""
Run all LLM scheduling experiments and write results.csv
Author: Yasaswitha (24CS2015)
Usage: python experiments/run_experiments.py
"""
import json, csv, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json(path):
    with open(path) as f:
        return json.load(f)

def build_jobs(workload):
    jobs = {}
    lst = []
    if isinstance(workload, dict):
        lst = workload.get("jobs") or workload.get("requests") or []
        if not lst:
            for k, v in workload.items():
                if isinstance(v, dict):
                    jobs[str(k)] = v
            return jobs
    elif isinstance(workload, list):
        lst = workload
    for j in lst:
        jid = j.get("id", j.get("job_id", j.get("name")))
        jobs[str(jid)] = j
    return jobs

def getv(job, *keys, default=0):
    for k in keys:
        if k in job:
            return job[k]
    return default

def evaluate(method, path, jobs):
    data = load_json(path)
    if isinstance(data, list):
        sched = data
    elif isinstance(data, dict):
        sched = data.get("schedule") or data.get("jobs") or data.get("assignments")
        if sched is None:
            # Repository schedule format: request ID -> integer start time.
            sched = [{"job_id": jid, "start": start} for jid, start in data.items()]
    else:
        sched = []
    total_flow = 0; makespan = 0; tardiness = 0; n = 0; scheduled_ids = set()
    for item in sched:
        if isinstance(item, dict):
            jid = item.get("job_id", item.get("id", item.get("job")))
            start = item.get("start", item.get("start_time", 0)) or 0
            end = item.get("end", item.get("end_time", item.get("completion_time")))
            if end is None:
                job = jobs.get(str(jid), {})
                duration = getv(job, "d", "decode_duration", "processing_time", default=1)
                end = start + duration - 1
        else:
            jid, start, end = item, 0, 0
        job = jobs.get(str(jid), {})
        a = getv(job, "a", "arrival", "arrival_time", default=0)
        d = getv(job, "deadline", "due", "due_time", default=None)
        total_flow += float(end) - float(a)
        if d is not None:
            tardiness += max(0, float(end) - float(d))
        makespan = max(makespan, float(end))
        scheduled_ids.add(str(jid))
        n += 1
    missing = len(set(jobs) - scheduled_ids)
    return {"method": method, "n_jobs": n, "missing_jobs": missing,
            "complete": missing == 0, "total_flow_time": round(total_flow, 2),
            "avg_flow_time": round(total_flow / n, 2) if n else 0,
            "makespan": round(makespan, 2), "total_tardiness": round(tardiness, 2)}

def main():
    workload = load_json(os.path.join(BASE, "data", "sample_workload.json"))
    jobs = build_jobs(workload)
    files = {"ilp": "ilp_schedule.json", "batch": "batch_schedule.json",
             "memory": "memory_schedule.json", "arrival": "arrival_schedule.json"}
    rows = []
    for method, fname in files.items():
        r = evaluate(method, os.path.join(BASE, "experiments", fname), jobs)
        print(r)
        rows.append(r)
    out = os.path.join(BASE, "experiments", "results.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["method","n_jobs","missing_jobs","complete","total_flow_time","avg_flow_time","makespan","total_tardiness"])
        w.writeheader(); w.writerows(rows)
    print("Wrote", out)

if __name__ == "__main__":
    main()
