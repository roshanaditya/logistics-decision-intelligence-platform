from app.models.cost_prediction.data import generate_dataset
from app.models.cost_prediction.features import FEATURE_COLUMNS, prepare_features


def test_synthetic_dataset_schema_and_target():
    frame = generate_dataset(n_rows=100, seed=7)
    assert len(frame) == 100
    assert "transportation_cost" in frame.columns
    assert frame["transportation_cost"].gt(0).all()


def test_feature_preparation():
    frame = generate_dataset(n_rows=20, seed=7)
    features = prepare_features(frame)
    assert list(features.columns) == FEATURE_COLUMNS
    assert str(features["carrier"].dtype) == "category"
