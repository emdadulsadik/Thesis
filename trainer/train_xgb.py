import pandas as pd
import xgboost as xgb
import logging, sys

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DATA_PATH = "/data/labeled_features.csv"
MODEL_PATH = "/data/xgb_model.json"

logging.info("[Training] Loading labeled features...")

df = pd.read_csv(DATA_PATH)

# Define the updated feature set
features = [
    "cpu_usage", "mem_usage",
    "buffer_size", "buffer_capacity",
    "avg_latency", "avg_rate",
    "temperature", "vibration", "load"
]

# Filter available columns dynamically
features = [f for f in features if f in df.columns]

X = df[features]
y = df["label"]

logging.info(f"[Training] Using features: {features}")
logging.info(f"[Training] Dataset size: {len(X)} samples")

# Train a simple XGBoost model
dtrain = xgb.DMatrix(X, label=y)
params = {
    "objective": "binary:logistic",
    "max_depth": 4,
    "eta": 0.1,
    "eval_metric": "logloss"
}

model = xgb.train(params, dtrain, num_boost_round=50)
model.save_model(MODEL_PATH)

logging.info(f"[Training] Model saved -> {MODEL_PATH}")

