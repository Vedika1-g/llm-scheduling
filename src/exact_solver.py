"""Small-instance exact branch-and-bound solver for independent validation."""
from __future__ import annotations
from simulator import check_schedule

def solve_exact(config: dict, requests: list[dict], seed_schedule: dict | None = None):
    """Find a proven optimum for tiny instances by exhaustive bounded search.

    The incumbent gives a valid upper bound. Since every request's minimum
    flow is d_i-1, the remaining start-delay budget safely bounds each domain.
    This is intended only for small instances, not as an ILP replacement.
    """
    if not requests:
        return {"objective": 0, "schedule": {}, "nodes": 1}
    M, B = config["M"], config.get("B")
    if any(r["p"]+r["d"]-1>M for r in requests) or B == 0:
        return {"objective": None, "schedule": None, "nodes": 0}
    from baselines import schedule_list
    incumbent = dict(seed_schedule or schedule_list(config, requests, "MAGLS"))
    best = check_schedule(config, requests, incumbent)
    if not best["feasible"]: raise ValueError("Seed schedule must be feasible")
    best_obj=best["total_flow_time"]
    base=sum(r["d"]-1 for r in requests)
    best_delay=best_obj-base
    ordered=sorted(requests,key=lambda r:(-(r["p"]+r["d"]),r["a"],r["id"]))
    horizon=max(r["a"] for r in requests)+sum(r["d"] for r in requests)+best_delay+1
    mem=[0]*(horizon+1); active=[0]*(horizon+1); schedule={}; nodes=0

    def visit(k,used_delay):
        nonlocal best_obj,best_delay,incumbent,nodes
        nodes+=1
        if used_delay>best_delay:return
        if k==len(ordered):
            objective=base+used_delay
            if objective<best_obj:
                best_obj,best_delay,incumbent=objective,used_delay,dict(schedule)
            return
        r=ordered[k]; max_start=min(horizon-r["d"]+1,r["a"]+best_delay-used_delay)
        for s in range(r["a"],max_start+1):
            extra=s-r["a"]
            if used_delay+extra>best_delay:break
            feasible=True
            for t in range(s,s+r["d"]):
                if mem[t]+r["p"]+t-s>M or (B is not None and active[t]+1>B):
                    feasible=False;break
            if not feasible:continue
            for t in range(s,s+r["d"]):mem[t]+=r["p"]+t-s;active[t]+=1
            schedule[r["id"]]=s
            visit(k+1,used_delay+extra)
            del schedule[r["id"]]
            for t in range(s,s+r["d"]):mem[t]-=r["p"]+t-s;active[t]-=1
    visit(0,0)
    checked=check_schedule(config,requests,incumbent)
    if not checked["feasible"] or checked["total_flow_time"]!=best_obj:
        raise AssertionError("Exact solver's returned schedule failed independent validation")
    return {"objective":best_obj,"schedule":incumbent,"nodes":nodes}
