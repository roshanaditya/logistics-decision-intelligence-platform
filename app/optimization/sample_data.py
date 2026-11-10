from app.optimization.scheduler import optimize_warehouse_schedule
from app.optimization.schemas import LoadRequest

def main():
    # Minute 0 represents the start of the planning horizon (e.g. 08:00).
    loads = [
        LoadRequest(load_id="LOAD-001", arrival_minute=0, duration_minutes=90, due_minute=150, priority=5),
        LoadRequest(load_id="LOAD-002", arrival_minute=10, duration_minutes=60, due_minute=120, priority=3),
        LoadRequest(load_id="LOAD-003", arrival_minute=15, duration_minutes=120, due_minute=210, priority=4),
        LoadRequest(load_id="LOAD-004", arrival_minute=30, duration_minutes=45, due_minute=120, priority=2),
        LoadRequest(load_id="LOAD-005", arrival_minute=45, duration_minutes=75, due_minute=180, priority=5),
        LoadRequest(load_id="LOAD-006", arrival_minute=60, duration_minutes=90, due_minute=240, priority=1),
        LoadRequest(load_id="LOAD-007", arrival_minute=75, duration_minutes=60, due_minute=210, priority=3),
        LoadRequest(load_id="LOAD-008", arrival_minute=90, duration_minutes=50, due_minute=200, priority=4),
        LoadRequest(load_id="LOAD-009", arrival_minute=100, duration_minutes=80, due_minute=260, priority=2),
        LoadRequest(load_id="LOAD-010", arrival_minute=120, duration_minutes=100, due_minute=300, priority=5),
    ]
    result = optimize_warehouse_schedule(loads, dock_count=3, horizon_minutes=480)
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
