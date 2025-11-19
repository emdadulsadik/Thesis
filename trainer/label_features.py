import pandas as pd
import os, logging, sys

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DATA_DIR = "/data"
RAW_FILE = os.path.join(DATA_DIR, "features.csv")
LABELED_FILE = os.path.join(DATA_DIR, "labeled_features.csv")

CPU_THRESHOLD = 80.0
BUFFER_THRESHOLD = 25

def label_data(df):
    df["label"] = ((df["cpu_usage"] > CPU_THRESHOLD) | 
                   (df["buffer_size"] > BUFFER_THRESHOLD)).astype(int)
    return df

def main():
    if not os.path.exists(RAW_FILE):
        logging.info(f"[Labeling] No features.csv found in {DATA_DIR}")
        return

    logging.info("[Labeling] Loading features...")
    df = pd.read_csv(RAW_FILE)

    # Ensure columns exist
    for col in ["cpu_usage", "buffer_size"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    logging.info("[Labeling] Applying labeling rules...")
    df = label_data(df)
    df.to_csv(LABELED_FILE, index=False)
    logging.info(f"[Labeling] Done. Saved labeled dataset -> {LABELED_FILE}")

if __name__ == "__main__":
    main()
