"""Train a median baseline and LightGBM; log experiment metrics to MLflow."""
import json
from pathlib import Path
import joblib
import mlflow
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from app.models.cost_prediction.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, TARGET_COLUMN, prepare_features

DATA_PATH = Path("data/sample/transportation_costs.csv")
ARTIFACT_DIR = Path("artifacts/cost_prediction")


def metrics(y_true, y_pred):
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape_percent": float(np.mean(np.abs((y_true-y_pred) / np.maximum(np.abs(y_true), 1))) * 100),
        "r2": float(r2_score(y_true, y_pred)),
    }


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError("Generate data first: python -m app.models.cost_prediction.data")
    frame = pd.read_csv(DATA_PATH)
    X, y = prepare_features(frame), frame[TARGET_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Ensure target arrays are contiguous and use a consistent numeric type
    y_train = np.ascontiguousarray(
        y_train.to_numpy(dtype=np.float64)
    )

    y_test = np.ascontiguousarray(
        y_test.to_numpy(dtype=np.float64)
    )

    # Ensure feature DataFrames are independent copies
    X_train = X_train.copy()
    X_test = X_test.copy()

    baseline = DummyRegressor(strategy="median").fit(X_train, y_train)
    baseline_metrics = metrics(y_test, baseline.predict(X_test))

    model = LGBMRegressor(objective="regression", n_estimators=500, learning_rate=0.04,
                          num_leaves=31, subsample=0.85, colsample_bytree=0.85,
                          reg_lambda=1.0, random_state=42, n_jobs=-1, verbosity=-1)
    model.fit(X_train, y_train, categorical_feature=CATEGORICAL_FEATURES)
    model_metrics = metrics(y_test, model.predict(X_test))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACT_DIR / "model.joblib")
    (ARTIFACT_DIR / "feature_columns.json").write_text(json.dumps(FEATURE_COLUMNS, indent=2))
    report = {"baseline_median": baseline_metrics, "lightgbm": model_metrics,
              "train_rows": len(X_train), "test_rows": len(X_test), "synthetic_data": True}
    (ARTIFACT_DIR / "metrics.json").write_text(json.dumps(report, indent=2))

    # mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("transportation-cost-prediction")
    with mlflow.start_run(run_name="lightgbm-v1"):
        mlflow.log_params({"model": "LGBMRegressor", "n_estimators": 500,
                           "learning_rate": 0.04, "num_leaves": 31, "test_size": 0.2,
                           "random_state": 42, "data_type": "synthetic"})
        mlflow.log_metrics({f"baseline_{k}": v for k, v in baseline_metrics.items()})
        mlflow.log_metrics({f"lightgbm_{k}": v for k, v in model_metrics.items()})
        mlflow.log_artifact(str(ARTIFACT_DIR / "metrics.json"))
    print(json.dumps(report, indent=2))
    print(f"Model saved: {ARTIFACT_DIR / 'model.joblib'}")


if __name__ == "__main__":
    main()
