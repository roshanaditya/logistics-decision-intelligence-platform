from ortools.sat.python import cp_model
from app.optimization.schemas import LoadRequest, ScheduledLoad, WarehouseOptimizationResponse

def optimize_warehouse_schedule(loads: list[LoadRequest], dock_count: int = 6,
                                horizon_minutes: int = 1440,
                                max_solver_seconds: int = 10) -> WarehouseOptimizationResponse:
    if not loads:
        raise ValueError("At least one load is required.")
    if dock_count < 1:
        raise ValueError("dock_count must be at least 1.")

    for load in loads:
        if load.arrival_minute + load.duration_minutes > horizon_minutes:
            raise ValueError(f"Load {load.load_id} cannot fit within the planning horizon.")
        if load.due_minute > horizon_minutes:
            raise ValueError(f"Load {load.load_id} has due_minute beyond the planning horizon.")

    model = cp_model.CpModel()
    starts, ends, waits, late = {}, {}, {}, {}
    assignments = {}
    dock_intervals = {dock: [] for dock in range(1, dock_count + 1)}

    for i, load in enumerate(loads):
        starts[i] = model.new_int_var(load.arrival_minute,
                                      horizon_minutes - load.duration_minutes, f"start_{i}")
        ends[i] = model.new_int_var(load.arrival_minute + load.duration_minutes,
                                    horizon_minutes, f"end_{i}")
        model.add(ends[i] == starts[i] + load.duration_minutes)

        waits[i] = model.new_int_var(0, horizon_minutes, f"waiting_{i}")
        model.add(waits[i] == starts[i] - load.arrival_minute)
        late[i] = model.new_int_var(0, horizon_minutes, f"tardiness_{i}")
        model.add_max_equality(late[i], [ends[i] - load.due_minute, 0])

        choices = []
        for dock in range(1, dock_count + 1):
            assigned = model.new_bool_var(f"load_{i}_dock_{dock}")
            assignments[i, dock] = assigned
            choices.append(assigned)
            interval = model.new_optional_interval_var(
                starts[i], load.duration_minutes, ends[i], assigned,
                f"interval_load_{i}_dock_{dock}")
            dock_intervals[dock].append(interval)
        model.add_exactly_one(choices)

    for intervals in dock_intervals.values():
        model.add_no_overlap(intervals)

    model.minimize(sum(
        load.priority * (waits[i] + late[i]) for i, load in enumerate(loads)
    ))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_solver_seconds
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    status_name = solver.status_name(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"No feasible schedule found. Solver status: {status_name}")

    schedule = []
    for i, load in enumerate(loads):
        dock = next(d for d in range(1, dock_count + 1)
                    if solver.value(assignments[i, d]))
        start, end = solver.value(starts[i]), solver.value(ends[i])
        schedule.append(ScheduledLoad(
            load_id=load.load_id, dock_id=dock, start_minute=start, end_minute=end,
            waiting_minutes=start - load.arrival_minute,
            tardiness_minutes=max(0, end - load.due_minute), priority=load.priority))

    schedule.sort(key=lambda x: (x.start_minute, x.dock_id))
    return WarehouseOptimizationResponse(
        solver_status=status_name, objective_value=solver.objective_value,
        total_waiting_minutes=sum(x.waiting_minutes for x in schedule),
        total_tardiness_minutes=sum(x.tardiness_minutes for x in schedule),
        schedule=schedule)
