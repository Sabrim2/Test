#!/bin/bash
# Run from the Lab 2 bin folder.
set -euo pipefail

RATES=(isched_large_rate msched_large_rate fsched_large_rate ssched_large_rate)
TRACE="$HOME/macsim-4dm4-lab1/tools/benchmarks/mergesort/BM.txt"
OUT="../submission/rate_sweep.csv"
RUN_DIR="../work/rate_sweep_$(date +%Y%m%d_%H%M%S)"

test -s "$TRACE"
test -s "${TRACE%.txt}_0.raw"

if [[ -e "$OUT" ]]; then
  echo "$OUT already exists; rename it before another sweep."
  exit 1
fi

mkdir -p ../submission "$RUN_DIR"
cp params.in "$RUN_DIR/params.in.original"
cp trace_file_list "$RUN_DIR/trace_file_list.original"

restore_inputs() {
  cp "$RUN_DIR/params.in.original" params.in
  cp "$RUN_DIR/trace_file_list.original" trace_file_list
}
trap restore_inputs EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Parameter;Rate;Cycles" > "$OUT"

for parameter in "${RATES[@]}"; do
  for rate in 1 2 4 8 16; do
    echo "Running $parameter = $rate..."

    # Remove the settings we are controlling, keeping everything else.
    sed -E \
      '/^[[:space:]]*(large_width|[imfs]sched_large_(size|rate))([[:space:]]|$)/d' \
      "$RUN_DIR/params.in.original" > params.in

    {
      echo "large_width 4"
      for unit in i m f s; do
        echo "${unit}sched_large_size 32"
        key="${unit}sched_large_rate"
        value=1
        if [[ "$key" == "$parameter" ]]; then
          value="$rate"
        fi
        echo "$key $value"
      done
    } >> params.in

    printf '1\n%s\n' "$TRACE" > trace_file_list
    prefix="$RUN_DIR/${parameter}_${rate}"
    cp params.in "${prefix}.params.in"

    if ! ./macsim > "${prefix}.log" 2>&1; then
      echo "Run failed: ${prefix}.log"
      exit 1
    fi

    cycles=$(
      { grep -Eo 'cycles:[[:space:]]*\[?[[:space:]]*[0-9]+' \
          "${prefix}.log" || true; } |
      tail -n 1 | grep -Eo '[0-9]+' || true
    )

    if [[ -z "$cycles" ]]; then
      echo "No cycle count found: ${prefix}.log"
      exit 1
    fi

    echo "$parameter;$rate;$cycles" | tee -a "$OUT"
  done
done

echo "Finished all 20 runs. Results: $OUT"
