#!/bin/bash
# Run from the Lab 2 bin folder.
set -euo pipefail

BENCHMARKS=(
  median memBW memcpy memlatency mergesort multiply
  qsort rsort spmv st-matmul st-vvadd towers vvadd
)

TRACE_ROOT="$HOME/macsim-4dm4-lab1/tools/benchmarks"
OUT="../submission/width_sweep.csv"
RUN_DIR="../work/width_sweep_$(date +%Y%m%d_%H%M%S)"

# Check all inputs before starting.
for bench in "${BENCHMARKS[@]}"; do
  for file in BM.txt BM_0.raw; do
    test -s "$TRACE_ROOT/$bench/$file" || {
      echo "Missing trace: $TRACE_ROOT/$bench/$file"
      exit 1
    }
  done
done

if [[ -e "$OUT" ]]; then
  echo "$OUT already exists. Rename it before starting another sweep."
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

echo "Benchmark;large_width;Cycles" > "$OUT"

for bench in "${BENCHMARKS[@]}"; do
  for w in 1 2 3 4; do
    echo "Running $bench, width $w..."

    # Start each run from the original settings.
    sed -E '/^[[:space:]]*large_width([[:space:]]|$)/d' \
      "$RUN_DIR/params.in.original" > params.in
    echo "large_width $w" >> params.in

    printf '1\n%s\n' "$TRACE_ROOT/$bench/BM.txt" > trace_file_list

    prefix="$RUN_DIR/${bench}_w${w}"
    cp params.in "${prefix}.params.in"

    if ! ./macsim > "${prefix}.log" 2>&1; then
      echo "Run failed. Check ${prefix}.log"
      exit 1
    fi

    cycles=$(
      { grep -Eo 'cycles:[[:space:]]*\[?[[:space:]]*[0-9]+' \
          "${prefix}.log" || true; } |
      tail -n 1 | grep -Eo '[0-9]+' || true
    )

    if [[ -z "$cycles" ]]; then
      echo "No cycle count found. Check ${prefix}.log"
      exit 1
    fi

    echo "$bench;$w;$cycles" | tee -a "$OUT"
  done
done

echo "Finished all 52 runs. Results: $OUT"
