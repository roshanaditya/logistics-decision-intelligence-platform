from pathlib import Path
import joblib
import pandas as pd
from app.models.cost_prediction.features import prepare_features

MODEL_PATH = Path("artifacts/cost_prediction/model.joblib")


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model artifact missing. Run python -m app.models.cost_prediction.train")
    return joblib.load(MODEL_PATH)


def predict_cost(model, payload: dict) -> float:
    frame = pd.DataFrame([payload])
    return float(model.predict(prepare_features(frame))[0])
