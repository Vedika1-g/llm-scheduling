"""Build a compact, template-styled research manuscript from experiment CSVs."""
from pathlib import Path
import csv, math
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether, Image)
from reportlab.graphics.shapes import Drawing, String, Line, PolyLine, Circle

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/"output"/"pdf"/"llm_inference_request_scheduling.pdf"
rows=list(csv.DictReader((ROOT/"experiments"/"results"/"summary.csv").open(encoding="utf-8")))
exact_rows=list(csv.DictReader((ROOT/"experiments"/"results"/"exact_small.csv").open(encoding="utf-8")))
scale_rows=list(csv.DictReader((ROOT/"experiments"/"results"/"ilp_scaling.csv").open(encoding="utf-8")))
def get(method,n=64,mode="offline"):
    return next(r for r in rows if r["method"]==method and int(r["n"])==n and r["mode"]==mode)
def f(method,key,n=64,mode="offline"): return float(get(method,n,mode)[key])

offline=["FCFS","SDF","MAGLS","E-MAGLS","Portfolio+LS"]
online=["FCFS","SDF","MAGLS","E-MAGLS","Portfolio+LS"]
reduction=lambda ref,method:100*(1-f(method,"total_flow")/f(ref,"total_flow"))

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name="PaperTitle",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=19,leading=22,alignment=TA_CENTER,textColor=colors.HexColor("#18324b"),spaceAfter=10))
styles.add(ParagraphStyle(name="Authors",parent=styles["Normal"],fontSize=9.5,leading=13,alignment=TA_CENTER,spaceAfter=5))
styles.add(ParagraphStyle(name="Abstract",parent=styles["BodyText"],fontSize=9,leading=12,alignment=TA_JUSTIFY,spaceAfter=5))
styles.add(ParagraphStyle(name="H1x",parent=styles["Heading1"],fontSize=13,leading=16,textColor=colors.HexColor("#173b57"),spaceBefore=6,spaceAfter=5,keepWithNext=True))
styles.add(ParagraphStyle(name="H2x",parent=styles["Heading2"],fontSize=10.5,leading=13,textColor=colors.HexColor("#245b7a"),spaceBefore=5,spaceAfter=3,keepWithNext=True))
styles.add(ParagraphStyle(name="BodyX",parent=styles["BodyText"],fontSize=8.6,leading=11.5,alignment=TA_JUSTIFY,spaceAfter=5))
styles.add(ParagraphStyle(name="CaptionX",parent=styles["Normal"],fontSize=8,leading=10,alignment=TA_CENTER,textColor=colors.HexColor("#333333"),spaceBefore=2,spaceAfter=5))
styles.add(ParagraphStyle(name="RefX",parent=styles["BodyText"],fontSize=8,leading=10,firstLineIndent=-14,leftIndent=14,spaceAfter=5))

def P(t,style="BodyX"): return Paragraph(t,styles[style])
def chart():
    d=Drawing(460,205); L,R,T,B=48,15,22,32; W,H=460-L-R,205-T-B
    ns=[8,16,32,64]; vals={m:[float(next(r["total_flow"] for r in rows if r["method"]==m and int(r["n"])==n and r["mode"]=="offline")) for n in ns] for m in offline}
    ymax=max(max(v) for v in vals.values())*1.1
    for k in range(6):
        y=B+H*k/5; val=ymax*k/5
        d.add(Line(L,y,L+W,y,strokeColor=colors.HexColor("#d9e0e5"),strokeWidth=.6))
        d.add(String(L-6,y-3,f"{val:.0f}",fontSize=7,textAnchor="end",fillColor=colors.HexColor("#4b5563")))
    d.add(Line(L,B,L,B+H,strokeColor=colors.black));d.add(Line(L,B,L+W,B,strokeColor=colors.black))
    palette=["#64748b","#2563eb","#16a34a","#9333ea","#dc2626"]
    for idx,m in enumerate(offline):
        points=[]
        for i,n in enumerate(ns): points.append((L+i*W/3,B+H*vals[m][i]/ymax))
        d.add(PolyLine(points,strokeColor=colors.HexColor(palette[idx]),strokeWidth=1.8))
        for x,y in points:d.add(Circle(x,y,2.4,fillColor=colors.HexColor(palette[idx]),strokeColor=colors.HexColor(palette[idx])))
        lx=L+idx*84; ly=205-10
        d.add(Line(lx,ly,lx+12,ly,strokeColor=colors.HexColor(palette[idx]),strokeWidth=2))
        label=m.replace("Portfolio+LS","Port.+LS")
        d.add(String(lx+15,ly-2.5,label,fontSize=6.5))
    for i,n in enumerate(ns):
        x=L+i*W/3;d.add(String(x,B-14,str(n),fontSize=8,textAnchor="middle"))
    d.add(String(L+W/2,5,"Number of requests",fontSize=8,textAnchor="middle"))
    d.add(String(10,B+H/2,"Mean total flow",fontSize=8,textAnchor="middle",angle=90))
    return d

def schedule_diagram():
    d=Drawing(460,115); labels=["arrival", "rank", "fit check", "start", "release"]
    xs=[42,132,232,332,423]; y=66
    for i,(x,label) in enumerate(zip(xs,labels)):
        d.add(Circle(x,y,22,fillColor=colors.HexColor("#eaf2f8"),strokeColor=colors.HexColor("#246082"),strokeWidth=1.1))
        d.add(String(x,y-3,label,fontSize=7,textAnchor="middle",fillColor=colors.HexColor("#18324b")))
        if i<len(xs)-1:d.add(Line(x+23,y,xs[i+1]-23,y,strokeColor=colors.HexColor("#64748b"),strokeWidth=1.2,endArrow=1))
    d.add(String(230,20,"A start is accepted only if its full decode window fits memory M and batch B.",fontSize=8,textAnchor="middle"))
    return d

def make_table(data,widths,header=True):
    t=Table(data,colWidths=widths,repeatRows=1 if header else 0,hAlign="CENTER")
    cmds=[("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),7.4),("LEADING",(0,0),(-1,-1),9),
          ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
          ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
          ("LINEABOVE",(0,0),(-1,0),.8,colors.HexColor("#18324b")),("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor("#18324b")),
          ("LINEBELOW",(0,-1),(-1,-1),.8,colors.HexColor("#18324b"))]
    if header:cmds.append(("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"))
    for i in range(1,len(data)):
        if i%2==0:cmds.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor("#f3f6f8")))
    t.setStyle(TableStyle(cmds));return t

def header_footer(canvas,doc):
    canvas.saveState();w,h=letter
    canvas.setFont("Helvetica",7);canvas.setFillColor(colors.HexColor("#536471"))
    canvas.drawString(doc.leftMargin,h-27,"Advanced Algorithms Project | PS-1")
    canvas.drawRightString(w-doc.rightMargin,h-27,"RGIPT, 2026-27")
    canvas.setStrokeColor(colors.HexColor("#ccd5dc"));canvas.line(doc.leftMargin,h-33,w-doc.rightMargin,h-33)
    canvas.line(doc.leftMargin,35,w-doc.rightMargin,35)
    canvas.drawString(doc.leftMargin,23,"LLM inference request scheduling under a GPU memory limit")
    canvas.drawRightString(w-doc.rightMargin,23,str(doc.page));canvas.restoreState()

story=[]
story += [Spacer(1,14),P("LLM Inference Request Scheduling under GPU Memory Limits","PaperTitle"),
P("Abhishri Krishna (24CS2004) | Vedika Choudhary (24CS3060) | Sonali Swaraj (24CS3052)<br/>Manya Dixit (24CS2026) | Yasashwitha (24CS2015)<br/>Department of Computer Science and Engineering, RGIPT<br/><b>Presented to Dr. Aakash Yadav</b>","Authors"),Spacer(1,7),P("Abstract","H2x")]
abstract=(f"We implement and evaluate list-scheduling policies for offline LLM request scheduling under a discrete GPU-memory budget. We compare FCFS, SDF, MAGLS, event-jump E-MAGLS, and a ranking portfolio with local search. Across 40 synthetic offline workloads (8-64 requests, 10 seeds per size), every schedule was feasible. At 64 requests, MAGLS reduced mean total flow by 20.4% vs. FCFS and 8.0% vs. SDF; the portfolio reduced it by 20.6% and 8.3%. On 10 six-request cases, the heuristics' mean gaps to proven MILP optima were 15.90% (FCFS), 7.94% (SDF), 2.60% (MAGLS), and 1.36% (portfolio). For five cases each at 30, 40, and 50 requests, the MILP proved 5, 2, and 3 optima within 15 seconds; the largest residual solver gap was 0.70%. E-MAGLS matched MAGLS schedules but ran 1.74 times slower at n=64. Results use synthetic inputs and a scheduling abstraction, not GPU-engine measurements.")
story += [P(abstract,"Abstract"),P("Keywords: LLM serving; KV cache; total flow time; memory-aware scheduling; synthetic evaluation","Abstract"),P("1. Introduction","H1x"),
P("Autoregressive inference retains a key-value (KV) cache for each active request. Prompt tokens determine the initial cache footprint, and decoding adds cache state over time. Continuous batching and paged cache management improve utilization, but admission and scheduling still interact with memory capacity. Orca schedules at iteration granularity, while vLLM's PagedAttention manages KV-cache blocks and reduces fragmentation (Yu et al., 2022; Kwon et al., 2023). More recent systems optimize throughput, latency, or goodput through chunked prefill, phase disaggregation, and scheduling policies (Agrawal et al., 2024; Zhong et al., 2024)."),
P("This project isolates a smaller combinatorial question: given request sizes, arrivals, and decode lengths, when should each non-preemptive request start to minimize summed completion-minus-arrival time while respecting memory and a batch cap? The model is useful for algorithm comparison, but its unit-time and linear-cache assumptions are not a latency model. We therefore report synthetic scheduling metrics and do not interpret them as measured GPU performance."),
P("The work product is an independently checked simulator, four ranking policies plus a portfolio/local-search procedure, and a seeded experiment harness. We report results against FCFS and SDF, including a finite-batch arrival check. We also give a hardness reduction for decode durations greater than one, while separating that inherited single-machine hardness from hardness caused specifically by memory growth.")]
story += [PageBreak(),P("2. Problem Model and Related Work","H1x"),P("2.1 Discrete-time formulation","H2x"),
P("Let I be the requests. Request i has prompt length p_i, decode duration d_i, and arrival iteration a_i. A schedule chooses an integer start s_i >= a_i. It is active at iterations s_i,...,s_i+d_i-1, completes at C_i=s_i+d_i-1, and contributes flow F_i=C_i-a_i. At active time t, its memory is p_i+(t-s_i). For GPU memory capacity M and optional batch limit B, feasibility requires, for every t, sum of active memory <= M and the number of active requests <= B. The objective is minimize sum_i F_i. Memory is measured in abstract token-equivalent units; page/block rounding and fragmentation are excluded."),
P("The team convention starts a request at its arrival iteration (a_i), consistent with the repository simulator and hand example. Each request runs without preemption on one abstract GPU; arrival times, prompt/decode lengths, M, and B are known; every request must fit alone. Iterations have equal duration. These assumptions make the model reproducible, but omit variable iteration latency, preemption, recomputation, chunked prefill, uncertain output lengths, and multiple GPUs."),
P("2.2 Position relative to prior work","H2x"),
P("The model is an abstraction of memory-constrained admission and decode scheduling, not a replacement for production serving. PagedAttention uses block-based allocation; Orca uses iteration-level scheduling; Sarathi-Serve balances throughput and latency with chunked-prefill scheduling; DistServe separates prefill and decode to target service-level objectives (Kwon et al., 2023; Yu et al., 2022; Agrawal et al., 2024a; Zhong et al., 2024). FastServe explores preemption and token-level scheduling (Wu et al., 2026). These systems model execution and service objectives beyond our single-resource discrete abstraction. The supplied project base paper studies variable prefill and decode lengths (LLM Serving Optimization with Variable Prefill and Decode Lengths, 2025); an exact claim-by-claim comparison and implementation of its algorithms are not included in this implementation."),
P("Other recent systems address dynamic rescheduling and fragmentation, prompt sharing, phase splitting, scalable simulation, structured generation, or adapter multiplexing (Sun et al., 2024; Srivatsa et al., 2024; Patel et al., 2024; Agrawal et al., 2024b; Zheng et al., 2024; Chen et al., 2024; Qin et al., 2025). These systems measure inference behavior on serving engines or traces; our synthetic evaluation does not claim comparable latency or throughput. For foundations, single-machine scheduling surveys and complexity results provide context for release-date and completion-time objectives (Smith, 1956; Graham et al., 1979; Lenstra et al., 1977; Lawler et al., 1993; Goemans et al., 2002; Brucker, 2007). Dynamic storage allocation and bin packing study time-varying resource occupancy and fragmentation (Coffman et al., 1983; Garey & Johnson, 1979; Ivković & Lloyd, 1998; Buchsbaum et al., 2004; Murthy & Bhattacharyya, 1999; Mehta & DeWitt, 1993). They motivate our resource constraint but differ in objective and model details; this paper does not claim new results for those problems."),
P("2.3 Hardness with decode duration greater than one","H2x"),
P("Theorem. The total-flow-time decision problem is strongly NP-hard even when p_i=1, d_i>=2 for every request, and B=1. Proof sketch. Start from the strongly NP-hard single-machine problem 1|r_j|sum C_j, which remains strongly NP-hard with unit weights (Lenstra et al., 1977; Goemans et al., 2002). Since sum r_j is constant, minimizing sum(C_j-r_j) is equivalent. For each job j with processing q_j and release r_j, create a request with p_i=1, d_i=2q_j, and a_i=2r_j; set B=1 and M=2 max_j q_j. Every request fits alone, and B=1 makes memory nonbinding. Doubling source times doubles total flow. Conversely, an optimal target schedule can be left-justified; starts are even releases or even completions, and halving gives a source schedule. A source threshold K on sum C_j maps to 2(K-sum_j r_j). This proves hardness in a growing-decode regime, but inherits release-date single-machine hardness rather than isolating the growing-memory constraint."),
P("The d_i=1 reduction in the project draft separately gives the memory-packing hardness case. These reductions identify two distinct restrictions in the general problem; neither establishes that the time-varying memory constraint alone is strongly hard when B is unlimited and all decode lengths exceed one."),P("3. Methods","H1x"),P("3.1 Algorithms and feasibility","H2x"),
P("All policies use the same deterministic priority order and earliest-feasible placement objective. FCFS orders by arrival then ID; SDF orders by decode duration, arrival, and ID; MAGLS (memory-aware greedy list scheduling) orders by memory-time area A_i=p_i d_i+d_i(d_i-1)/2, arrival, and ID. The area is the sum of a request's memory over its run. E-MAGLS (event-driven MAGLS) keeps this ranking but jumps over contiguous forbidden start intervals: at a violating iteration t, the memory or batch constraint identifies an interval of starts that cannot fit, and the search resumes after that interval. This preserves earliest-fit behavior. A parity check found identical MAGLS/E-MAGLS schedules on 100 seeded instances with and without arrivals and finite B."),
P("The portfolio computes FCFS, SDF, MAGLS, and area-per-wait rankings, retains the lowest-flow feasible schedule, then tests adjacent pair swaps once and keeps the best strict improvement. Since every candidate placement checks the complete run window and the checker independently recomputes memory and activity, feasibility is enforced by construction and rechecked after scheduling. This is a feasibility property of the implementation, not an approximation ratio."),schedule_diagram(),P("Figure 1. Scheduling pipeline and full-window feasibility check.","CaptionX"),
P("3.2 Experimental design","H2x"),P("The standard-library Python harness uses fixed seeds and generates p_i from a clipped log-normal distribution and d_i from a second clipped log-normal distribution. Each of 10 seeds is run at n in {8,16,32,64}; M is set from the maximum individual footprint and 42% of aggregate prompt footprint; B is unlimited. This yields 40 offline workloads x five policies = 200 schedules. A second set contains 10 workloads of 16 requests, nonzero exponentially sampled arrivals, and B=4, adding 50 schedules. Every schedule is checked independently. Reported runtime is wall-clock Python runtime on the same host; no GPU or LLM is invoked. The online set is a small feasibility/behavior check, not a full online benchmark."),
P("Metrics are total flow time, mean per-request flow, mean over-instance 95th-percentile flow, utilization defined as summed memory profile divided by M times the inclusive makespan horizon, and runtime. The sparse time-indexed MILP uses SciPy's HiGHS-backed solver. Start domains are safely bounded by a feasible MAGLS objective; every schedule is checked independently. Ten six-request cases are also solved by exhaustive branch-and-bound, and MILP/exhaustive optima agree exactly. A separate scaling run tests five seeded workloads each at n=30, 40, and 50 with a 15-second solver limit; unfinished runs report the solver's incumbent, lower bound, and gap rather than being labelled optimal.")]
story += [P("4. Results","H1x"),P("4.1 Offline workloads","H2x")]
tab=[["Policy","Flow","vs FCFS","vs SDF","P95 flow","Utilization","Runtime (ms)"]]
for m in offline:
    val=f(m,"total_flow"); fc=100*(1-val/f("FCFS","total_flow")); sd=100*(1-val/f("SDF","total_flow"))
    tab.append([m,f"{val:.1f}",f"{fc:+.1f}%",f"{sd:+.1f}%",f"{f(m,'p95_flow'):.1f}",f"{100*f(m,'memory_utilization'):.1f}%",f"{1000*f(m,'runtime_s'):.2f}"])
story += [make_table(tab,[83,49,54,54,56,65,70]),P("Table 1. Means over 10 offline instances at n=64. Percentage differences are computed from mean total flow; negative values indicate improvement over the named baseline.","CaptionX"),chart(),P("Figure 2. Mean total flow time on offline synthetic workloads (10 seeds per size). Lower is better.","CaptionX"),
P(f"At n=64, FCFS averages {f('FCFS','total_flow'):.1f} flow units and SDF {f('SDF','total_flow'):.1f}. MAGLS averages {f('MAGLS','total_flow'):.1f}, a {reduction('FCFS','MAGLS'):.1f}% reduction from FCFS and {reduction('SDF','MAGLS'):.1f}% from SDF. Portfolio plus local search averages {f('Portfolio+LS','total_flow'):.1f}, improving by {reduction('FCFS','Portfolio+LS'):.1f}% and {reduction('SDF','Portfolio+LS'):.1f}%. All methods were feasible on all 40 offline instances. The portfolio gains only {f('MAGLS','total_flow')-f('Portfolio+LS','total_flow'):.1f} additional flow units over MAGLS on average at n=64, while requiring {f('Portfolio+LS','runtime_s')/f('MAGLS','runtime_s'):.0f} times as much runtime."),
P(f"The tail result differs from the sum objective: the n=64 mean instance-level P95 is {f('FCFS','p95_flow'):.1f} for FCFS, {f('MAGLS','p95_flow'):.1f} for MAGLS, and {f('Portfolio+LS','p95_flow'):.1f} for the portfolio. MAGLS also has lower memory utilization than FCFS ({100*f('MAGLS','memory_utilization'):.1f}% vs {100*f('FCFS','memory_utilization'):.1f}%), so the current objective does not reward high utilization directly. This indicates an objective tradeoff rather than universal dominance."),
P("4.2 Exact tiny-instance comparison","H2x")]
gap_data=[["Policy","Mean gap to optimum","Optimal schedules"]]
for method in ("FCFS","SDF","MAGLS","Portfolio+LS"):
    subset=[r for r in exact_rows if r["method"]==method]
    gap_data.append([method,f"{sum(float(r['relative_gap_pct']) for r in subset)/len(subset):.2f}%",f"{sum(float(r['relative_gap_pct'])==0 for r in subset)}/10"])
story += [make_table(gap_data,[120,155,130]),P("Table 2. Heuristic gaps to the proven time-indexed MILP optimum; 10 synthetic instances with six requests each, with each optimum cross-checked by exhaustive branch-and-bound.","CaptionX"),
P("The MILP and exhaustive search agreed exactly on all 10 optima. MAGLS is within 2.60% of the optimum on average in this small set, while the portfolio is within 1.36% and matches the optimum on eight of 10 cases. The exhaustive check provides an independent validation of the time-indexed model for these instances; it does not scale to the larger workloads."),
P("4.3 Nonzero arrivals and finite batch cap","H2x")]
tab2=[["Policy","Total flow","Mean flow","P95 flow","Utilization","Runtime (ms)"]]
for m in online:tab2.append([m,f"{f(m,'total_flow',16,'online_B4'):.1f}",f"{f(m,'mean_flow',16,'online_B4'):.2f}",f"{f(m,'p95_flow',16,'online_B4'):.1f}",f"{100*f(m,'memory_utilization',16,'online_B4'):.1f}%",f"{1000*f(m,'runtime_s',16,'online_B4'):.2f}"])
story += [make_table(tab2,[92,72,67,66,82,72]),P("Table 3. Means over 10 synthetic arrival workloads (n=16, B=4). Every returned schedule passed the checker.","CaptionX"),
P(f"In the finite-B set, the portfolio averages {f('Portfolio+LS','total_flow',16,'online_B4'):.1f} total flow versus {f('FCFS','total_flow',16,'online_B4'):.1f} for FCFS and {f('MAGLS','total_flow',16,'online_B4'):.1f} for MAGLS. Its average P95 is {f('Portfolio+LS','p95_flow',16,'online_B4'):.1f}; FCFS is {f('FCFS','p95_flow',16,'online_B4'):.1f}. Across all 50 returned schedules in this set, all were feasible. Since the workload sample is small and synthetic, differences are descriptive; no statistical significance claim is made.")]
story += [P("4.4 ILP scaling","H2x")]
scale_table=[["Requests","Proven / 5","Mean solve (s)","Max MIP gap","MAGLS gap*","Portfolio gap*"]]
for n in (30,40,50):
    subset=[r for r in scale_rows if int(r["n"])==n and r["method"]=="FCFS"]
    methods_at_n=[r for r in scale_rows if int(r["n"])==n]
    avgtime=sum(float(r["ilp_runtime_s"]) for r in subset)/len(subset)
    maxgap=100*max(float(r["ilp_gap"] or 0) for r in subset)
    magls=sum(float(r["gap_to_bound_pct"]) for r in methods_at_n if r["method"]=="MAGLS")/len(subset)
    port=sum(float(r["gap_to_bound_pct"]) for r in methods_at_n if r["method"]=="Portfolio+LS")/len(subset)
    proven=sum(r["ilp_proven"]=="True" for r in subset)
    scale_table.append([str(n),f"{proven}/5",f"{avgtime:.2f}",f"{maxgap:.2f}%",f"{magls:.2f}%",f"{port:.2f}%"])
story += [make_table(scale_table,[58,70,85,76,77,88]),P("Table 4. Five seeded offline workloads per size, 15-second solver limit. *Heuristic gaps use the proven optimum when available and the best MILP bound otherwise; for unfinished solves they are lower-bound gaps, not exact optimality gaps.","CaptionX"),
P("The MILP proved all n=30 cases, two of five at n=40, and three of five at n=50. The maximum reported MILP gap among unfinished instances was 0.70%. All 15 workloads returned feasible incumbents. Portfolio and MAGLS are close to solver bounds in these instances, but a small gap to a bound does not prove a similarly small gap to the unknown optimum when the MILP has not closed.")]
story += [P("5. Discussion and Conclusions","H1x"),P("5.1 Interpretation and limitations","H2x"),
P("Area ranking improves mean summed flow in the offline synthetic workloads, consistent with preferring requests with smaller cumulative memory footprint. This is not a proof that area is the right ranking for a general instance: the area ignores arrival pressure and can increase the waiting time of some requests. The n=64 P95 comparison confirms that lower aggregate flow does not imply better tail flow. The portfolio/local-search step finds modest additional mean gains but has a much higher runtime; its usefulness depends on whether that gain justifies the added compute."),
P("The evaluation has important scope limits. First, the generated distribution is not a trace collected from vLLM, ShareGPT, or another serving system. Second, abstract memory units and unit-length iterations do not capture bytes per token, model-layer KV size, batch-dependent decode time, prefill cost, or cache-block fragmentation. Third, decode lengths are known, and jobs never preempt. Fourth, E-MAGLS uses direct scans rather than a segment tree and is 1.74 times slower than MAGLS at n=64; no speed-up is demonstrated. Fifth, only five workloads per larger size were tested; some MILPs timed out with small residual bounds, and exhaustive optimum checks cover six requests only. The algorithms from the supplied base paper were not implemented. The d_i>=2 hardness reduction uses B=1 and leaves memory nonbinding, so hardness specifically due to growing memory with an unlimited batch remains open."),
P("A production-relevant follow-up should calibrate iteration time and cache demand from a real serving engine, compare the base-paper algorithms, include preemption or chunked prefill, vary decode-length prediction error, and evaluate serving traces with a finite batch cap. E-MAGLS would need a segment tree or another accelerated fit data structure before a speedup can be claimed. A theoretical extension should isolate hardness due specifically to growing memory with unlimited B and d_i>1; the present proof does not do so."),
P("5.2 Conclusion","H2x"),P("This project implemented a common feasibility-checked scheduler and compared FCFS, SDF, MAGLS, event-jump E-MAGLS, and a ranking portfolio with local search. On 40 offline synthetic instances, all schedules were feasible, and MAGLS reduced mean total flow by 20.4% versus FCFS at n=64, while the portfolio achieved a 20.6% reduction at substantially higher runtime. The portfolio was 1.36% above proven six-request MILP optima on average. At n=30, 40, and 50, the time-limited MILP proved 5/5, 2/5, and 3/5 instances. E-MAGLS preserved MAGLS schedules but did not improve runtime. The portfolio's P95 was worse than FCFS. Results support memory-time ranking on these generated workloads, not production latency or universal improvement. Evaluation on serving traces and comparison with the base-paper algorithms remain necessary."),P("Acknowledgments","H2x"),P("We thank Dr. Aakash Yadav for feedback on the proposed project and manuscript. The authors are the student team listed on the title page.")]
story += [P("References","H1x"),
P("Agrawal, A., Kedia, N., Panwar, A., Mohan, J., Kwatra, N., Gulavani, B. S., Tumanov, A., & Ramjee, R. (2024). Taming throughput-latency tradeoff in LLM inference with Sarathi-Serve. Proceedings of the 18th USENIX Symposium on Operating Systems Design and Implementation.","RefX"),
P("Garey, M. R., & Johnson, D. S. (1979). Computers and intractability: A guide to the theory of NP-completeness. W. H. Freeman.","RefX"),
P("Goemans, M. X., Queyranne, M., Schulz, A. S., Skutella, M., & Wang, Y. (2002). Single-machine scheduling with release dates. SIAM Journal on Discrete Mathematics, 15(2), 165-192. https://doi.org/10.1137/S089548019936223X","RefX"),
P("Kwon, W., Li, Z., Zhuang, S., Sheng, Y., Zheng, L., Yu, C. H., Gonzalez, J., Zhang, H., & Stoica, I. (2023). Efficient memory management for large language model serving with PagedAttention. Proceedings of the 29th Symposium on Operating Systems Principles. https://doi.org/10.1145/3600006.3613165","RefX"),
P("Lenstra, J. K., Rinnooy Kan, A. H. G., & Brucker, P. (1977). Complexity of machine scheduling problems. Annals of Discrete Mathematics, 1, 343-362.","RefX"),
P("Lawler, E. L., Lenstra, J. K., Rinnooy Kan, A. H. G., & Shmoys, D. B. (1993). Sequencing and scheduling: Algorithms and complexity. In S. C. Graves, A. H. G. Rinnooy Kan, & P. H. Zipkin (Eds.), Handbooks in Operations Research and Management Science (Vol. 4, pp. 445-522). Elsevier.","RefX"),
P("Wu, B., Zhong, Y., Zhang, Z., Liu, S., Liu, F., Sun, Y., Huang, G., Liu, X., & Jin, X. (2023). Fast distributed inference serving for large language models. arXiv:2305.05920.","RefX"),
P("Yu, G.-I., Jeong, J. S., Kim, G.-W., Kim, S., & Ha, S. (2022). Orca: A distributed serving system for transformer-based generative models. Proceedings of the 16th USENIX Symposium on Operating Systems Design and Implementation, 521-538.","RefX"),
P("Zhong, Y., Liu, S., Chen, J., Hu, J., Zhu, Y., Liu, X., Jin, X., & Zhang, H. (2024). DistServe: Disaggregating prefill and decoding for goodput-optimized LLM serving. Proceedings of the 18th USENIX Symposium on Operating Systems Design and Implementation, 193-210.","RefX"),
P("Wang, M., Ye, Y., & Zhou, Z. (2025). LLM Serving Optimization with Variable Prefill and Decode Lengths. arXiv:2508.06133. https://arxiv.org/abs/2508.06133","RefX"),
P("Baker, B. S., Brown, D. J., & Katseff, H. P. (1985). A 5/4 algorithm for two-dimensional packing. Journal of Algorithms, 6(4), 596-608.","RefX"),
P("Brucker, P. (2007). Scheduling algorithms (5th ed.). Springer.","RefX"),
P("Coffman, E. G., Garey, M. R., & Johnson, D. S. (1983). Approximation algorithms for bin packing: A survey. In D. S. Hochbaum (Ed.), Approximation Algorithms for NP-hard Problems. PWS.","RefX"),
P("Conway, R. W., Maxwell, W. L., & Miller, L. W. (1967). Theory of scheduling. Addison-Wesley.","RefX"),
P("Graham, R. L., Lawler, E. L., Lenstra, J. K., & Rinnooy Kan, A. H. G. (1979). Optimization and approximation in deterministic sequencing and scheduling: A survey. Annals of Discrete Mathematics, 5, 287-326.","RefX"),
P("Ivković, Z., & Lloyd, E. L. (1998). Fully dynamic algorithms for bin packing: Being (mostly) myopic helps. SIAM Journal on Computing, 28(2), 574-611.","RefX"),
P("Mehta, A., & DeWitt, D. J. (1993). Dynamic memory allocation for multiple-query workloads. Proceedings of the 19th International Conference on Very Large Data Bases, 354-367.","RefX"),
P("Moore, J. M. (1968). An n job, one machine sequencing algorithm for minimizing the number of late jobs. Management Science, 15(1), 102-109.","RefX"),
P("Murthy, P. K., & Bhattacharyya, S. S. (1999). Approximation algorithms and heuristics for the dynamic storage allocation problem. UMIACS-TR-99-31, University of Maryland.","RefX"),
P("Patel, P., Choukse, E., Zhang, C., Shah, A., Goiri, Í., Maleki, S., & Bianchini, R. (2024). Splitwise: Efficient generative LLM inference using phase splitting. ISCA.","RefX"),
P("Qin, R., et al. (2025). Mooncake: Trading more storage for less computation: A KVCache-centric architecture for serving LLM chatbot. FAST.","RefX"),
P("Robson, J. M. (1981). Worst case analysis of memory allocation strategies. Proceedings of the 2nd Annual ACM Symposium on Theory of Computing, 122-130.","RefX"),
P("Srivatsa, V., He, Z., Abhyankar, R., Li, D., & Zhang, Y. (2024). Preble: Efficient distributed prompt scheduling for LLM serving. arXiv:2407.00023.","RefX"),
P("Sun, B., Huang, Z., Zhao, H., Xiao, W., Zhang, X., Li, Y., & Lin, W. (2024). Llumnix: Dynamic scheduling for large language model serving. OSDI.","RefX"),
P("Agrawal, A., et al. (2024). Vidur: A large-scale simulation framework for LLM inference. MLSys.","RefX"),
P("Chen, L., Ye, Z., Wu, Y., Zhuo, D., Ceze, L., & Krishnamurthy, A. (2024). Punica: Multi-tenant LoRA serving. MLSys.","RefX"),
P("Zheng, L., Yin, L., Xie, Z., et al. (2024). SGLang: Efficient execution of structured language model programs. NeurIPS.","RefX"),
P("Wu, B., Zhong, Y., Zhang, Z., Liu, S., Liu, F., Sun, Y., Huang, G., Liu, X., & Jin, X. (2026). FastServe: Iteration-level preemptive scheduling for large language model inference. NSDI.","RefX"),
P("Smith, W. E. (1956). Various optimizers for single-stage production. Naval Research Logistics Quarterly, 3(1-2), 59-66.","RefX"),
P("Software and reproducibility","H2x"),P("Code, generated workloads, per-instance measurements, and summary tables are included in the repository. From its root run <font name='Courier'>python experiments/run_synthetic_experiments.py</font>, <font name='Courier'>python experiments/run_exact_small.py</font>, and <font name='Courier'>python experiments/run_ilp_scaling.py</font>. The team's original sample-schedule evaluator remains available as <font name='Courier'>python experiments/run_experiments.py</font>. The tested environment was Python 3.13.5 on Windows; the MILP uses SciPy's HiGHS interface (<font name='Courier'>python -m pip install scipy</font>), and manuscript generation uses ReportLab. Rebuild the PDF with <font name='Courier'>python paper/build_manuscript.py</font>. The paper reads the checked-in experiment CSV files. The references cover LLM serving, scheduling theory, and dynamic storage allocation.")]

PDF.parent.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(PDF),pagesize=letter,rightMargin=.68*inch,leftMargin=.68*inch,topMargin=.58*inch,bottomMargin=.58*inch,title="LLM Inference Request Scheduling under GPU Memory Limits",author="PS-1 Team, RGIPT")
doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer)
print(PDF)
