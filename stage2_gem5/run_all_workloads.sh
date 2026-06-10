#!/bin/bash
# run_all_workloads.sh — Run gem5 simulations for all three workload binaries
#
# Prerequisites:
#   - gem5 built at $GEM5_ROOT/build/X86/gem5.opt
#   - Workload binaries compiled in stage1_workloads/
#   - DRAMSim3 config in stage2_gem5/dramsim3_configs/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GEM5_ROOT="${GEM5_ROOT:-$HOME/gem5}"
GEM5_BIN="$GEM5_ROOT/build/X86/gem5.opt"

WORKLOADS=("streaming" "random_access" "rowhammer")

# Verify gem5 binary exists
if [ ! -f "$GEM5_BIN" ]; then
    echo "[ERROR] gem5 binary not found at: $GEM5_BIN"
    echo "        Set GEM5_ROOT environment variable to your gem5 installation."
    exit 1
fi

echo "============================================"
echo "  DDR4 PDN Optimizer — gem5 Simulation Suite"
echo "============================================"
echo ""
echo "gem5 binary: $GEM5_BIN"
echo "Project root: $PROJECT_ROOT"
echo ""

for workload in "${WORKLOADS[@]}"; do
    ELF="$PROJECT_ROOT/stage1_workloads/${workload}.elf"
    TRACE_DIR="$SCRIPT_DIR/traces/${workload}"

    if [ ! -f "$ELF" ]; then
        echo "[SKIP] ${workload}.elf not found — run 'make' in stage1_workloads/ first"
        continue
    fi

    echo "--- Running: ${workload} ---"
    mkdir -p "$TRACE_DIR"

    "$GEM5_BIN" \
        --outdir="$TRACE_DIR" \
        "$SCRIPT_DIR/se_config.py" \
        "$ELF" \
        "$TRACE_DIR" \
        2>&1 | tee "$TRACE_DIR/gem5_stdout.log"

    echo "[OK] ${workload} complete — traces in $TRACE_DIR"
    echo ""
done

echo "============================================"
echo "  All simulations complete."
echo "  Traces are in: $SCRIPT_DIR/traces/"
echo "============================================"
