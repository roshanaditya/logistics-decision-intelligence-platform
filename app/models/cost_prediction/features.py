CATEGORICAL_FEATURES = ["carrier", "transport_mode", "origin_region", "destination_region", "urgency"]
NUMERIC_FEATURES = ["distance_km", "weight_kg", "volume_m3", "fuel_index", "month", "weekend_pickup"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "transportation_cost"


def prepare_features(frame):
    result = frame[FEATURE_COLUMNS].copy()
    for column in CATEGORICAL_FEATURES:
        result[column] = result[column].astype("category")
    return result
