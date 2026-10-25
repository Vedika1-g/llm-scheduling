"""
Unit tests for the simulator/checker.
Run with: python tests/test_checker.py
"""

import sys
sys.path.insert(0, "src")
from simulator import check_schedule


def test_feasible():
    """The hand-worked example from conventions.md should be feasible."""
    config = {"M": 15, "B": None}
    requests = [
        {"id": 1, "p": 3, "d": 2, "a": 0},
        {"id": 2, "p": 5, "d": 1, "a": 0},
        {"id": 3, "p": 2, "d": 3, "a": 0},
    ]
    schedule = {1: 0, 2: 0, 3: 1}
    result = check_schedule(config, requests, schedule)

    assert result["feasible"] == True
    assert result["total_flow_time"] == 4
    assert result["makespan"] == 3
    assert result["memory_profile"][0] == 8
    print("PASSED: test_feasible")


def test_memory_violation():
    """All 3 requests at time 0 with M=9 should violate memory."""
    config = {"M": 9, "B": None}
    requests = [
        {"id": 1, "p": 3, "d": 2, "a": 0},
        {"id": 2, "p": 5, "d": 1, "a": 0},
        {"id": 3, "p": 2, "d": 3, "a": 0},
    ]
    # All start at 0: memory at t=0 = 3+5+2 = 10 > 9
    schedule = {1: 0, 2: 0, 3: 0}
    result = check_schedule(config, requests, schedule)

    assert result["feasible"] == False
    mem_violations = [v for v in result["violations"] if v["type"] == "memory"]
    assert len(mem_violations) > 0
    print("PASSED: test_memory_violation")


def test_batch_violation():
    """B=1 but two requests overlap should violate batch limit."""
    config = {"M": 100, "B": 1}
    requests = [
        {"id": 1, "p": 3, "d": 2, "a": 0},
        {"id": 2, "p": 5, "d": 1, "a": 0},
    ]
    # Both start at 0: 2 active at t=0 > B=1
    schedule = {1: 0, 2: 0}
    result = check_schedule(config, requests, schedule)

    assert result["feasible"] == False
    batch_violations = [v for v in result["violations"] if v["type"] == "batch"]
    assert len(batch_violations) > 0
    print("PASSED: test_batch_violation")


def test_arrival_violation():
    """Request arrives at time 5 but scheduled at time 2 should violate."""
    config = {"M": 100, "B": None}
    requests = [
        {"id": 1, "p": 3, "d": 2, "a": 5},
    ]
    schedule = {1: 2}
    result = check_schedule(config, requests, schedule)

    assert result["feasible"] == False
    arr_violations = [v for v in result["violations"] if v["type"] == "arrival"]
    assert len(arr_violations) > 0
    print("PASSED: test_arrival_violation")


def test_missing_request():
    """Schedule missing a request should be infeasible."""
    config = {"M": 100, "B": None}
    requests = [
        {"id": 1, "p": 3, "d": 2, "a": 0},
        {"id": 2, "p": 5, "d": 1, "a": 0},
    ]
    schedule = {1: 0}  # missing request 2
    result = check_schedule(config, requests, schedule)

    assert result["feasible"] == False
    missing = [v for v in result["violations"] if v["type"] == "missing"]
    assert len(missing) > 0
    print("PASSED: test_missing_request")


if __name__ == "__main__":
    test_feasible()
    test_memory_violation()
    test_batch_violation()
    test_arrival_violation()
    test_missing_request()
    print("\n=== ALL 5 TESTS PASSED ===")