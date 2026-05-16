import glob
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR.parent / "results"
PLOTS_DIR = SCRIPT_DIR / "plots"
SUMMARY_PATH = SCRIPT_DIR / "summary_statistics.csv"

ALGORITHM_ORDER = ["FCFS", "SJF", "PRIORITY", "MLFQ", "LOTTERY"]
COLORS = {
    "FCFS": "#1f77b4",
    "SJF": "#ff7f0e",
    "PRIORITY": "#2ca02c",
    "MLFQ": "#d62728",
    "LOTTERY": "#9467bd",
}

plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "figure.figsize": (9, 5),
})


def parse_result_filename(path):
    stem = Path(path).stem
    parts = stem.split("_")
    if len(parts) != 3:
        raise ValueError(f"Unexpected results filename format: {stem}")

    algorithm = parts[0]
    if algorithm == "AWFQ":
        algorithm = "LOTTERY"
    n_patrons = int(parts[1].removeprefix("n"))
    seed = int(parts[2].removeprefix("s"))
    return algorithm, n_patrons, seed


def load_results():
    csv_files = sorted(glob.glob(str(RESULTS_DIR / "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found at {RESULTS_DIR}")

    frames = []
    for csv_file in csv_files:
        algorithm, n_patrons, seed = parse_result_filename(csv_file)
        frame = pd.read_csv(csv_file)
        frame["algorithm"] = algorithm
        frame["n_patrons"] = n_patrons
        frame["seed"] = seed
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    return data, csv_files


def build_run_summary(df):
    grouped = df.groupby(["algorithm", "n_patrons", "seed"], sort=False)

    run_stats = grouped.agg(
        waiting_mean=("waitingTime", "mean"),
        waiting_median=("waitingTime", "median"),
        waiting_std=("waitingTime", "std"),
        waiting_min=("waitingTime", "min"),
        waiting_max=("waitingTime", "max"),
        response_mean=("responseTime", "mean"),
        response_median=("responseTime", "median"),
        response_std=("responseTime", "std"),
        response_min=("responseTime", "min"),
        response_max=("responseTime", "max"),
        turnaround_mean=("turnaroundTime", "mean"),
        turnaround_median=("turnaroundTime", "median"),
        turnaround_std=("turnaroundTime", "std"),
        turnaround_min=("turnaroundTime", "min"),
        turnaround_max=("turnaroundTime", "max"),
        order_count=("orderID", "count"),
        arrival_min=("arrivalTime", "min"),
        completion_max=("completionTime", "max"),
    ).reset_index()

    elapsed_seconds = (run_stats["completion_max"] - run_stats["arrival_min"]) / 1000.0
    run_stats["throughput"] = run_stats["order_count"] / elapsed_seconds
    run_stats = run_stats.drop(columns=["arrival_min", "completion_max"])

    std_columns = ["waiting_std", "response_std", "turnaround_std"]
    run_stats[std_columns] = run_stats[std_columns].fillna(0.0)
    return run_stats


def build_aggregate_summary(run_stats):
    metric_columns = [
        "waiting_mean", "waiting_median", "waiting_std", "waiting_min", "waiting_max",
        "response_mean", "response_median", "response_std", "response_min", "response_max",
        "turnaround_mean", "turnaround_median", "turnaround_std", "turnaround_min", "turnaround_max",
        "throughput",
    ]

    agg_map = {}
    for column in metric_columns:
        agg_map[f"{column}_mean"] = (column, "mean")
        agg_map[f"{column}_std"] = (column, "std")

    agg = run_stats.groupby(["algorithm", "n_patrons"]).agg(**agg_map).reset_index()
    agg = agg.fillna(0.0)
    return agg


def ordered_subset(frame):
    ordered = frame.copy()
    ordered["algorithm"] = pd.Categorical(
        ordered["algorithm"],
        categories=ALGORITHM_ORDER,
        ordered=True,
    )
    return ordered.sort_values(["algorithm", "n_patrons"])


def patron_sizes_from(frame):
    return sorted(frame["n_patrons"].dropna().unique().tolist())


def save_line_plot_with_errorbars(agg, x_values, y_col, err_col, title, ylabel, output_path):
    plt.figure()
    ordered = ordered_subset(agg)

    for algorithm in ALGORITHM_ORDER:
        subset = ordered[ordered["algorithm"] == algorithm].sort_values("n_patrons")
        plt.errorbar(
            subset["n_patrons"],
            subset[y_col],
            yerr=subset[err_col],
            marker="o",
            capsize=4,
            linewidth=1.8,
            color=COLORS[algorithm],
            label=algorithm,
        )

    plt.title(title)
    plt.xlabel("Number of Patrons")
    plt.ylabel(ylabel)
    plt.xticks(x_values)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_box_plot(df, metric, title, ylabel, output_path):
    subset = df[df["n_patrons"] == 20]
    data = [subset[subset["algorithm"] == algorithm][metric].tolist() for algorithm in ALGORITHM_ORDER]

    plt.figure()
    box = plt.boxplot(data, tick_labels=ALGORITHM_ORDER, showfliers=True, patch_artist=True)
    for patch, algorithm in zip(box["boxes"], ALGORITHM_ORDER):
        patch.set_facecolor(COLORS[algorithm])
        patch.set_alpha(0.55)

    plt.title(title)
    plt.xlabel("Algorithm")
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_throughput_bar_chart(agg, output_path):
    subset = ordered_subset(agg[agg["n_patrons"] == 20])
    heights = subset["throughput_mean"].tolist()
    labels = subset["algorithm"].tolist()
    colors = [COLORS[label] for label in labels]

    plt.figure()
    bars = plt.bar(labels, heights, color=colors)
    plt.title("Throughput Comparison (n=20 Patrons)")
    plt.xlabel("Algorithm")
    plt.ylabel("Throughput (orders/sec)")

    for bar, value in zip(bars, heights):
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_fairness_plot(df, output_path):
    per_patron = (
        df.groupby(["algorithm", "n_patrons", "seed", "patronID"])["waitingTime"]
        .mean()
        .reset_index(name="patron_mean_waiting")
    )
    per_run_variance = (
        per_patron.groupby(["algorithm", "n_patrons", "seed"])["patron_mean_waiting"]
        .var()
        .reset_index(name="waiting_variance")
    )
    fairness = (
        per_run_variance.groupby(["algorithm", "n_patrons"])["waiting_variance"]
        .mean()
        .reset_index()
        .fillna(0.0)
    )

    x_values = patron_sizes_from(df)
    width = 0.8 / max(1, len(ALGORITHM_ORDER))
    positions = list(range(len(x_values)))
    center_offset = (len(ALGORITHM_ORDER) - 1) / 2.0

    plt.figure()
    for index, algorithm in enumerate(ALGORITHM_ORDER):
        subset = fairness[fairness["algorithm"] == algorithm].set_index("n_patrons")
        heights = [float(subset["waiting_variance"].get(n, 0.0)) for n in x_values]
        offsets = [pos + (index - center_offset) * width for pos in positions]
        plt.bar(offsets, heights, width=width, color=COLORS[algorithm], label=algorithm)

    plt.title("Per-Patron Waiting Time Variance (Fairness)")
    plt.xlabel("Number of Patrons")
    plt.ylabel("Variance in Per-Patron Waiting Time (ms²)")
    plt.xticks(positions, x_values)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_line_plot_without_errorbars(agg, x_values, y_col, title, ylabel, output_path):
    plt.figure()
    ordered = ordered_subset(agg)

    for algorithm in ALGORITHM_ORDER:
        subset = ordered[ordered["algorithm"] == algorithm].sort_values("n_patrons")
        plt.plot(
            subset["n_patrons"],
            subset[y_col],
            marker="o",
            linewidth=1.8,
            color=COLORS[algorithm],
            label=algorithm,
        )

    plt.title(title)
    plt.xlabel("Number of Patrons")
    plt.ylabel(ylabel)
    plt.xticks(x_values)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_mlfq_queue_distribution(df, output_path):
    subset = df[(df["algorithm"] == "MLFQ") & (df["n_patrons"] == 20)]
    counts = subset["queueLevel"].value_counts().reindex([0, 1, 2], fill_value=0)

    plt.figure()
    plt.bar([0, 1, 2], counts.values, color=COLORS["MLFQ"])
    plt.title("MLFQ Queue Level Distribution (n=20)")
    plt.xlabel("Queue Level")
    plt.ylabel("Number of Orders")
    plt.xticks([0, 1, 2], [0, 1, 2])
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    df, csv_files = load_results()
    print(f"Loaded {len(csv_files)} CSV files from {RESULTS_DIR}")
    print("Master DataFrame shape:", df.shape)
    print(df.head())
    print("Columns:", list(df.columns))

    run_stats = build_run_summary(df)
    agg = build_aggregate_summary(run_stats)
    agg = ordered_subset(agg)
    x_values = patron_sizes_from(agg)

    agg.to_csv(SUMMARY_PATH, index=False)
    print(agg.to_string(index=False))

    starvation = (
        run_stats.groupby(["algorithm", "n_patrons"])["waiting_max"]
        .mean()
        .reset_index(name="mean_max_waiting")
    )
    starvation = ordered_subset(starvation)

    predictability = (
        run_stats.groupby(["algorithm", "n_patrons"])["waiting_std"]
        .mean()
        .reset_index(name="mean_waiting_std")
    )
    predictability = ordered_subset(predictability)

    saved_plots = []

    waiting_plot = PLOTS_DIR / "waiting_time_vs_patrons.png"
    save_line_plot_with_errorbars(
        agg,
        x_values,
        "waiting_mean_mean",
        "waiting_mean_std",
        "Mean Waiting Time by Algorithm",
        "Mean Waiting Time (ms)",
        waiting_plot,
    )
    saved_plots.append(waiting_plot)

    turnaround_plot = PLOTS_DIR / "turnaround_vs_patrons.png"
    save_line_plot_with_errorbars(
        agg,
        x_values,
        "turnaround_mean_mean",
        "turnaround_mean_std",
        "Mean Turnaround Time by Algorithm",
        "Mean Turnaround Time (ms)",
        turnaround_plot,
    )
    saved_plots.append(turnaround_plot)

    response_plot = PLOTS_DIR / "response_time_vs_patrons.png"
    save_line_plot_with_errorbars(
        agg,
        x_values,
        "response_mean_mean",
        "response_mean_std",
        "Mean Response Time by Algorithm",
        "Mean Response Time (ms)",
        response_plot,
    )
    saved_plots.append(response_plot)

    waiting_box = PLOTS_DIR / "boxplot_waiting_n20.png"
    save_box_plot(
        df,
        "waitingTime",
        "Waiting Time Distribution (n=20 Patrons)",
        "Waiting Time (ms)",
        waiting_box,
    )
    saved_plots.append(waiting_box)

    turnaround_box = PLOTS_DIR / "boxplot_turnaround_n20.png"
    save_box_plot(
        df,
        "turnaroundTime",
        "Turnaround Time Distribution (n=20 Patrons)",
        "Turnaround Time (ms)",
        turnaround_box,
    )
    saved_plots.append(turnaround_box)

    throughput_plot = PLOTS_DIR / "throughput_n20.png"
    save_throughput_bar_chart(agg, throughput_plot)
    saved_plots.append(throughput_plot)

    fairness_plot = PLOTS_DIR / "fairness_variance.png"
    save_fairness_plot(df, fairness_plot)
    saved_plots.append(fairness_plot)

    starvation_plot = PLOTS_DIR / "starvation_max_waiting.png"
    save_line_plot_without_errorbars(
        starvation,
        x_values,
        "mean_max_waiting",
        "Maximum Waiting Time by Algorithm (Starvation Risk)",
        "Mean Max Waiting Time (ms)",
        starvation_plot,
    )
    saved_plots.append(starvation_plot)

    predictability_plot = PLOTS_DIR / "predictability_stddev.png"
    save_line_plot_without_errorbars(
        predictability,
        x_values,
        "mean_waiting_std",
        "Waiting Time Std Dev (Predictability)",
        "Mean Std Dev of Waiting Time (ms)",
        predictability_plot,
    )
    saved_plots.append(predictability_plot)

    mlfq_plot = PLOTS_DIR / "mlfq_queue_distribution.png"
    save_mlfq_queue_distribution(df, mlfq_plot)
    saved_plots.append(mlfq_plot)

    print("Analysis complete. Plots saved to analysis/plots/")
    print("Summary statistics saved to analysis/summary_statistics.csv")
    for plot_path in saved_plots:
        print(plot_path.relative_to(SCRIPT_DIR.parent).as_posix())


if __name__ == "__main__":
    main()
