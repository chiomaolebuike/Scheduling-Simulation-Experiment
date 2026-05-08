import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR.parent / "results"
PLOTS_DIR = SCRIPT_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

ALGORITHMS = ["FCFS", "SJF", "PRIORITY", "MLFQ"]
PATRON_SIZES = [5, 10, 20, 30, 50]

# ── 1. Load all CSVs into one master DataFrame ────────────────────────────────

def load_all_results():
    frames = []
    result_files = sorted(glob.glob(str(RESULTS_DIR / "*.csv")))
    if not result_files:
        raise FileNotFoundError(
            f"No CSV result files found in {RESULTS_DIR}. "
            "Make sure the script is run from the repository or that results exist."
        )

    for fpath in result_files:
        fname = Path(fpath).stem           # e.g. "FCFS_n20_s42" or "FCFS_results"
        parts = fname.split("_")
        alg = parts[0]
        if len(parts) >= 3 and parts[1].startswith("n") and parts[2].startswith("s"):
            n = int(parts[1].replace("n",""))
            seed = int(parts[2].replace("s",""))
        else:
            # Handle legacy format like "FCFS_results"
            n = 5  # Assume 5 patrons based on patronID range
            seed = 42  # Default seed

        df = pd.read_csv(fpath)
        df["algorithm"] = alg
        df["n_patrons"]  = n
        df["seed"]       = seed
        frames.append(df)

    return pd.concat(frames, ignore_index=True)

df = load_all_results()
print(f"Loaded {len(df)} order records across {df['seed'].nunique()} seeds")

# Data integrity checks
assert (df["waitingTime"] >= 0).all(),    "Negative waiting time!"
assert (df["turnaroundTime"] >= 0).all(), "Negative turnaround!"
assert (df["turnaroundTime"] >= df["waitingTime"]).all(), \
    "Turnaround must be >= waiting time"
assert (df["serviceStartTime"] >= df["arrivalTime"]).all(), \
    "Service cannot start before arrival"
assert (df["completionTime"] >= df["serviceStartTime"]).all(), \
    "Cannot complete before starting"

# ── 2. Per-run summary statistics ────────────────────────────────────────────

def summarise(df):
    grouped = df.groupby(["algorithm", "n_patrons", "seed"])
    summary = grouped.agg(
        mean_waiting    = ("waitingTime",    "mean"),
        median_waiting  = ("waitingTime",    "median"),
        mean_turnaround = ("turnaroundTime", "mean"),
        mean_response   = ("responseTime",   "mean"),
        total_orders    = ("waitingTime",    "count"),
    ).reset_index()

    # Throughput: orders / total elapsed wall-clock time for that run
    # Approximate: use (max completionTime - min arrivalTime)
    elapsed = df.groupby(["algorithm","n_patrons","seed"]).apply(
        lambda g: (g["completionTime"].max() - g["arrivalTime"].min()) / 1000.0
    ).reset_index(name="elapsed_s")

    summary = summary.merge(elapsed, on=["algorithm","n_patrons","seed"])
    summary["throughput"] = summary["total_orders"] / summary["elapsed_s"]
    return summary

summary = summarise(df)

# Aggregate across seeds (mean ± std)
agg = summary.groupby(["algorithm","n_patrons"]).agg(
    avg_waiting     = ("mean_waiting",    "mean"),
    std_waiting     = ("mean_waiting",    "std"),
    avg_turnaround  = ("mean_turnaround", "mean"),
    std_turnaround  = ("mean_turnaround", "std"),
    avg_response    = ("mean_response",   "mean"),
    avg_throughput  = ("throughput",      "mean"),
).reset_index()

print(agg.to_string())

# ── 3. Plot: Mean Waiting Time vs Number of Patrons ───────────────────────────

def plot_metric_vs_patrons(agg, metric_col, err_col, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9,5))
    for alg in ALGORITHMS:
        sub = agg[agg["algorithm"]==alg].sort_values("n_patrons")
        ax.errorbar(
            sub["n_patrons"], sub[metric_col],
            yerr=sub[err_col] if err_col in sub else None,
            marker="o", label=alg, capsize=4
        )
    ax.set_xlabel("Number of Patrons")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{PLOTS_DIR}/{filename}", dpi=150)
    plt.close()
    print(f"Saved: {PLOTS_DIR}/{filename}")

plot_metric_vs_patrons(
    agg, "avg_waiting", "std_waiting",
    "Mean Waiting Time (ms)", "Waiting Time by Algorithm",
    "waiting_time_comparison.png"
)
plot_metric_vs_patrons(
    agg, "avg_turnaround", "std_turnaround",
    "Mean Turnaround Time (ms)", "Turnaround Time by Algorithm",
    "turnaround_comparison.png"
)

# ── 4. Box Plot: Waiting Time Distribution (fixed n) ─────────────────────────

def boxplot_for_n(df, n, metric="waitingTime"):
    sub = df[df["n_patrons"]==n]
    data = [sub[sub["algorithm"]==alg][metric].values for alg in ALGORITHMS]

    fig, ax = plt.subplots(figsize=(8,5))
    ax.boxplot(data, labels=ALGORITHMS, showfliers=True)
    ax.set_ylabel(f"{metric} (ms)")
    ax.set_title(f"Distribution of {metric} — {n} Patrons")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fname = f"{PLOTS_DIR}/boxplot_{metric}_n{n}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"Saved: {fname}")

for n in [10, 30]:
    boxplot_for_n(df, n, "waitingTime")
    boxplot_for_n(df, n, "turnaroundTime")

# ── 5. Throughput Bar Chart ───────────────────────────────────────────────────

def throughput_bar(agg, n):
    sub = agg[agg["n_patrons"]==n]
    fig, ax = plt.subplots(figsize=(7,4))
    bars = ax.bar(sub["algorithm"], sub["avg_throughput"], color="steelblue")
    ax.bar_label(bars, fmt="%.2f")
    ax.set_ylabel("Throughput (orders/sec)")
    ax.set_title(f"Throughput Comparison — {n} Patrons")
    plt.tight_layout()
    fname = f"{PLOTS_DIR}/throughput_n{n}.png"
    plt.savefig(fname, dpi=150)
    plt.close()

throughput_bar(agg, 20)

# ── 6. Per-Patron Fairness: Waiting Time Variance per Algorithm ───────────────

def fairness_analysis(df, n):
    sub = df[df["n_patrons"]==n]
    patron_avg = sub.groupby(["algorithm","seed","patronID"])["waitingTime"].mean().reset_index()
    variance   = patron_avg.groupby(["algorithm","seed"])["waitingTime"].var().reset_index()
    variance_agg = variance.groupby("algorithm")["waitingTime"].mean().reset_index()
    variance_agg.columns = ["algorithm","avg_patron_variance"]
    print(f"\nFairness (lower variance = fairer) for n={n}:")
    print(variance_agg.to_string(index=False))

fairness_analysis(df, 20)