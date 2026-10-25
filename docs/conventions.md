# PS-1 Time Convention (agreed by Vedika & Sonali)

## Definitions

- Request i has: prompt length p_i, decode duration d_i, arrival time a_i
- A request started at time s is **active** during times: s, s+1, ..., s + d - 1
- Memory at time t = p + (t - s) for each active request
- Completion time C = s + d - 1
- Flow time = C - a = (s + d - 1) - a
- Total flow time (objective) = sum of all flow times

## Constraints

- Arrival: s_i >= a_i (cannot start before arrival)
- Memory: sum of memory of all active requests at time t <= M
- Batch: number of active requests at time t <= B (skip if B is null)

## Starting scope

- Offline: all a_i = 0
- No batch limit: B = null (only memory constraint M applies)
- Extensions (later): nonzero arrivals, finite B

## Hand-worked example

3 requests, M = 15, B = null, all a = 0:

| Request | p | d |
|---------|---|---|
| 1       | 3 | 2 |
| 2       | 5 | 1 |
| 3       | 2 | 3 |

Schedule: req 1 starts at 0, req 2 starts at 0, req 3 starts at 1

| Time | Req 1 mem | Req 2 mem | Req 3 mem | Total |
|------|-----------|-----------|-----------|-------|
| 0    | 3         | 5         | -         | 8     |
| 1    | 4         | done      | 2         | 6     |
| 2    | done      | done      | 3         | 3     |
| 3    | done      | done      | 4         | 4     |

Flow times: Req 1 = 1, Req 2 = 0, Req 3 = 3
Total flow time = 4

## Status


- [ ] Vedika confirmed
- [ ] Sonali confirmed