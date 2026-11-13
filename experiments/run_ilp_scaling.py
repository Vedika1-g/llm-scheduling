"""Time-limited sparse MILP scaling and heuristic-gap comparison."""
import csv,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"experiments"))
from run_synthetic_experiments import make_workload
from scipy_ilp import solve_workload
from baselines import schedule_list
from proposed import e_magls,proposed
from simulator import check_schedule

out=ROOT/"experiments"/"results";out.mkdir(exist_ok=True);rows=[]
methods={"FCFS":lambda c,r:schedule_list(c,r,"FCFS"),"SDF":lambda c,r:schedule_list(c,r,"SDF"),
         "MAGLS":lambda c,r:schedule_list(c,r,"MAGLS"),"E-MAGLS":e_magls,"Portfolio+LS":proposed}
for n in (30,40,50):
    for seed in range(5):
        w=make_workload(n,62000+100*n+seed,tightness=.42)
        wp=out/f"ilp_scale_n{n}_s{seed}.json";wp.write_text(json.dumps(w,indent=2),encoding="utf-8")
        t0=time.perf_counter();ilp=solve_workload(wp,out/f"ilp_scale_n{n}_s{seed}_schedule.json",time_limit=15);wall=time.perf_counter()-t0
        for method,fn in methods.items():
            a=time.perf_counter();result=fn(w["config"],w["requests"]);rt=time.perf_counter()-a
            sched=result[0] if method=="Portfolio+LS" else result
            checked=check_schedule(w["config"],w["requests"],sched);flow=checked["total_flow_time"]
            bound=ilp["best_bound"]
            gap=(100*(flow-bound)/max(1,abs(bound))) if bound is not None else None
            rows.append({"n":n,"seed":seed,"method":method,"flow":flow,"heuristic_runtime_s":rt,
                "ilp_status":ilp["status"],"ilp_proven":ilp["optimality_proven"],"ilp_objective":ilp["objective"],
                "ilp_best_bound":bound,"ilp_gap":ilp["mip_gap"],"ilp_runtime_s":ilp["runtime_s"],
                "wall_runtime_s":wall,"variables":ilp["variables"],"constraints":ilp["constraints"],
                "gap_to_bound_pct":gap,"feasible":checked["feasible"]})
with (out/"ilp_scaling.csv").open("w",newline="",encoding="utf-8") as f:
    wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
for n in (30,40,50):
    q=[x for x in rows if x["n"]==n];instance=q[::len(methods)]
    print({"n":n,"instances":len(instance),"proven":sum(bool(x["ilp_proven"]) for x in instance),
        "avg_ilp_runtime_s":sum(float(x["ilp_runtime_s"]) for x in instance)/len(instance),
        "max_variables":max(int(x["variables"]) for x in instance),
        "max_solver_gap":max(float(x["ilp_gap"] or 0) for x in instance),
        "avg_gap_to_bound_pct":{m:round(sum(float(x["gap_to_bound_pct"]) for x in q if x["method"]==m)/len(instance),2) for m in methods}})
