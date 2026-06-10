import os
import pickle
import matplotlib.pyplot as plt
import numpy as np
import yaml

ABLATION_DIR = os.path.join(os.path.dirname(__file__), "ablation_results")

# load DDR timing from project config
CFG_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config", "ddr4_params.yaml"))
try:
    with open(CFG_PATH, 'r') as cf:
        cfg = yaml.safe_load(cf)
        CLOCK_MHZ = float(cfg.get('ddr4', {}).get('clock_mhz', 1600))
except Exception:
    CLOCK_MHZ = 1600.0

# frequencies to mark (Hz)
CLOCK_HZ = CLOCK_MHZ * 1e6
DDR_HZ = CLOCK_HZ * 2.0


def _save(fig, filename):
    path = os.path.join(ABLATION_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Plot saved: {path}")


# ---------------------------------------------------------------------------
# 1. impedance_comparison.png  (No Decoupling / Baseline / GA Optimised)
# ---------------------------------------------------------------------------

def plot_comparison():
    with open(os.path.join(ABLATION_DIR, "ablation_data.pkl"), "rb") as f:
        results = pickle.load(f)

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = {"No_Decoupling": "red", "Baseline_Single": "orange", "GA_Optimized": "green"}

    for name, data in results.items():
        freq = np.real(data['ac']['freq'])
        z    = np.abs(data['ac']['z_vddq'])
        ax.loglog(freq, z, label=name.replace("_", " "),
                  color=colors.get(name, "blue"), linewidth=2)
        # collect z for autoscaling
        try:
            z_vals
        except NameError:
            z_vals = []
        z_vals.append(z)

    ax.axhline(0.050, color='black', linestyle='--', alpha=0.6, label='Target (50 mΩ)')
    ax.set_title("VDDQ PDN Impedance Spectrum Comparison", fontsize=14)
    ax.set_xlabel("Frequency (Hz)", fontsize=12)
    ax.set_ylabel("Impedance (Ω)", fontsize=12)
    ax.grid(True, which="both", ls="-", alpha=0.2)
    ax.legend(fontsize=11)
    # extend x-axis to include DDR harmonics (clock and DDR rate)
    x_upper = max(1e9, DDR_HZ * 1.1)
    ax.set_xlim(1e3, x_upper)
    # determine y-limits from data to avoid clipping (apply margin in log space)
    if 'z_vals' in globals() and len(z_vals) > 0:
        all_z = np.concatenate(z_vals)
        zmin = np.min(all_z[np.where(all_z > 0)]) if np.any(all_z > 0) else 1e-6
        zmax = np.max(all_z)
        lower = max(zmin / 10.0, 1e-12)
        upper = max(zmax * 10.0, lower * 10.0)
        ax.set_ylim(lower, upper)
    else:
        ax.set_ylim(1e-6, 10)

    # add vertical markers for clock and DDR rates
    ylim = ax.get_ylim()
    y_annot = ylim[1] / 1.8
    ax.axvline(CLOCK_HZ, color='purple', linestyle='--', linewidth=1.2, label=f'Clock ({CLOCK_MHZ:.0f} MHz)')
    ax.text(CLOCK_HZ * 1.02, y_annot, f'{CLOCK_MHZ:.0f} MHz', color='purple', fontsize=9, rotation=90, va='bottom')
    ax.axvline(DDR_HZ, color='magenta', linestyle=':', linewidth=1.2, label=f'DDR ({CLOCK_MHZ*2:.0f} MHz)')
    ax.text(DDR_HZ * 1.02, y_annot, f'{CLOCK_MHZ*2:.0f} MHz', color='magenta', fontsize=9, rotation=90, va='bottom')
    _save(fig, "impedance_comparison.png")


# ---------------------------------------------------------------------------
# 2. impedance_via_sweep.png  (GA network + increasing via inductance)
# ---------------------------------------------------------------------------

def plot_via_sweep():
    pkl = os.path.join(ABLATION_DIR, "via_impedance.pkl")
    if not os.path.exists(pkl):
        print(f"[SKIP] {pkl} not found — run run_ablation.py first")
        return

    with open(pkl, "rb") as f:
        data = pickle.load(f)

    cmap   = plt.cm.Blues
    labels = list(data.keys())
    colors = [cmap(0.35 + 0.65 * i / max(len(labels) - 1, 1)) for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(12, 7))
    z_vals = []
    for (label, ac), color in zip(data.items(), colors):
        freq = np.real(ac['freq'])
        z    = np.abs(ac['z_vddq'])
        ax.loglog(freq, z, label=f"Via L = {label}", color=color, linewidth=2)
        z_vals.append(z)

    ax.axhline(0.050, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label='Target (50 mΩ)')
    ax.set_title("Effect of Via Inductance on VDDQ PDN Impedance (GA Optimised Network)", fontsize=13)
    ax.set_xlabel("Frequency (Hz)", fontsize=12)
    ax.set_ylabel("Impedance (Ω)", fontsize=12)
    ax.grid(True, which="both", ls="-", alpha=0.2)
    ax.legend(fontsize=11)
    # extend x-axis to include DDR harmonics (clock and DDR rate)
    x_upper = max(1e9, DDR_HZ * 1.1)
    ax.set_xlim(1e3, x_upper)
    # autoscale y-limits from plotted data
    if len(z_vals) > 0:
        all_z = np.concatenate(z_vals)
        all_z_pos = all_z[all_z > 0]
        zmin = np.min(all_z_pos) if all_z_pos.size > 0 else 1e-6
        zmax = np.max(all_z)
        lower = max(zmin / 10.0, 1e-12)
        upper = max(zmax * 10.0, lower * 10.0)
        ax.set_ylim(lower, upper)
    else:
        ax.set_ylim(1e-6, 10)
    # add vertical markers for clock and DDR rates
    ylim = ax.get_ylim()
    y_annot = ylim[1] / 1.8
    ax.axvline(CLOCK_HZ, color='purple', linestyle='--', linewidth=1.2, label=f'Clock ({CLOCK_MHZ:.0f} MHz)')
    ax.text(CLOCK_HZ * 1.02, y_annot, f'{CLOCK_MHZ:.0f} MHz', color='purple', fontsize=9, rotation=90, va='bottom')
    ax.axvline(DDR_HZ, color='magenta', linestyle=':', linewidth=1.2, label=f'DDR ({CLOCK_MHZ*2:.0f} MHz)')
    ax.text(DDR_HZ * 1.02, y_annot, f'{CLOCK_MHZ*2:.0f} MHz', color='magenta', fontsize=9, rotation=90, va='bottom')
    _save(fig, "impedance_via_sweep.png")


if __name__ == "__main__":
    plot_comparison()
    plot_via_sweep()
