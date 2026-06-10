import os
import subprocess
import numpy as np
from PyLTSpice.raw.raw_read import RawRead
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stage5_ltspice.ltspice_interface import run_simulation
from stage6_ga.chromosome import CAP_LIBRARY

# Define Baseline Network (1x 10uF Decoupling for each rail)
# Library index 0 is 10uF 0402
baseline_params = {
    "vddq_network": [1, 0, 0, 0, 0, 0, 0, 0],
    "vtt_network": [1, 0, 0, 0, 0, 0, 0, 0],
    "library": CAP_LIBRARY
}

print("=" * 70)
print("  DDR4 PDN Commercial Baseline (Multi-Capacitor Model)")
print("=" * 70)

# 1. Run Transient Analysis
print("\nRunning Transient Analysis (Rowhammer)...")
res_tran = run_simulation(baseline_params, "stage4_converter/pwl_files/rowhammer.pwl", 'tran')

# 2. Run AC Analysis
print("Running AC Analysis (Impedance Spectrum)...")
res_ac = run_simulation(baseline_params, None, 'ac')

# Performance Targets
VDDQ_LIMIT = 60.0  # mV
VTT_LIMIT = 40.0   # mV
Z_LIMIT = 50.0     # mOhm

# Output Results
print("\n=== Baseline Results ===")
vddq_rip = (res_tran['V_max'] - res_tran['V_min']) * 1e3
vtt_rip = (res_tran['VTT_max'] - res_tran['VTT_min']) * 1e3

print(f"VDDQ Ripple: {vddq_rip:.1f}mV", end=" ")
if vddq_rip > VDDQ_LIMIT:
    print(f"--> [FAIL] (Limit: {VDDQ_LIMIT}mV)")
else:
    print(f"--> [PASS]")

print(f"VTT Ripple:  {vtt_rip:.1f}mV", end=" ")
if vtt_rip > VTT_LIMIT:
    print(f"--> [FAIL] (Limit: {VTT_LIMIT}mV)")
else:
    print(f"--> [PASS]")

# Anti-Resonance Check (up to 200MHz)
freq = res_ac['freq']
mask = freq < 200e6
z_peak = np.max(res_ac['z_vddq'][mask]) * 1000
print(f"VDDQ Peak Impedance: {z_peak:.1f}mOhm", end=" ")
if z_peak > Z_LIMIT:
    print(f"--> [FAIL] (Limit: {Z_LIMIT}mOhm)")
else:
    print(f"--> [PASS]")

print("\n" + "="*70)
if vddq_rip > VDDQ_LIMIT or z_peak > Z_LIMIT:
    print("  OVERALL STATUS: NON-COMPLIANT")
    print("  The baseline capacitor network is insufficient for Rowhammer loads.")
else:
    print("  OVERALL STATUS: COMPLIANT")
print("="*70)
