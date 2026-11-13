"""Compare heuristics with a proven optimum on tiny instances."""
import csv,json,sys,time,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"experiments"))
from run_synthetic_experiments import make_workload
from exact_solver import solve_exact
from scipy_ilp import solve_workload
from baselines import schedule_list
from proposed import proposed
from simulator import check_schedule

out=ROOT/"experiments"/"results";out.mkdir(exist_ok=True)
rows=[]
for seed in range(10):
    w=make_workload(6,771200+seed,tightness=.55);c,r=w["config"],w["requests"]
    workload_file=out/f"exact_workload_{seed}.json"
    workload_file.write_text(json.dumps(w,indent=2),encoding="utf-8")
    exact=solve_exact(c,r);obj=exact["objective"]
    ilp=solve_workload(workload_file)
    if not ilp["optimality_proven"] or ilp["objective"]!=obj:
        raise AssertionError(f"MILP and exhaustive optimum disagree for seed {seed}: {ilp} vs {exact}")
    for method in ("FCFS","SDF","MAGLS","Portfolio+LS"):
        t=time.perf_counter()
        result=proposed(c,r) if method=="Portfolio+LS" else schedule_list(c,r,method)
        sched=result[0] if method=="Portfolio+LS" else result
        sec=time.perf_counter()-t;value=check_schedule(c,r,sched)["total_flow_time"]
        rows.append({"seed":seed,"n":len(r),"method":method,"exact_objective":obj,"ilp_objective":ilp["objective"],
                     "ilp_proven":ilp["optimality_proven"],"ilp_runtime_s":ilp["runtime_s"],"ilp_mip_gap":ilp["mip_gap"],
                     "objective":value,"relative_gap_pct":100*(value-ilp["objective"])/max(1,obj),"runtime_s":sec,"exact_nodes":exact["nodes"]})
with (out/"exact_small.csv").open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
for m in ("FCFS","SDF","MAGLS","Portfolio+LS"):
    q=[x for x in rows if x["method"]==m]
    print(m,"avg gap %",round(statistics.mean(x["relative_gap_pct"] for x in q),2),"optimal cases",sum(x["relative_gap_pct"]==0 for x in q),"/10")
print("Instances",len(set(x["seed"] for x in rows)),"requests each: 6; exhaustive nodes total",sum(x["exact_nodes"] for x in rows[::4]))
