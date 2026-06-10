"""
convert_to_pwl.py — Convert DRAMPower current waveforms to LTSpice PWL format.
Includes 0.7ms startup delay and 10x looping for steady-state analysis.
"""

import os
import sys
import pandas as pd
import yaml

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WAVEFORM_DIR = os.path.join(PROJECT_ROOT, "stage3_drampower", "current_waveforms")
PWL_DIR = os.path.join(os.path.dirname(__file__), "pwl_files")

# Stabilization delay for LTM4632 (match our measurement window)
STARTUP_DELAY_PS = 0.7e-3 * 1e12  # 0.7ms in ps
N_REPEATS = 15                   # Repeat 10us trace 15 times to cover 150us window

def convert(workload: str, config: dict) -> str:
    csv_path = os.path.join(WAVEFORM_DIR, f"{workload}_It.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Current waveform not found: {csv_path}")

    df = pd.read_csv(csv_path)

    n_chips = config["ddr4"]["chips_per_dimm"]
    simultaneity = config["ddr4"]["max_simultaneous_nets"]
    idc_per_net = config["ddr4"]["vddq_v"] / config["ddr4"]["odt_ohm"]

    # Scale: per-chip → system level + ODT termination
    df["I_A"] = (df["current_mA"] / 1000.0 * n_chips) + (idc_per_net * simultaneity)
    
    mean_vddq_variation = df["current_mA"] / 1000.0 * n_chips
    mean_val = mean_vddq_variation.mean()
    df["I_VTT_A"] = (mean_vddq_variation - mean_val) * 0.15

    os.makedirs(PWL_DIR, exist_ok=True)
    pwl_path = os.path.join(PWL_DIR, f"{workload}.pwl")
    vtt_pwl_path = os.path.join(PWL_DIR, f"{workload}_vtt.pwl")

    duration_ps = df['time_ps'].iloc[-1]

    with open(pwl_path, "w") as f_vddq, open(vtt_pwl_path, "w") as f_vtt:
        # 1. Initial zero current during startup delay
        f_vddq.write(f"0ps 0.0\n")
        f_vddq.write(f"{STARTUP_DELAY_PS - 1}ps 0.0\n")
        f_vtt.write(f"0ps 0.0\n")
        f_vtt.write(f"{STARTUP_DELAY_PS - 1}ps 0.0\n")

        # 2. Repeated workload bursts
        for r in range(N_REPEATS):
            offset = STARTUP_DELAY_PS + (r * duration_ps)
            for _, row in df.iterrows():
                t = offset + row['time_ps']
                f_vddq.write(f"{t:.1f}ps {row['I_A']:.6f}\n")
                f_vtt.write(f"{t:.1f}ps {row['I_VTT_A']:.6f}\n")

    print(f"[OK] {workload}: Delayed to 0.7ms and looped {N_REPEATS}x")
    return pwl_path

def main():
    config_path = os.path.join(PROJECT_ROOT, "config", "ddr4_params.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    workloads = ["streaming", "random_access", "rowhammer"]
    for wl in workloads:
        try:
            convert(wl, config)
        except Exception as e:
            print(f"[ERR] {wl}: {e}")

if __name__ == "__main__":
    main()
