from app.optimization.scheduler import optimize_warehouse_schedule
from app.optimization.schemas import LoadRequest

def test_every_load_is_scheduled_once():
    loads = [
        LoadRequest(load_id="A", arrival_minute=0, duration_minutes=60, due_minute=100, priority=2),
        LoadRequest(load_id="B", arrival_minute=0, duration_minutes=60, due_minute=100, priority=1),
        LoadRequest(load_id="C", arrival_minute=10, duration_minutes=30, due_minute=100, priority=3),
    ]
    result = optimize_warehouse_schedule(loads, dock_count=2, horizon_minutes=240)
    assert result.solver_status in {"OPTIMAL", "FEASIBLE"}
    assert {x.load_id for x in result.schedule} == {"A", "B", "C"}
    assert len(result.schedule) == 3

def test_same_dock_has_no_overlapping_loads():
    loads = [
        LoadRequest(load_id=x, arrival_minute=0, duration_minutes=60, due_minute=100, priority=1)
        for x in ["A", "B", "C"]
    ]
    result = optimize_warehouse_schedule(loads, dock_count=2, horizon_minutes=240)
    by_dock = {}
    for item in result.schedule:
        by_dock.setdefault(item.dock_id, []).append(item)
    for items in by_dock.values():
        items.sort(key=lambda x: x.start_minute)
        for prev, curr in zip(items, items[1:]):
            assert prev.end_minute <= curr.start_minute

def test_load_never_starts_before_arrival():
    load = LoadRequest(load_id="A", arrival_minute=50, duration_minutes=30, due_minute=100, priority=1)
    result = optimize_warehouse_schedule([load], dock_count=1, horizon_minutes=240)
    assert result.schedule[0].start_minute >= 50
