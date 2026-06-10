"""
run_baseline.py — Run baseline PDN simulation to validate model.

Uses a single 0603 capacitor (L_eq = 0.87nH + 0.948nH = 1.818nH).
Expected result: V(VDDQ) fails ±60mV tolerance under rowhammer workload.
This validates that the model correctly captures L·di/dt noise.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stage5_ltspice.ltspice_interface import run_simulation

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PWL_DIR = os.path.join(PROJECT_ROOT, "stage4_converter", "pwl_files")

VDDQ_NOM = 1.2
TOLERANCE = 0.060


def run_baseline():
    """Run baseline simulation with a single 0603 cap."""
    # Baseline: single Murata 4.7µF 0603 cap
    baseline = {
        "C_val": 4.7e-6,
        "ESR_val": 0.012,
        "ESL_val": 0.87e-9,
        "N_caps": 1,
    }

    workloads = ["streaming", "random_access", "rowhammer"]
    results = {}

    print("=" * 60)
    print("  DDR4 PDN — Baseline Validation")
    print("  Single 4.7µF 0603 cap (Murata GRM188R60J475ME19)")
    print("  L_eq = ESL + L_via = 0.87nH + 0.948nH = 1.818nH")
    print("=" * 60)

    for wl in workloads:
        pwl = os.path.join(PWL_DIR, f"{wl}.pwl")
        if not os.path.exists(pwl):
            print(f"\n[SKIP] {wl}: PWL file not found")
            continue

        print(f"\n--- {wl.upper()} ---")
        result = run_simulation(baseline, pwl)
        results[wl] = result

        v_max = result["V_max"]
        v_min = result["V_min"]
        v_upper = VDDQ_NOM + TOLERANCE
        v_lower = VDDQ_NOM - TOLERANCE

        over = max(0, v_max - v_upper)
        under = max(0, v_lower - v_min)

        status = "PASS" if (over == 0 and under == 0) else "FAIL"

        print(f"  V(VDDQ):   [{v_min:.4f}V, {v_max:.4f}V]")
        print(f"  Tolerance: [{v_lower:.3f}V, {v_upper:.3f}V]")
        print(f"  Overshoot: {over*1e3:.1f}mV")
        print(f"  Undershoot:{under*1e3:.1f}mV")
        print(f"  Result:    {status}")

    print("\n" + "=" * 60)
    all_pass = all(
        results[wl]["V_max"] <= VDDQ_NOM + TOLERANCE and
        results[wl]["V_min"] >= VDDQ_NOM - TOLERANCE
        for wl in results
    )

    if not all_pass:
        print("  [!] Baseline FAILS -- this is expected and correct!")
        print("  The model shows that a single cap cannot meet DDR4 ±60mV tolerance.")
        print("  Proceed to GA optimization (Stage 6).")
    else:
        print("  [OK] Baseline passes (check model -- should fail for rowhammer)")
    print("=" * 60)

    return results


if __name__ == "__main__":
    run_baseline()
