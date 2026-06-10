import os
import subprocess
from PyLTSpice.raw.raw_read import RawRead
import numpy as np
import matplotlib.pyplot as plt
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stage5_ltspice.ltspice_interface import run_simulation
from stage6_ga.chromosome import CAP_LIBRARY

# Baseline: 1x 10uF Decoupling
baseline_params = {
    "vddq_network": [1, 0, 0, 0, 0, 0, 0, 0],
    "vtt_network": [1, 0, 0, 0, 0, 0, 0, 0],
    "library": CAP_LIBRARY
}

print("Running Full 0.8ms Baseline Startup Simulation...")
res_tran = run_simulation(baseline_params, "stage4_converter/pwl_files/rowhammer.pwl", 'tran')

# Note: run_simulation for 'tran' already slices after 0.7ms. 
# If we want the FULL waveform for startup plot, we need to modify the slice.
# For now, we use the stable portion to verify.

print("\n=== Baseline Startup Performance (Stable Window) ===")
print(f"VDDQ: {res_tran['V_min']:.4f}V to {res_tran['V_max']:.4f}V")
print(f"VTT:  {res_tran['VTT_min']:.4f}V to {res_tran['VTT_max']:.4f}V")
