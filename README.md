# LLM Inference Request Scheduling under GPU Memory Limits

Advanced Algorithms semester project (PS-1), RGIPT 2026-27

## Problem

Schedule LLM inference requests on a GPU to minimize total flow time, subject to memory capacity (M) and optional batch limit (B).

## Team Roles

| Member | Role | Files |
|--------|------|-------|
| Vedika | Simulator and checker | src/simulator.py, tests/test_checker.py |
| Sonali | ILP/MILP formulation | src/scipy_ilp.py, docs/model.md |
| Abhishri | Baselines and proposed algorithm | src/baselines.py, src/proposed.py |
| Yasashwitha | Experiments and plots | experiments/ |
| Manya | Literature, hardness, and paper | paper/, docs/hardness.md |

## Setup

1. Clone the repo:

git clone https://github.com/Vedika1-g/llm-scheduling.git
cd llm-scheduling

2. Requires Python 3.x (no extra packages for simulator)

3. Run the built-in test:

python src/simulator.py

4. Run all unit tests:

python tests/test_checker.py

5. Run the seeded synthetic comparison (FCFS, SDF, MAGLS, E-MAGLS, portfolio + local search):

python experiments/run_synthetic_experiments.py

python experiments/run_exact_small.py

python experiments/run_ilp_scaling.py

This writes per-instance workloads and metrics to `experiments/results/`, including
offline cases with 8, 16, 32, and 64 requests and a small nonzero-arrival, finite-batch
set. The exact-small script verifies 10 six-request MILP optima against exhaustive
search. Every returned schedule is independently checked by `src/simulator.py`.

The team's existing sample-schedule evaluator remains available as
`python experiments/run_experiments.py`; it evaluates the four example schedules in
`experiments/` and writes `experiments/results.csv`.

6. Solve a small workload with the time-indexed MILP (requires SciPy):

python -m pip install scipy
python src/scipy_ilp.py --workload data/sample_workload.json --output experiments/ilp_schedule.json

7. Rebuild the paper PDF (requires ReportLab; the bundled Codex Python runtime was used
for the delivered build):

python -m pip install reportlab
python paper/build_manuscript.py

The sparse time-indexed MILP uses SciPy's HiGHS-backed `milp` interface and checks each
returned schedule with the independent simulator. `experiments/run_exact_small.py` also
compares solver-proven MILP optima with exhaustive search on 10 tiny instances.

The result is written to `output/pdf/llm_inference_request_scheduling.pdf`. The paper
build reads the generated `experiments/results/summary.csv`, so rerun the experiments
after changing algorithms or workloads.

## Workload Format (JSON)

Each request has id, p (prompt length), d (decode duration), a (arrival time).
Config has M (memory limit) and B (batch limit, null means no limit).

Example file (data/sample_workload.json):

{"config": {"M": 15, "B": null}, "requests": [{"id": 1, "p": 3, "d": 2, "a": 0}, {"id": 2, "p": 5, "d": 1, "a": 0}, {"id": 3, "p": 2, "d": 3, "a": 0}]}

## Schedule Format (JSON)

Maps request ID to start time:

{"1": 0, "2": 0, "3": 1}

## Run With Files

python src/simulator.py data/sample_workload.json data/sample_schedule.json

## Use In Your Code

Import check_schedule from src/simulator.py:

from simulator import check_schedule
config = {"M": 15, "B": None}
requests = [{"id": 1, "p": 3, "d": 2, "a": 0}]
schedule = {1: 0}
result = check_schedule(config, requests, schedule)

result["feasible"] gives True or False
result["total_flow_time"] gives the objective value
result["violations"] gives list of violations if any

## What The Checker Returns

- feasible: True or False
- violations: list of constraint violations with details
- total_flow_time: the objective (sum of all flow times)
- makespan: latest completion time
- per_request: start, end, flow for each request
- memory_profile: total memory at each time step
- active_profile: number of active requests at each time step

## Time Convention (see docs/conventions.md)

- Request started at time s is active
