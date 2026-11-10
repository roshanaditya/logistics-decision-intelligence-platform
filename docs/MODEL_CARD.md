# Model Card — Transportation Cost Prediction

## Status
Phase 2 prototype; not validated for real-world use.

## Intended use
Demonstrate regression that estimates fictional shipment transportation cost from shipment, carrier, route, fuel and urgency attributes.

## Data
Generated synthetically by `app/models/cost_prediction/data.py`. It does not represent any real company, carrier, route or market price.

## Model and evaluation
LightGBM regression compared with a median `DummyRegressor`. Random 80/20 split; metrics: MAE, RMSE, MAPE and R-squared.

## Limitations
Synthetic data has a deliberately learnable cost structure. Metrics do not establish real-world predictive performance. USD is a demonstration assumption, not a sourced quote. No temporal validation, uncertainty intervals, or production monitoring yet.

## Next steps
Add time-based validation, error analysis by carrier/mode/region, prediction intervals and validation against authorized real data before business use.
