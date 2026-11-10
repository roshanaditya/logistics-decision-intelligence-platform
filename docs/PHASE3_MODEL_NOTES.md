# Phase 3 model notes

## Prototype assumptions
- One planning horizon measured in integer minutes.
- Each load occupies one dock for its entire service duration.
- Docks are interchangeable.
- No breaks, maintenance, setup times, or dock eligibility rules yet.
- Due time is the desired completion time.
- Priority 1–5 is mapped to a simple objective weight, not a monetary value.

## Why optional intervals?
For every load/dock pair, an optional interval is controlled by a Boolean assignment variable. Exactly one assignment is selected for each load. `NoOverlap` prevents selected intervals from overlapping on a dock.

## Objective
Minimize `sum(priority_i * (waiting_i + tardiness_i))`.

This is a prototype objective, not a validated business cost function. Stakeholders must validate the relative importance of waiting, lateness, throughput, overtime, and SLA penalties.

## Next improvements
1. Build a First-Come-First-Served baseline and compare KPIs.
2. Add dock eligibility and dock-specific service durations.
3. Add operating shifts, breaks, and maintenance windows.
4. Model multiple warehouse stages where required.
5. Add scenario analysis and solver time-limit / optimality-gap reporting.
6. Persist optimization requests and schedules in PostgreSQL.
