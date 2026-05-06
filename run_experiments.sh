#!/bin/bash

# Configuration
PATRONS=(5 10 20 30 50)
ALGORITHMS=(0 1 2 3)
ALG_NAMES=("FCFS" "SJF" "PRIORITY" "MLFQ")
SEEDS=(42 123 999 2024 31415)
SWITCH_TIME=0
RESULTS_DIR="results"

mkdir -p "$RESULTS_DIR"

# Compile first
javac -d out src/barScheduling/*.java 2>/dev/null || {
    echo "Compilation failed"; exit 1;
}

for n in "${PATRONS[@]}"; do
    for seed in "${SEEDS[@]}"; do
        for alg in "${ALGORITHMS[@]}"; do
            ALG_LABEL="${ALG_NAMES[$alg]}"
            echo "Running: patrons=$n alg=$ALG_LABEL seed=$seed"

            # Results go to: results/FCFS_n20_s42_results.csv
            # The Barman class names its file after the scheduler,
            # so we rename after each run to include n and seed
            java -cp out barScheduling.SchedulingSimulation \
                $n $alg $SWITCH_TIME $seed \
                > "$RESULTS_DIR/${ALG_LABEL}_n${n}_s${seed}.log" 2>&1

            # Rename the CSV the Barman wrote
            SRC="$RESULTS_DIR/${ALG_LABEL}_results.csv"
            DST="$RESULTS_DIR/${ALG_LABEL}_n${n}_s${seed}.csv"
            if [ -f "$SRC" ]; then
                mv "$SRC" "$DST"
            fi
        done
    done
done

echo "All experiments complete. Results in: $RESULTS_DIR/"