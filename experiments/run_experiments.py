"""Reproducible synthetic evaluation; Python standard library only."""
from __future__ import annotations
import csv, json, random, statistics, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from baselines import schedule_list, portfolio
from proposed import e_magls, proposed
from simulator import check_schedule

OUT = ROOT / "experiments" / "results"

def make_workload(n: int, seed: int, tightness: float = 0.42, online: bool = False):
    rng = random.Random(seed)
    reqs=[]
    for i in range(n):
        p=max(2, min(32, round(rng.lognormvariate(2.0, 0.55))))
        d=max(1, min(16, round(rng.lognormvariate(1.15, 0.5))))
        arrival=max(0, round(rng.expovariate(0.18))) if online else 0
        reqs.append({"id":i+1,"p":p,"d":d,"a":arrival})
    M=max(r["p"]+r["d"]-1 for r in reqs)
    # Tightness is a fraction of the aggregate prompt footprint, bounded so
    # every request remains individually feasible.
    M=max(M, round(sum(r["p"] for r in reqs)*tightness))
    return {"config":{"M":M,"B":4 if online else None},"requests":reqs}

def p95(values):
    xs=sorted(values)
    return xs[max(0, (95*len(xs)+99)//100-1)]

def summarize(config, reqs, schedule, runtime):
    z=check_schedule(config,reqs,schedule)
    flows=[x["flow"] for x in z["per_request"].values()]
    memarea=sum(sum(z["memory_profile"].values()) for _ in [0])
    denominator=config["M"]*max(1,z["makespan"]+1)
    return {"total_flow":z["total_flow_time"],"mean_flow":statistics.mean(flows),"p95_flow":p95(flows),
            "memory_utilization":memarea/denominator,"makespan":z["makespan"],"runtime_s":runtime,"feasible":z["feasible"]}

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    methods={"FCFS":lambda c,r:schedule_list(c,r,"FCFS"),
             "SDF":lambda c,r:schedule_list(c,r,"SDF"),
             "MAGLS":lambda c,r:schedule_list(c,r,"MAGLS"),
             "E-MAGLS":e_magls,
             "Portfolio+LS":proposed}
    for n in (8,16,32,64):
        for seed in range(10):
            case=make_workload(n, 20261112+seed+1000*n)
            cfg,reqs=case["config"],case["requests"]
            (OUT/f"workload_n{n}_s{seed}.json").write_text(json.dumps(case,indent=2),encoding="utf-8")
            for name,fn in methods.items():
                t0=time.perf_counter(); result=fn(cfg,reqs); elapsed=time.perf_counter()-t0
                sched=result[0] if name=="Portfolio+LS" else result
                row={"n":n,"seed":seed,"M":cfg["M"],"method":name,**summarize(cfg,reqs,sched,elapsed)}
                row["mode"]="offline"
                rows.append(row)
    # A small finite-batch, nonzero-arrival check exercises both constraints
    # beyond the offline baseline study.
    for seed in range(10):
        case=make_workload(16, 909090+seed, online=True)
        cfg,reqs=case["config"],case["requests"]
        (OUT/f"workload_online_s{seed}.json").write_text(json.dumps(case,indent=2),encoding="utf-8")
        for name,fn in methods.items():
            t0=time.perf_counter(); result=fn(cfg,reqs); elapsed=time.perf_counter()-t0
            sched=result[0] if name=="Portfolio+LS" else result
            rows.append({"n":16,"seed":seed,"M":cfg["M"],"method":name,"mode":"online_B4",**summarize(cfg,reqs,sched,elapsed)})
    keys=list(rows[0])
    with (OUT/"per_instance.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    agg=[]
    for mode,n in [("offline",n) for n in (8,16,32,64)]+[("online_B4",16)]:
        for method in methods:
            group=[r for r in rows if r["n"]==n and r["method"]==method and r["mode"]==mode]
            agg.append({"n":n,"method":method,
                "mode":mode,
                **{k:statistics.mean(r[k] for r in group) for k in ("total_flow","mean_flow","p95_flow","memory_utilization","makespan","runtime_s")},
                "feasible_runs":sum(bool(r["feasible"]) for r in group),"runs":len(group)})
    with (OUT/"summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(agg[0]));w.writeheader();w.writerows(agg)
    (OUT/"summary.json").write_text(json.dumps(agg,indent=2),encoding="utf-8")
    make_svg(agg,OUT/"flow_time.svg")
    print(f"Wrote {len(rows)} runs to {OUT}")
    for r in agg: print(r)

def make_svg(agg,path):
    methods=list(dict.fromkeys(x["method"] for x in agg)); ns=(8,16,32,64)
    W,H=900,500; left,top,bottom=85,35,65; cw,ch=W-left-35,H-top-bottom
    ymax=max(r["total_flow"] for r in agg)*1.1
    colors=["#6b7280","#2563eb","#16a34a","#9333ea","#dc2626"]
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="100%" height="100%" fill="white"/>']
    for j in range(6):
        y=top+ch*j/5; val=ymax*(1-j/5)
        s.append(f'<path d="M {left} {y:.1f} H {left+cw}" stroke="#ddd"/><text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="12">{val:.0f}</text>')
    s.append(f'<path d="M {left} {top} V {top+ch} H {left+cw}" stroke="#222" fill="none"/>')
    for mi,m in enumerate(methods):
        pts=[]
        for i,n in enumerate(ns):
            r=next(x for x in agg if x["n"]==n and x["method"]==m)
            x=left+i*cw/(len(ns)-1); y=top+ch*(1-r["total_flow"]/ymax);pts.append((x,y))
        s.append(f'<polyline fill="none" stroke="{colors[mi]}" stroke-width="3" points="'+" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)+'"/>')
        for x,y in pts:s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colors[mi]}"/>')
        ly=top+mi*23; lx=left+30+mi*160
        s.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+22}" y2="{ly}" stroke="{colors[mi]}" stroke-width="3"/><text x="{lx+28}" y="{ly+4}" font-size="12">{m}</text>')
    for i,n in enumerate(ns):
        x=left+i*cw/(len(ns)-1);s.append(f'<text x="{x:.1f}" y="{top+ch+24}" text-anchor="middle" font-size="13">{n}</text>')
    s.append(f'<text x="{left+cw/2}" y="{H-14}" text-anchor="middle" font-size="14">Number of requests</text>')
    s.append(f'<text transform="translate(20 {top+ch/2}) rotate(-90)" text-anchor="middle" font-size="14">Mean total flow time (iterations)</text>')
    s.append('</svg>');path.write_text("\n".join(s),encoding="utf-8")

if __name__=="__main__":run()
