"""Sparse time-indexed MILP solver using SciPy's HiGHS-backed milp API."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from baselines import schedule_list
from simulator import load_workload, check_schedule

def solve_workload(workload_path, output_path=None, time_limit=None, mip_rel_gap=None):
    config,requests=load_workload(workload_path)
    M,B=config["M"],config.get("B")
    if not requests:raise ValueError("Workload must contain at least one request")
    for r in requests:
        if r["p"]+r["d"]-1>M:raise ValueError(f"Request {r['id']} cannot fit alone")
    if B==0:raise ValueError("Batch limit B=0 makes every nonempty workload infeasible")

    incumbent=schedule_list(config,requests,"MAGLS")
    upper=check_schedule(config,requests,incumbent)["total_flow_time"]
    minimum=sum(r["d"]-1 for r in requests)
    delay_budget=int(round(upper-minimum))
    domains=[]
    for i,r in enumerate(requests):
        for s in range(r["a"],r["a"]+delay_budget+1):domains.append((i,s))
    col={x:j for j,x in enumerate(domains)};nvar=len(domains)
    if nvar==0:raise RuntimeError("No start-time variables were constructed")

    c=np.array([domains[j][1]+requests[i]["d"]-1-requests[i]["a"] for j,(i,_) in enumerate(domains)],dtype=float)
    rows=[];cols=[];vals=[];lower=[];upper_rows=[];row=0
    for i,r in enumerate(requests):
        for s in range(r["a"],r["a"]+delay_budget+1):rows.append(row);cols.append(col[i,s]);vals.append(1.0)
        lower.append(1.0);upper_rows.append(1.0);row+=1

    horizon=max(s+requests[i]["d"]-1 for i,s in domains)
    for t in range(0,horizon+1):
        mem_terms=[];active_terms=[]
        for j,(i,s) in enumerate(domains):
            r=requests[i]
            if s<=t<s+r["d"]:
                mem_terms.append((j,r["p"]+t-s));active_terms.append(j)
        for j,v in mem_terms:rows.append(row);cols.append(j);vals.append(float(v))
        lower.append(-np.inf);upper_rows.append(float(M));row+=1
        if B is not None:
            for j in active_terms:rows.append(row);cols.append(j);vals.append(1.0)
            lower.append(-np.inf);upper_rows.append(float(B));row+=1

    A=coo_matrix((vals,(rows,cols)),shape=(row,nvar),dtype=float).tocsr()
    constraints=LinearConstraint(A,np.asarray(lower),np.asarray(upper_rows))
    options={"disp":False}
    if time_limit is not None:
        if time_limit<=0:raise ValueError("time_limit must be positive")
        options["time_limit"]=float(time_limit)
    if mip_rel_gap is not None:
        if not 0<=mip_rel_gap<1:raise ValueError("mip_rel_gap must be in [0,1)")
        options["mip_rel_gap"]=float(mip_rel_gap)

    started=time.perf_counter()
    result=milp(c,integrality=np.ones(nvar,dtype=np.uint8),bounds=Bounds(np.zeros(nvar),np.ones(nvar)),constraints=constraints,options=options)
    elapsed=time.perf_counter()-started
    status_names={0:"optimal",1:"limit",2:"infeasible",3:"unbounded",4:"solver_error"}
    out={"status":status_names.get(result.status,"unknown"),"message":result.message,"runtime_s":elapsed,
         "variables":nvar,"constraints":row,"optimality_proven":result.status==0,
         "objective":None,"best_bound":getattr(result,"mip_dual_bound",None),
         "mip_gap":getattr(result,"mip_gap",None),"schedule":None,"checker_result":None}
    if result.x is not None:
        schedule={}
        for j,(i,s) in enumerate(domains):
            if result.x[j]>.5:schedule[requests[i]["id"]]=s
        if len(schedule)!=len(requests):raise RuntimeError("MILP did not select exactly one start per request")
        checked=check_schedule(config,requests,schedule)
        if not checked["feasible"]:raise RuntimeError(f"MILP result failed checker: {checked['violations']}")
        obj=checked["total_flow_time"]
        if result.fun is not None and abs(obj-result.fun)>1e-5:raise RuntimeError("MILP and checker objectives differ")
        out.update({"objective":obj,"schedule":schedule,"checker_result":checked})
        if output_path:
            Path(output_path).parent.mkdir(parents=True,exist_ok=True)
            Path(output_path).write_text(json.dumps({str(k):v for k,v in schedule.items()},indent=2),encoding="utf-8")
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workload",default="data/sample_workload.json")
    p.add_argument("--output",default="experiments/ilp_schedule.json")
    p.add_argument("--time-limit",type=float,default=None)
    p.add_argument("--gap",type=float,default=None)
    a=p.parse_args()
    result=solve_workload(a.workload,a.output,a.time_limit,a.gap)
    for key in ("status","message","runtime_s","variables","constraints","optimality_proven","objective","best_bound","mip_gap","schedule"):
        print(f"{key}: {result[key]}")

if __name__=="__main__":main()
