# Mathematical Formulation

## 1. Problem Definition

We consider a set of LLM inference requests that must be scheduled on a GPU with limited memory.

Each request i has the following parameters:

- p_i: Prompt length (initial memory requirement).
- d_i: Decode duration (number of discrete time steps).
- a_i: Arrival time.
- s_i: Start time (decision variable).
- C_i: Completion time.

The GPU has:

- M: Maximum available GPU memory.
- B: Maximum number of simultaneously active requests. If B is null, there is no batch-size limit.

The objective is to minimize the total flow time of all requests while satisfying arrival-time, GPU-memory, and optional batch-size constraints.

## 2. Assumptions and Scheduling Conventions

1. Time is divided into discrete integer time steps.
2. Each request executes without preemption.
3. Request i is active at times s_i, s_i + 1, ..., s_i + d_i - 1.
4. A request cannot start before its arrival time.
5. Its memory requirement increases linearly during decoding.
6. Memory is released immediately after the final active time step.
7. All requests must be scheduled exactly once.
8. The initial experiment uses a_i = 0 for every request and B = null.
9. Extensions support non-zero arrival times and a finite batch limit.

## 3. Derived Quantities

### Completion Time

The completion time of request i is:

C_i = s_i + d_i - 1

The subtraction of one follows from the convention that a request with duration d_i occupies exactly d_i discrete time steps.

### Flow Time

Flow time measures the time between request arrival and completion:

F_i = C_i - a_i

Therefore:

F_i = s_i + d_i - 1 - a_i

## 4. Decision Variables

We use a time-indexed binary decision variable:

x_(i,t) = 1 if request i starts at time t, and 0 otherwise.

The variable is defined only for feasible start times:

a_i <= t <= H

where H is the maximum start-time horizon.

This representation ensures that each request can select exactly one start time.

## 5. Objective Function

The objective is to minimize the sum of flow times across all requests.

Since the flow time of request i is:

F_i = s_i + d_i - 1 - a_i

and x_(i,t) identifies its selected start time, the objective becomes:

Minimize:

Z = sum_i sum_t (t + d_i - 1 - a_i) * x_(i,t)

This objective encourages requests to complete as early as possible after their arrival.

## 6. Constraints

### 6.1 Exactly One Start Time

Every request must start exactly once:

sum_t x_(i,t) = 1       for every request i

This prevents requests from being omitted or scheduled multiple times.

### 6.2 Arrival-Time Constraint

A request cannot start before its arrival:

s_i >= a_i

This is enforced directly by defining the decision-variable domain only for:

t >= a_i

### 6.3 GPU Memory Constraint

At every time step tau, the total memory consumed by all active requests must not exceed the GPU memory limit M.

A request i that starts at time t is active at time tau if:

t <= tau <= t + d_i - 1

Its memory consumption at time tau is:

p_i + (tau - t)

Therefore, the GPU memory constraint is:

sum_i sum_{t: t <= tau <= t + d_i - 1}
    [p_i + (tau - t)] * x_(i,t) <= M

for every time step tau in the scheduling horizon.

Only start times for which request i is active at time tau are included in the inner summation.

### 6.4 Batch-Size Constraint

When a finite batch limit B is specified, the number of simultaneously active requests cannot exceed B at any time.

At time tau, a request i is active if:

t <= tau <= t + d_i - 1

Therefore, the batch-size constraint is:

sum_i sum_{t: t <= tau <= t + d_i - 1} x_(i,t) <= B
                                                        for every tau

The inner sum includes only start times for which request i is active at time tau.

When B is null, batch-size constraints are not added to the model.

## 7. Complete ILP Model

The complete Integer Linear Programming formulation is:

Minimize:

Z = sum_i sum_{t=a_i}^{H}
    (t + d_i - 1 - a_i) * x_(i,t)

Subject to:

1. Exactly one start time for each request:

   sum_{t=a_i}^{H} x_(i,t) = 1
   for every request i

2. GPU memory constraint:

   sum_i sum_{t: t <= tau <= t + d_i - 1}
       [p_i + (tau - t)] * x_(i,t) <= M

   for every time step tau

3. Optional batch-size constraint:

   sum_i sum_{t: t <= tau <= t + d_i - 1}
       x_(i,t) <= B

   for every time step tau, when B is specified

4. Arrival-time restriction:

   Only start times satisfying t >= a_i are included
   in the decision-variable domain.

5. Binary decision variables:

   x_(i,t) in {0, 1}

   for every request i and allowed start time t.

All start times and time steps are integer-valued.

## 8. Finite Scheduling Horizon

The time-indexed formulation requires a finite upper bound H on possible start times.

The implementation first checks whether every request can execute individually within the memory limit:

p_i + d_i - 1 <= M

It also requires B to be at least one if a batch limit is specified.

When these conditions hold, the implementation constructs a feasible serial schedule by sorting requests by arrival time and scheduling one request at a time.

Let U be the total flow time of this feasible serial schedule:

U = sum_i (s_i + d_i - 1 - a_i)

Since this schedule is feasible, the optimal objective cannot exceed U.

Every request has non-negative flow time. Therefore, the flow time of any individual request in an optimal solution cannot exceed U.

Consequently:

s_i + d_i - 1 - a_i <= U

which gives:

s_i <= a_i + U - d_i + 1

A safe common upper bound is therefore:

H = max_i(a_i) + U

This gives the model a finite start-time domain without excluding an optimal solution.

If an individual request cannot fit in memory even when running alone, or B = 0, the implementation uses a fallback finite horizon. Such an instance is infeasible under the model's constraints.

## 9. Solver and Implementation

The model is implemented in Python using PuLP.

The optimization backend is HiGHS.

The implementation performs the following steps:

1. Loads the workload JSON file.
2. Validates the configuration and request parameters.
3. Calculates the scheduling horizon.
4. Creates binary start-time decision variables.
5. Adds the exactly-one-start constraints.
6. Adds GPU memory constraints.
7. Adds batch-size constraints when B is specified.
8. Minimizes total flow time.
9. Extracts the selected start times.
10. Validates the resulting schedule using the independent simulator.
11. Saves the schedule as a JSON file.

The solver reports its status, runtime, best bound, and relative MIP gap when available.

An Optimal solver status indicates that an optimal solution was found and proven for the constructed model. A feasible incumbent without an optimality proof should not be reported as a proven optimum.

## 10. Validation and Experiments

The ILP implementation has been tested using:

| Experiment | Configuration | Expected behavior |
|---|---|---|
| Sample workload | M = 15, B = null | Feasible schedule |
| Memory test | M = 9, B = null | Respect memory limit |
| Batch test | M = 100, B = 1 | At most one active request |
| Arrival test | M = 100, B = null | Respect non-zero arrival time |

The generated schedules are checked independently using the existing simulator.

The existing checker test suite also covers:

- Feasible schedules.
- GPU memory violations.
- Batch-size violations.
- Arrival-time violations.
- Missing requests.

## 11. Limitations

1. The model uses discrete time steps.
2. Requests are non-preemptive.
3. Memory usage is represented by a linear increase during decoding.
4. The model assumes that prompt length and decode duration are known in advance.
5. The formulation does not explicitly model GPU computation time, throughput, or communication overhead.
6. The time-indexed ILP can become computationally expensive as the number of requests and scheduling horizon increase.
7. The formulation minimizes total flow time; it does not directly optimize throughput, energy consumption, or fairness.

## 12. Complexity Considerations

Let n be the number of requests and H the maximum start-time horizon.

The model creates at most:

O(nH)

binary decision variables.

It also creates one exactly-one-start constraint per request, along with time-indexed memory constraints and optional batch constraints.

Each start-time variable can contribute to multiple time-indexed resource constraints because a request remains active for multiple time steps.

Consequently, the model size and solving time can grow substantially with the number of requests, the scheduling horizon, and the request durations.

The actual optimization complexity depends on the instance and the MILP solver.
