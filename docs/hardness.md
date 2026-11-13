# Hardness with decode duration greater than one

## Theorem

The total-flow-time decision problem is strongly NP-hard even when every
request has prompt length `p_i = 1`, decode duration `d_i >= 2`, and batch
limit `B = 1`.

## Reduction

Use the strongly NP-hard single-machine problem `1|r_j|sum C_j`: each job j
has positive integer processing time q_j and release date r_j, and the goal is
to minimize the sum of completion times. Strong NP-hardness holds even with
unit job weights (Lenstra, Rinnooy Kan, & Brucker, 1977; Goemans et al., 2002).

For every source job j, make one request i with

- `p_i = 1`,
- `d_i = 2 q_j`,
- `a_i = 2 r_j`.

Set `B = 1` and `M = 2 max_j q_j`. Each request fits alone because its peak
memory is `p_i + d_i - 1 = 2 q_j <= M`. With `B = 1`, no two requests overlap,
so the memory constraint never further restricts the schedule.

Every source schedule maps to the target by doubling each start time. Decode
durations, arrivals, completion times, and flow times all scale by two; hence
the target objective is exactly twice the source total flow time. The source
objective `sum(C_j-r_j)` differs from `sum C_j` only by the constant
`sum r_j`, so it has the same strongly NP-hard optimization problem. For a
source decision threshold K stated on `sum C_j`, the corresponding target
threshold is `2(K - sum_j r_j)`. Conversely, an optimal target schedule can be
left-justified: each job starts at its release date or at the preceding job's
completion. Releases and decode durations are even, so all starts in this
normalized schedule are even. Dividing times by two yields a feasible source
schedule with half the target total flow. Thus an optimum for either instance
determines an optimum for the other.

The construction is polynomial, preserves strong hardness under a constant
factor scaling of the integer data, and has `d_i >= 2` for every request.

## Scope of the result

This establishes hardness in a regime where memory grows during decoding, as
requested. It does not show that the growing-memory constraint itself causes
hardness: with `B = 1`, the reduction inherits the classical single-machine
release-date hardness and memory is nonbinding. The separate `d_i = 1`
3-Partition reduction is the memory-packing result.
