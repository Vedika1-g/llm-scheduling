
import argparse
import json
import math
import time
from pathlib import Path

import pulp

from simulator import load_workload, check_schedule, print_result


def validate_input(config, requests):
    """Validate workload configuration and request fields."""

    if not isinstance(config, dict):
        raise ValueError("Workload config must be a dictionary.")

    if not isinstance(requests, list) or not requests:
        raise ValueError("Workload must contain at least one request.")

    M = config.get("M")
    B = config.get("B")

    if isinstance(M, bool) or not isinstance(M, int) or M <= 0:
        raise ValueError("M must be a positive integer.")

    if B is not None:
        if isinstance(B, bool) or not isinstance(B, int) or B < 0:
            raise ValueError("B must be None or a non-negative integer.")

    seen_ids = set()

    for r in requests:
        if not isinstance(r, dict):
            raise ValueError("Every request must be a dictionary.")

        for field in ("id", "p", "d", "a"):
            if field not in r:
                raise ValueError(f"Request is missing field: {field}")

        rid = r["id"]

        try:
            if rid in seen_ids:
                raise ValueError(f"Duplicate request ID: {rid}")
            seen_ids.add(rid)
        except TypeError:
            raise ValueError("Request IDs must be hashable.")

        for field in ("p", "d", "a"):
            value = r[field]

            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"Request {rid}: {field} must be an integer."
                )

        if r["p"] <= 0:
            raise ValueError(f"Request {rid}: p must be positive.")

        if r["d"] <= 0:
            raise ValueError(f"Request {rid}: d must be positive.")

        if r["a"] < 0:
            raise ValueError(f"Request {rid}: a cannot be negative.")


def calculate_horizon(config, requests):
    """
    Calculate a finite scheduling horizon.

    If serial execution is feasible, its total flow time provides
    an upper bound on the optimal objective.

    Since every request has non-negative flow time, no request in
    an optimal solution needs a start time beyond max(arrival) + U,
    where U is the serial schedule's total flow time.

    If serial execution is impossible because a request cannot fit
    in memory or B = 0, the fallback horizon is sufficient for the
    model to establish infeasibility.
    """

    M = config["M"]
    B = config["B"]

    max_arrival = max(r["a"] for r in requests)
    total_duration = sum(r["d"] for r in requests)

    serial_feasible = (
        (B is None or B >= 1)
        and all(r["p"] + r["d"] - 1 <= M for r in requests)
    )

    if serial_feasible:
        current_time = 0
        upper_bound = 0

        # Process requests in arrival-time order.
        for r in sorted(requests, key=lambda item: item["a"]):
            start = max(current_time, r["a"])

            completion = start + r["d"] - 1
            flow_time = completion - r["a"]

            upper_bound += flow_time
            current_time = start + r["d"]

        return max_arrival + upper_bound

    return max_arrival + total_duration - 1


def solve_workload(
    workload_path,
    output_path=None,
    time_limit=None,
    relative_gap=None
):
    """Build, solve, and independently validate the scheduling ILP."""

    config, requests = load_workload(workload_path)

    validate_input(config, requests)

    M = config["M"]
    B = config["B"]

    n = len(requests)
    horizon = calculate_horizon(config, requests)
    max_duration = max(r["d"] for r in requests)

    print("\n========== WORKLOAD ==========")
    print("Number of requests:", n)
    print("GPU memory capacity M:", M)
    print("Batch limit B:", B)
    print("Scheduling horizon: 0 to", horizon)

    # ---------------------------------------------------------
    # 1. Create the optimization problem
    # ---------------------------------------------------------

    model = pulp.LpProblem(
        "LLM_Inference_Scheduling",
        pulp.LpMinimize
    )

    # x[(request_id, t)] = 1 if request starts at time t.
    # Otherwise, it is 0.

    x = {}

    for index, r in enumerate(requests):
        rid = r["id"]

        for t in range(r["a"], horizon + 1):
            x[(rid, t)] = pulp.LpVariable(
                f"x_{index}_{t}",
                cat=pulp.LpBinary
            )

    # ---------------------------------------------------------
    # 2. Objective: Minimize total flow time
    # ---------------------------------------------------------

    model += pulp.lpSum(
        (
            t + r["d"] - 1 - r["a"]
        ) * x[(r["id"], t)]

        for r in requests
        for t in range(r["a"], horizon + 1)
    ), "Total_Flow_Time"

    # ---------------------------------------------------------
    # 3. Each request must start exactly once
    # ---------------------------------------------------------

    for r in requests:
        rid = r["id"]

        model += (
            pulp.lpSum(
                x[(rid, t)]
                for t in range(r["a"], horizon + 1)
            ) == 1,
            f"One_Start_{rid}"
        )

    # ---------------------------------------------------------
    # 4. GPU memory constraints
    # ---------------------------------------------------------

    # A request starting at t is active at time tau when:
    #
    # t <= tau <= t + d_i - 1
    #
    # Its memory usage at tau is:
    #
    # p_i + (tau - t)

    last_time = horizon + max_duration - 1

    for tau in range(last_time + 1):
        memory_terms = []

        for r in requests:
            rid = r["id"]
            p = r["p"]
            d = r["d"]

            earliest_start = max(r["a"], tau - d + 1)
            latest_start = min(tau, horizon)

            for t in range(earliest_start, latest_start + 1):
                memory_terms.append(
                    (p + tau - t) * x[(rid, t)]
                )

        if memory_terms:
            model += (
                pulp.lpSum(memory_terms) <= M,
                f"Memory_At_Time_{tau}"
            )

    # ---------------------------------------------------------
    # 5. Optional batch-size constraints
    # ---------------------------------------------------------

    if B is not None:

        for tau in range(last_time + 1):
            active_terms = []

            for r in requests:
                rid = r["id"]
                d = r["d"]

                earliest_start = max(r["a"], tau - d + 1)
                latest_start = min(tau, horizon)

                for t in range(earliest_start, latest_start + 1):
                    active_terms.append(x[(rid, t)])

            if active_terms:
                model += (
                    pulp.lpSum(active_terms) <= B,
                    f"Batch_At_Time_{tau}"
                )

    print("\n========== MODEL SIZE ==========")
    print("Number of variables:", len(model.variables()))
    print("Number of constraints:", len(model.constraints))

    # ---------------------------------------------------------
    # 6. Configure and run HiGHS
    # ---------------------------------------------------------

    solver_options = {
        "msg": False
    }

    if time_limit is not None:
        if time_limit <= 0:
            raise ValueError("Time limit must be positive.")

        solver_options["timeLimit"] = time_limit

    if relative_gap is not None:
        if not 0 <= relative_gap < 1:
            raise ValueError("Relative gap must be in [0, 1).")

        solver_options["gapRel"] = relative_gap

    solver = pulp.HiGHS(**solver_options)

    print("\nSolving with HiGHS...")

    start_clock = time.perf_counter()

    model.solve(solver)

    runtime = time.perf_counter() - start_clock

    # Problem status and solution status are different.
    status = pulp.LpStatus[model.status]
    solution_status = pulp.LpSolution[model.sol_status]

    optimality_proven = (
        model.sol_status == pulp.LpSolutionOptimal
    )

    print("\n========== SOLVER RESULT ==========")
    print("Problem status:", status)
    print("Solution status:", solution_status)
    print("Optimality proven:", optimality_proven)
    print(f"Runtime: {runtime:.4f} seconds")

    # ---------------------------------------------------------
    # 7. Extract HiGHS best bound and MIP gap
    # ---------------------------------------------------------

    best_bound = None
    mip_gap = None

    try:
        info = model.solverModel.getInfo()

        best_bound = getattr(info, "mip_dual_bound", None)
        mip_gap = getattr(info, "mip_gap", None)

        if best_bound is not None and not math.isfinite(best_bound):
            best_bound = None

        if mip_gap is not None and not math.isfinite(mip_gap):
            mip_gap = None

    except (AttributeError, TypeError, ValueError):
        pass

    print("Best bound:", best_bound)
    print("Relative MIP gap:", mip_gap)

    # ---------------------------------------------------------
    # 8. Check whether a usable incumbent exists
    # ---------------------------------------------------------

    has_incumbent = (
        model.sol_status in (
            pulp.LpSolutionOptimal,
            pulp.LpSolutionIntegerFeasible
        )
        and all(
            variable.varValue is not None
            for variable in x.values()
        )
    )

    if not has_incumbent:
        print("\nNo feasible schedule was returned by the solver.")

        return {
            "status": status,
            "solution_status": solution_status,
            "optimality_proven": False,
            "objective": None,
            "runtime": runtime,
            "best_bound": best_bound,
            "mip_gap": mip_gap
        }

    if optimality_proven:
        print("\nThe solver proved that the solution is optimal.")
    else:
        print(
            "\nA feasible incumbent was found, "
            "but optimality has NOT been proven."
        )

    # ---------------------------------------------------------
    # 9. Extract the selected start time for every request
    # ---------------------------------------------------------

    schedule = {}

    for r in requests:
        rid = r["id"]

        selected_times = [
            t
            for t in range(r["a"], horizon + 1)
            if x[(rid, t)].varValue is not None
            and x[(rid, t)].varValue > 0.5
        ]

        if len(selected_times) != 1:
            print(
                f"Could not extract exactly one start "
                f"for request {rid}."
            )

            return {
                "status": status,
                "solution_status": solution_status,
                "optimality_proven": optimality_proven,
                "objective": None,
                "runtime": runtime,
                "best_bound": best_bound,
                "mip_gap": mip_gap
            }

        schedule[rid] = selected_times[0]

    objective = pulp.value(model.objective)

    if objective is None:
        raise RuntimeError("Solver returned no objective value.")

    # ---------------------------------------------------------
    # 10. Display the schedule
    # ---------------------------------------------------------

    print("\n========== SCHEDULE ==========")
    print(schedule)
    print("ILP objective:", objective)

    # ---------------------------------------------------------
    # 11. Independently validate using the simulator
    # ---------------------------------------------------------

    print("\n========== INDEPENDENT CHECKER ==========")

    result = check_schedule(config, requests, schedule)

    print_result(result)

    if not result["feasible"]:
        raise RuntimeError(
            "ILP output failed the independent simulator checker."
        )

    if abs(result["total_flow_time"] - objective) > 1e-5:
        raise RuntimeError(
            "ILP objective and simulator objective do not match."
        )

    print("\nIndependent validation: PASSED")

    # ---------------------------------------------------------
    # 12. Save the schedule
    # ---------------------------------------------------------

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with output_path.open("w") as f:
            json.dump(
                {str(k): v for k, v in schedule.items()},
                f,
                indent=4
            )

        print("Schedule saved to:", output_path)

    # ---------------------------------------------------------
    # 13. Return experiment results
    # ---------------------------------------------------------

    return {
        "status": status,
        "solution_status": solution_status,
        "optimality_proven": optimality_proven,
        "objective": objective,
        "schedule": schedule,
        "runtime": runtime,
        "best_bound": best_bound,
        "mip_gap": mip_gap,
        "checker_result": result
    }


def main():

    parser = argparse.ArgumentParser(
        description="Solve LLM inference scheduling using ILP."
    )

    parser.add_argument(
        "--workload",
        type=str,
        default="data/sample_workload.json",
        help="Path to workload JSON file."
    )

    parser.add_argument(
        "--output",
        type=str,
        default="experiments/ilp_schedule.json",
        help="Path where the generated schedule will be saved."
    )

    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        help="Optional solver time limit in seconds."
    )

    parser.add_argument(
        "--gap",
        type=float,
        default=None,
        help="Optional relative MIP gap, e.g. 0.01."
    )

    args = parser.parse_args()

    solve_workload(
        workload_path=args.workload,
        output_path=args.output,
        time_limit=args.time_limit,
        relative_gap=args.gap
    )


if __name__ == "__main__":
    main()
