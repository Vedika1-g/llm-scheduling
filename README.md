
### Use in your code

```python
from simulator import check_schedule

config = {"M": 15, "B": None}
requests = [{"id": 1, "p": 3, "d": 2, "a": 0}]
schedule = {1: 0}

result = check_schedule(config, requests, schedule)
print(result["feasible"])          # True or False
print(result["total_flow_time"])   # objective value
print(result["violations"])        # list of violations if any
```

### What the checker returns

- `feasible` — True/False
- `violations` — list of constraint violations with details
- `total_flow_time` — the objective (sum of all flow times)
- `makespan` — latest completion time
- `per_request` — start, end, flow for each request
- `memory_profile` — total memory at each time step
- `active_profile` — number of active requests at each time step

## Time Convention (see docs/conventions.md)

- Request started at time `s` is active during `s, s+1, ..., s+d-1`
- Memory at time `t` = `p + (t - s)`
- Completion = `s + d - 1`
- Flow time = `(s + d - 1) - a`
- **All methods must use this convention**

## Current Scope

- Offline: all arrivals at time 0
- No batch limit (B = null)
- Memory constraint only
- Extensions (later): nonzero arrivals, finite B