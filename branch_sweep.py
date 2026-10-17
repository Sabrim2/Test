#!/usr/bin/env python3
import csv
import re
import subprocess
from datetime import datetime
from pathlib import Path

BIN = Path(__file__).resolve().parent
ROOT = BIN.parent
TRACE = Path.home() / "macsim-4dm4-lab1/tools/benchmarks/mergesort/BM.txt"
PARAMS = BIN / "params.in"
TRACE_LIST = BIN / "trace_file_list"
SUBMISSION = ROOT / "submission"

EXPERIMENTS = [
    ("BTB_impact.csv", "BTB", [
        ("Disabled", {"enable_btb": 0, "perfect_btb": 0}),
        ("Perfect", {"enable_btb": 1, "perfect_btb": 1}),
        ("NonPerfect", {"enable_btb": 1, "perfect_btb": 0}),
    ]),
    ("sweep_btb_length.csv", "BTB Length", [
        (str(n), {"perfect_btb": 0, "btb_entries": n})
        for n in [2, 4, 8, 16, 32, 64, 128]
    ]),
    ("BP_impact.csv", "BP", [
        ("Disabled", {"use_branch_prediction": 0, "perfect_bp": 0}),
        ("Perfect", {"use_branch_prediction": 1, "perfect_bp": 1}),
        ("NonPerfect (gshare)", {
            "use_branch_prediction": 1, "perfect_bp": 0
        }),
    ]),
    ("sweep_bp_length.csv", "BP History Length", [
        (str(n), {"perfect_bp": 0, "bp_hist_length": n})
        for n in [1, 2, 4, 8, 16]
    ]),
]

# Section 4 baseline. Every run starts from this configuration.
BASE = {
    "num_sim_cores": 1,
    "num_sim_small_cores": 0,
    "num_sim_medium_cores": 0,
    "num_sim_large_cores": 1,
    "large_core_type": "x86",
    "sim_cycle_count": 0,
    "max_insts": 3000000,
    "debug_exec_stage": 0,
    "debug_print_trace": 0,
    "large_width": 1,
    "large_core_fetch_latency": 5,
    "large_core_alloc_latency": 5,
    "use_branch_prediction": 1,
    "bp_dir_mech": "gshare",
    "bp_hist_length": 1,
    "enable_btb": 1,
    "perfect_btb": 1,
    "btb_entries": 1024,
    "perfect_bp": 1,
    "isched_large_rate": 4,
    "msched_large_rate": 4,
    "fsched_large_rate": 4,
    "large_core_schedule": "io",
    "rob_large_size": 256,
    "fetch_policy": "rr",
}
for unit in "imfs":
    BASE[f"{unit}sched_large_size"] = 32

def atomic_write(path, content):
    temporary = path.with_name(path.name + ".branch_tmp")
    temporary.write_bytes(content)
    temporary.replace(path)

def main():
    for path in [TRACE, TRACE.with_name("BM_0.raw"), BIN / "macsim"]:
        if not path.is_file():
            raise RuntimeError(f"Missing input: {path}")

    for filename, _, _ in EXPERIMENTS:
        if (SUBMISSION / filename).exists():
            raise RuntimeError(f"{filename} already exists; preserve it first.")

    original_params = PARAMS.read_bytes()
    original_trace_list = TRACE_LIST.read_bytes()
    original_text = original_params.decode()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    logs = ROOT / "work" / f"branch_sweep_{stamp}"
    configs = SUBMISSION / f"branch_params_{stamp}"
    logs.mkdir(parents=True)
    configs.mkdir(parents=True)
    (logs / "params.in.original").write_bytes(original_params)
    (logs / "trace_file_list.original").write_bytes(original_trace_list)

    try:
        for filename, heading, cases in EXPERIMENTS:
            with (SUBMISSION / filename).open("x", newline="") as output:
                writer = csv.writer(output, delimiter=";")
                writer.writerow([heading, "Execution Time"])
                output.flush()

                for index, (label, changes) in enumerate(cases, 1):
                    settings = {**BASE, **changes}
                    lines = [
                        line for line in original_text.splitlines()
                        if not line.split()
                        or line.split()[0] not in settings
                    ]
                    lines += [f"{key} {value}" for key, value in settings.items()]
                    configuration = ("\n".join(lines) + "\n").encode()

                    tag = f"{Path(filename).stem}_{index}"
                    atomic_write(PARAMS, configuration)
                    atomic_write(TRACE_LIST, f"1\n{TRACE}\n".encode())
                    (configs / f"{tag}.params.in").write_bytes(configuration)

                    print(f"Running {filename}: {label}", flush=True)
                    log = logs / f"{tag}.log"
                    with log.open("wb") as stream:
                        result = subprocess.run(
                            ["./macsim"], cwd=BIN,
                            stdout=stream, stderr=subprocess.STDOUT
                        )

                    if result.returncode:
                        raise RuntimeError(f"MacSim failed; inspect {log}")

                    matches = re.findall(
                        r"cycles:\s*\[?\s*(\d+)",
                        log.read_text(errors="replace")
                    )
                    if not matches or int(matches[-1]) <= 0:
                        raise RuntimeError(f"No valid cycle count in {log}")

                    cycles = int(matches[-1])
                    writer.writerow([label, cycles])
                    output.flush()
                    print(f"  {cycles} cycles", flush=True)
    finally:
        atomic_write(PARAMS, original_params)
        atomic_write(TRACE_LIST, original_trace_list)

    print("Finished all 18 runs. Four CSVs saved in submission.")

if __name__ == "__main__":
    main()
