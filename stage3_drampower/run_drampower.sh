#!/bin/bash
# run_drampower.sh — Run DRAMPower for each workload trace
#
# Prerequisites:
#   - DRAMPower built and accessible at $DRAMPOWER_ROOT
#   - gem5 traces in stage2_gem5/traces/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRAMPOWER_ROOT="${DRAMPOWER_ROOT:-$HOME/DRAMPower}"
DRAMPOWER_BIN="$DRAMPOWER_ROOT/drampower"
DEVICE_SPEC="$SCRIPT_DIR/DDR4_8Gb_x8_3200.xml"

WORKLOADS=("streaming" "random_access" "rowhammer")

mkdir -p "$SCRIPT_DIR/raw_output"
mkdir -p "$SCRIPT_DIR/current_waveforms"

echo "============================================"
echo "  DDR4 PDN Optimizer — DRAMPower Extraction"
echo "============================================"

# Check if DRAMPower binary exists
if [ ! -f "$DRAMPOWER_BIN" ]; then
    echo "[WARN] DRAMPower binary not found at: $DRAMPOWER_BIN"
    echo "       Falling back to synthetic waveform generation..."
    echo ""

    cd "$PROJECT_ROOT"
    python stage3_drampower/parse_output.py synthetic \
        --workload all \
        --output-dir "$SCRIPT_DIR/current_waveforms" \
        --duration 10.0

    echo ""
    echo "[OK] Synthetic waveforms generated in $SCRIPT_DIR/current_waveforms/"
    exit 0
fi

for workload in "${WORKLOADS[@]}"; do
    TRACE="$PROJECT_ROOT/stage2_gem5/traces/${workload}/dramsim3_cmd_trace.csv"
    LOG="$SCRIPT_DIR/raw_output/${workload}.log"
    OUTPUT="$SCRIPT_DIR/current_waveforms/${workload}_It.csv"

    if [ ! -f "$TRACE" ]; then
        echo "[SKIP] Trace not found for ${workload} — generating synthetic"
        cd "$PROJECT_ROOT"
        python stage3_drampower/parse_output.py synthetic \
            --workload "$workload" \
            --output-dir "$SCRIPT_DIR/current_waveforms" \
            --duration 10.0
        continue
    fi

    echo "--- Processing: ${workload} ---"
    "$DRAMPOWER_BIN" \
        -m "$DEVICE_SPEC" \
        -c "$TRACE" \
        -t \
        > "$LOG"

    cd "$PROJECT_ROOT"
    python stage3_drampower/parse_output.py parse \
        --input "$LOG" \
        --output "$OUTPUT"

    echo "[OK] ${workload} current waveform extracted"
    echo ""
done

echo "============================================"
echo "  DRAMPower extraction complete."
echo "  Waveforms in: $SCRIPT_DIR/current_waveforms/"
echo "============================================"
