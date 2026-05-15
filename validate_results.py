import csv
import sys
from pathlib import Path

EXPECTED_HEADER = [
    "patron_id",
    "order_id",
    "arrival_time",
    "burst_time",
    "priority",
    "service_start_time",
    "completion_time",
    "response_time",
    "waiting_time",
    "turnaround_time",
    "queue_level",
]


def validate_csv(path: Path) -> int:
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        return 1

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print(f"ERROR: empty file: {path}")
            return 1

        if header != EXPECTED_HEADER:
            print("ERROR: CSV header does not match expected format")
            print(" expected:", EXPECTED_HEADER)
            print(" found:   ", header)
            return 1

        errors = 0
        line_number = 1
        algorithm = path.stem.split("_")[0].upper()
        is_mlfq = algorithm == "MLFQ"
        is_fcfs = algorithm == "FCFS"
        is_sjf = algorithm == "SJF"
        is_priority = algorithm == "PRIORITY"
        is_hrrn = algorithm == "HRRN"

        for row in reader:
            line_number += 1
            if len(row) != len(EXPECTED_HEADER):
                print(f"ERROR: line {line_number} has {len(row)} fields, expected {len(EXPECTED_HEADER)}")
                errors += 1
                continue

            try:
                patron_id = int(row[0])
                order_id = int(row[1])
                arrival_time = int(row[2])
                burst_time = int(row[3])
                priority = int(row[4])
                service_start = int(row[5])
                completion_time = int(row[6])
                response_time = int(row[7])
                waiting_time = int(row[8])
                turnaround_time = int(row[9])
                queue_level = int(row[10])
            except ValueError as exc:
                print(f"ERROR: line {line_number} has invalid numeric value: {exc}")
                errors += 1
                continue

            if patron_id < 0 or order_id < 0 or burst_time <= 0 or priority <= 0:
                print(f"ERROR: line {line_number} has invalid identifier or workload values")
                errors += 1

            if waiting_time < 0 or response_time < 0 or turnaround_time < 0:
                print(f"ERROR: line {line_number} has negative timing values: waiting={waiting_time}, response={response_time}, turnaround={turnaround_time}")
                errors += 1

            if not (arrival_time <= service_start < completion_time):
                print(f"ERROR: line {line_number} has inconsistent timestamps: arrival={arrival_time}, serviceStart={service_start}, completion={completion_time}")
                errors += 1

            if turnaround_time < waiting_time:
                print(f"ERROR: line {line_number} has turnaroundTime < waitingTime: {turnaround_time} < {waiting_time}")
                errors += 1

            if is_mlfq:
                if queue_level not in {0, 1, 2}:
                    print(f"ERROR: line {line_number} has invalid queueLevel for MLFQ: {queue_level}")
                    errors += 1
            elif is_fcfs or is_sjf or is_priority or is_hrrn:
                if queue_level != -1:
                    print(f"ERROR: line {line_number} has queueLevel {queue_level}, expected -1 for {algorithm}")
                    errors += 1

        if errors == 0:
            print(f"PASS: {path} is valid ({line_number - 1} data rows)")
            return 0

        print(f"FAIL: {errors} validation issue(s) found in {path}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_results.py results/<algorithm>/<ALGORITHM>_n<patrons>_s<seed>.csv")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    raise SystemExit(validate_csv(file_path))
