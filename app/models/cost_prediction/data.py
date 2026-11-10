"""Generate fictional shipment data for portfolio development only."""
from pathlib import Path
import numpy as np
import pandas as pd

CARRIERS = ["NorthStar", "BlueRoad", "SwiftHaul", "CargoOne", "TransGlobal"]
MODES = ["FTL", "LTL", "Refrigerated"]
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]


def generate_dataset(n_rows: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    distance = rng.integers(80, 4200, n_rows)
    weight = rng.integers(100, 24000, n_rows)
    volume = np.round(rng.uniform(1, 85, n_rows), 2)
    carrier = rng.choice(CARRIERS, n_rows)
    mode = rng.choice(MODES, n_rows, p=[0.62, 0.28, 0.10])
    origin = rng.choice(REGIONS, n_rows)
    destination = rng.choice(REGIONS, n_rows)
    fuel = np.round(rng.uniform(0.85, 1.35, n_rows), 3)
    urgency = rng.choice(["Standard", "Priority", "Critical"], n_rows, p=[0.68, 0.25, 0.07])
    month = rng.integers(1, 13, n_rows)
    weekend = rng.integers(0, 2, n_rows)

    carrier_factor = {"NorthStar": 1.00, "BlueRoad": 0.96, "SwiftHaul": 1.07, "CargoOne": 1.03, "TransGlobal": 0.99}
    mode_factor = {"FTL": 1.0, "LTL": 1.42, "Refrigerated": 1.68}
    urgency_factor = {"Standard": 1.0, "Priority": 1.13, "Critical": 1.27}
    seasonal = 1 + 0.07 * np.sin((month - 1) * 2 * np.pi / 12)
    base = 115 + distance * 0.78 + weight * 0.026 + volume * 2.4
    noise = rng.normal(0, 0.075, n_rows)
    cost = (base * np.array([carrier_factor[x] for x in carrier])
            * np.array([mode_factor[x] for x in mode])
            * np.array([urgency_factor[x] for x in urgency])
            * fuel * seasonal * np.where(origin == destination, 0.96, 1.04)
            * (1 + weekend * 0.045) * (1 + noise))
    return pd.DataFrame({
        "distance_km": distance, "weight_kg": weight, "volume_m3": volume,
        "carrier": carrier, "transport_mode": mode, "origin_region": origin,
        "destination_region": destination, "fuel_index": fuel, "urgency": urgency,
        "month": month, "weekend_pickup": weekend,
        "transportation_cost": np.maximum(cost, 50).round(2),
    })


def save_dataset(path="data/sample/transportation_costs.csv", n_rows=6000, seed=42):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_dataset(n_rows, seed).to_csv(output, index=False)
    return output


if __name__ == "__main__":
    print(f"Saved synthetic data to {save_dataset()}")
