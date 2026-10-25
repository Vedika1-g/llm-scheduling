"""
LLM Inference Request Scheduling - Simulator & Checker
Author: Vedika (Simulator & Feasibility Checker Lead)

Convention (see docs/conventions.md):
  - Request i started at time s is active during: s, s+1, ..., s+d-1
  - Memory at time t = p + (t - s) for each active request
  - Completion time C = s + d - 1
  - Flow time = C - a = (s + d - 1) - a
"""

import json
import sys


# ---- LOADING ----

def load_workload(filepath):
    """Load workload from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)

    config = data["config"]
    requests = data["requests"]

    # Validate each request
    for r in requests:
        if r["p"] <= 0:
            raise ValueError(f"Request {r['id']}: p must be > 0, got {r['p']}")
        if r["d"] <= 0:
            raise ValueError(f"Request {r['id']}: d must be > 0, got {r['d']}")
        if r["a"] < 0:
            raise ValueError(f"Request {r['id']}: a must be >= 0, got {r['a']}")

    return config, requests


def load_schedule(filepath):
    """Load schedule from a JSON file. Returns dict {request_id: start_time}."""
    with open(filepath, "r") as f:
        schedule = json.load(f)

    # Convert keys to int (JSON keys are strings)
    return {int(k): v for k, v in schedule.items()}


# ---- CHECKER ----

def check_schedule(config, requests, schedule):
    """
    Check if a schedule is feasible and compute all metrics.

    Returns a dict with:
      - feasible (bool)
      - violations (list of dicts)
      - total_flow_time (int)
      - makespan (int)
      - per_request (dict of per-request info)
      - memory_profile (dict time -> total memory)
      - active_profile (dict time -> active count)
    """
    M = config["M"]
    B = config.get("B", None)  # None means no batch limit

    violations = []
    per_request = {}

    # --- Check 1: every request has a start time ---
    for r in requests:
        rid = r["id"]
        if rid not in schedule:
            violations.append({
                "type": "missing",
                "request": rid,
                "message": f"Request {rid} has no start time in schedule"
            })

    if violations:
        return {
            "feasible": False,
            "violations": violations,
            "total_flow_time": None,
            "makespan": None,
            "per_request": {},
            "memory_profile": {},
            "active_profile": {}
        }

    # --- Compute per-request info ---
    for r in requests:
        rid = r["id"]
        s = schedule[rid]
        p = r["p"]
        d = r["d"]
        a = r["a"]

        start = s
        end = s + d - 1          # last active time step
        completion = end          # same as end
        flow = completion - a

        per_request[rid] = {
            "p": p,
            "d": d,
            "a": a,
            "start": start,
            "end": end,
            "completion": completion,
            "flow": flow
        }

    # --- Check 2: arrival constraint ---
    for rid, info in per_request.items():
        if info["start"] < info["a"]:
            violations.append({
                "type": "arrival",
                "request": rid,
                "message": f"Request {rid} starts at {info['start']} "
                           f"but arrives at {info['a']}"
            })

    # --- Find time horizon ---
    max_time = max(info["end"] for info in per_request.values())

    # --- Build memory and active-count profile ---
    memory_profile = {}
    active_profile = {}

    for t in range(0, max_time + 1):
        total_memory = 0
        active_count = 0

        for r in requests:
            rid = r["id"]
            info = per_request[rid]

            # Is this request active at time t?
            if info["start"] <= t <= info["end"]:
                active_count += 1
                mem = info["p"] + (t - info["start"])
                total_memory += mem

        memory_profile[t] = total_memory
        active_profile[t] = active_count

        # --- Check 3: memory constraint ---
        if total_memory > M:
            violations.append({
                "type": "memory",
                "time": t,
                "used": total_memory,
                "limit": M,
                "message": f"Time {t}: memory {total_memory} > limit {M}"
            })

        # --- Check 4: batch constraint ---
        if B is not None and active_count > B:
            violations.append({
                "type": "batch",
                "time": t,
                "count": active_count,
                "limit": B,
                "message": f"Time {t}: {active_count} active > batch limit {B}"
            })

    # --- Compute objectives ---
    total_flow = sum(info["flow"] for info in per_request.values())
    makespan = max(info["completion"] for info in per_request.values())

    return {
        "feasible": len(violations) == 0,
        "violations": violations,
        "total_flow_time": total_flow,
        "makespan": makespan,
        "per_request": per_request,
        "memory_profile": memory_profile,
        "active_profile": active_profile
    }


# ---- DISPLAY ----

def print_result(result):
    """Print the checker result in a readable way."""
    print("=" * 50)
    if result["feasible"]:
        print("RESULT: FEASIBLE")
    else:
        print("RESULT: INFEASIBLE")
        print(f"\nViolations ({len(result['violations'])}):")
        for v in result["violations"]:
            print(f"  - {v['message']}")

    if result["total_flow_time"] is not None:
        print(f"\nTotal flow time: {result['total_flow_time']}")
        print(f"Makespan: {result['makespan']}")

        print("\nPer-request details:")
        print(f"  {'ID':>4} {'p':>4} {'d':>4} {'a':>4} {'start':>6} "
              f"{'end':>5} {'flow':>5}")
        for rid, info in sorted(result["per_request"].items()):
            print(f"  {rid:>4} {info['p']:>4} {info['d']:>4} {info['a']:>4} "
                  f"{info['start']:>6} {info['end']:>5} {info['flow']:>5}")

        print("\nMemory profile:")
        print(f"  {'Time':>5} {'Memory':>7} {'Active':>7}")
        for t in sorted(result["memory_profile"].keys()):
            print(f"  {t:>5} {result['memory_profile'][t]:>7} "
                  f"{result['active_profile'][t]:>7}")

    print("=" * 50)


# ---- MAIN ----

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simulator.py <workload.json> <schedule.json>")
        print("\nRunning built-in test...\n")

        # Built-in test: 3 requests from conventions.md
        config = {"M": 15, "B": None}
        requests = [
            {"id": 1, "p": 3, "d": 2, "a": 0},
            {"id": 2, "p": 5, "d": 1, "a": 0},
            {"id": 3, "p": 2, "d": 3, "a": 0},
        ]
        schedule = {1: 0, 2: 0, 3: 1}

        result = check_schedule(config, requests, schedule)
        print_result(result)

        # Verify against hand-worked example
        assert result["feasible"] == True
        assert result["total_flow_time"] == 4
        assert result["memory_profile"][0] == 8
        assert result["memory_profile"][1] == 6
        assert result["memory_profile"][2] == 3
        assert result["memory_profile"][3] == 4
        print("\nAll hand-worked checks passed!")

    else:
        config, requests = load_workload(sys.argv[1])
        schedule = load_schedule(sys.argv[2])
        result = check_schedule(config, requests, schedule)
        print_result(result)