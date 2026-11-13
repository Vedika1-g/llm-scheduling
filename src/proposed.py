"""MAGLS ranking, event-style implementation, and local-search wrapper."""
from __future__ import annotations

from baselines import memory_time_area, schedule_list, portfolio
from simulator import check_schedule


def magls(config: dict, requests: list[dict]) -> dict:
    return schedule_list(config, requests, "MAGLS")


def e_magls(config: dict, requests: list[dict]) -> dict:
    """Offline event-driven MAGLS.

    With known arrivals, the fixed area ranking is computed once and each
    request is placed at its earliest feasible event. This produces the same
    schedule as MAGLS for the offline/all-arrivals-known model, without
    revisiting every idle iteration.
    """
    return schedule_list(config, requests, "MAGLS", event_driven=True)


def improve_by_pair_swaps(config: dict, requests: list[dict], schedule: dict | None = None):
    """Best-improvement local search over pairwise ranking swaps."""
    current = dict(schedule or magls(config, requests))
    score = check_schedule(config, requests, current)["total_flow_time"]
    order = sorted(requests, key=lambda r: (current[r["id"]], r["a"], r["id"]))
    # One best-improvement pass over adjacent inversions keeps runtime
    # predictable for the larger generated workloads.
    best_schedule, best_score = current, score
    from baselines import _first_feasible
    for i in range(len(order) - 1):
        candidate_order = list(order)
        candidate_order[i], candidate_order[i + 1] = candidate_order[i + 1], candidate_order[i]
        candidate = {}
        for r in candidate_order:
            candidate[r["id"]] = _first_feasible(config, requests, candidate, r, r["a"])
        value = check_schedule(config, requests, candidate)["total_flow_time"]
        if value < best_score:
            best_schedule, best_score = candidate, value
    current, score = best_schedule, best_score
    return current, score


def proposed(config: dict, requests: list[dict]):
    _, base = portfolio(config, requests)
    return improve_by_pair_swaps(config, requests, base)
