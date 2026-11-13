"""Deterministic list-scheduling policies for the PS-1 discrete-time model."""
from __future__ import annotations

from typing import Callable

from simulator import check_schedule


def memory_time_area(request: dict) -> int:
    p, d = request["p"], request["d"]
    return d * p + d * (d - 1) // 2


def _key(policy: str, request: dict, now: int):
    rid = request["id"]
    if policy == "FCFS":
        return (request["a"], rid)
    if policy == "SDF":
        return (request["d"], request["a"], rid)
    if policy == "MAGLS":
        return (memory_time_area(request), request["a"], rid)
    if policy == "AREA_WAIT":
        # Waiting multiplier is a deterministic aging tie-breaker.
        return (memory_time_area(request) / (1 + now - request["a"]), request["a"], rid)
    raise ValueError(f"Unknown policy: {policy}")


def _first_feasible(config: dict, requests: list[dict], schedule: dict, r: dict, earliest: int) -> int:
    """Find the earliest start whose complete non-preemptive window fits."""
    M, B = config["M"], config.get("B")
    last = max([earliest] + [s + q["d"] for q in requests for s in [schedule.get(q["id"], -q["d"])]] )
    # Any serial schedule is feasible when each request fits alone.
    horizon = max(last + sum(q["d"] for q in requests) + 1,
                  max((q["a"] for q in requests), default=0) + sum(q["d"] for q in requests) + 1)
    for start in range(earliest, horizon + 1):
        good = True
        for t in range(start, start + r["d"]):
            mem, active = r["p"] + t - start, 1
            for q in requests:
                if q["id"] == r["id"] or q["id"] not in schedule:
                    continue
                s = schedule[q["id"]]
                if s <= t < s + q["d"]:
                    mem += q["p"] + t - s
                    active += 1
            if mem > M or (B is not None and active > B):
                good = False
                break
        if good:
            return start
    raise RuntimeError("No feasible start found; check that every request fits alone.")


def _first_feasible_event(config: dict, requests: list[dict], schedule: dict, r: dict, earliest: int) -> int:
    """Find the earliest fit by jumping over forbidden start intervals.

    A capacity violation at iteration t rules out a contiguous interval of
    starts for this request. We jump only past that interval's upper endpoint,
    so no potentially feasible start is skipped.
    """
    M, B = config["M"], config.get("B")
    horizon=max(earliest, max((q["a"] for q in requests),default=0))+sum(q["d"] for q in requests)+1
    start=earliest
    while start<=horizon:
        jumps=[]
        for t in range(start,start+r["d"]):
            other_mem=0;other_active=0
            for q in requests:
                if q["id"]==r["id"] or q["id"] not in schedule:continue
                qs=schedule[q["id"]]
                if qs<=t<qs+q["d"]:
                    other_active+=1;other_mem+=q["p"]+t-qs
            if B is not None and other_active+1>B:
                jumps.append(t+1)
            if other_mem+r["p"]+t-start>M:
                upper=min(t,r["p"]+t+other_mem-M-1)
                jumps.append(upper+1)
        if not jumps:return start
        start=max(start+1,min(jumps))
    raise RuntimeError("No feasible start found; check that every request fits alone.")


def schedule_list(config: dict, requests: list[dict], policy: str = "FCFS", event_driven: bool = False) -> dict:
    """Schedule each request in policy order at its earliest feasible start."""
    schedule = {}
    for r in sorted(requests, key=lambda q: _key(policy, q, q["a"])):
        placer=_first_feasible_event if event_driven else _first_feasible
        schedule[r["id"]] = placer(config, requests, schedule, r, r["a"])
    checked = check_schedule(config, requests, schedule)
    if not checked["feasible"]:
        raise AssertionError(checked["violations"])
    return schedule


def portfolio(config: dict, requests: list[dict]) -> tuple[str, dict]:
    """Return the best feasible schedule among fixed ranking policies."""
    candidates = {name: schedule_list(config, requests, name)
                  for name in ("FCFS", "SDF", "MAGLS", "AREA_WAIT")}
    best = min(candidates, key=lambda name: (check_schedule(config, requests, candidates[name])["total_flow_time"], name))
    return best, candidates[best]
