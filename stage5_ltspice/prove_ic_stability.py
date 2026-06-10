import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stage5_ltspice.ltspice_interface import run_simulation
from stage6_ga.chromosome import CAP_LIBRARY

# Define a "Network" for the test (1x 10uF Decoupling baseline)
test_params = {
    "vddq_network": [1, 0, 0, 0, 0, 0, 0, 0],
    "vtt_network": [1, 0, 0, 0, 0, 0, 0, 0],
    "library": CAP_LIBRARY
}

print("=" * 70)
print("  DDR4 PDN Steady-State & Ripple Analysis (High-Fidelity)")
print("=" * 70)

# 1. Run 0.8ms simulation (Workload starts at 0.7ms, we start capture at 0.6ms)
print("Running simulation (0.8ms)...")
pbar = tqdm(total=1, desc="LTSpice Simulation")
res = run_simulation(test_params, "stage4_converter/pwl_files/rowhammer.pwl", 'tran', start_time=0.6e-3)
pbar.update(1)
pbar.close()

# 2. Extract results (Slicing 0.6ms to 0.8ms)
time = (res['time'] - 0.7e-3) * 1e6 # 0us is the workload start
vddq = res['vddq']

# 3. Calculate Ripple
ripple_mv = (np.max(vddq) - np.min(vddq)) * 1000

# 4. Create Detailed Plot
plt.figure(figsize=(10, 6))
plt.plot(time, vddq, color='blue', linewidth=1, label='VDDQ (1.2V)')
plt.axhline(y=1.26, color='red', linestyle='--', alpha=0.5, label='JEDEC Max (+60mV)')
plt.axhline(y=1.14, color='red', linestyle='--', alpha=0.5, label='JEDEC Min (-60mV)')
plt.axhline(y=1.20, color='black', linestyle='-', alpha=0.3)

plt.title(f"DDR4 VDDQ Steady-State Ripple (Rowhammer Load)\nMeasured Ripple: {ripple_mv:.1f} mV", fontsize=14)
plt.xlabel("Time after Workload Start (us)", fontsize=12)
plt.ylabel("Voltage (V)", fontsize=12)
plt.grid(True, alpha=0.3)
plt.legend(loc='upper right')
plt.ylim(1.10, 1.30)

output_plot = 'stage5_ltspice/sim_results/steady_state_analysis.png'
os.makedirs(os.path.dirname(output_plot), exist_ok=True)
plt.savefig(output_plot, dpi=150)
plt.close()

print(f"\n[OK] Analysis complete!")
print(f"Measured Ripple: {ripple_mv:.1f} mV")
print(f"Plot saved to:   {output_plot}")
