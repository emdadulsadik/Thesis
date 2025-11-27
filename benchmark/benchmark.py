import pandas as pd
import matplotlib.pyplot as plt
import sys, logging

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BENCHMARK_PATH = "/data/benchmark.csv"
OUT_PATH = "/data/benchmark_plot.png"

df = pd.read_csv(BENCHMARK_PATH)

df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

plt.figure(figsize=(12,6))

pre = df[df['event_type'] == 'prewarm']
cold = df[df['event_type'] == 'cold']

plt.plot(pre['timestamp'], pre['start_time_ms'], label="Prewarm start time (ms)")
plt.plot(cold['timestamp'], cold['start_time_ms'], label="Cold start time (ms)")

plt.xlabel("Timestamp")
plt.ylabel("Start time (ms)")
plt.title("Warm vs Cold Processor Startup")
plt.legend()

plt.grid(True)
plt.tight_layout()

plt.savefig(OUT_PATH)
logging.info(f"Benchmark graph saved to: {OUT_PATH}")
