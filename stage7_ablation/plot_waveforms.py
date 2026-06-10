import os
import pickle
import matplotlib.pyplot as plt
import numpy as np

ABLATION_DIR = os.path.join(os.path.dirname(__file__), "ablation_results")

VDDQ_NOM  = 1.2
VDDQ_HIGH = 1.26
VDDQ_LOW  = 1.14


def _save(fig, filename):
    path = os.path.join(ABLATION_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Plot saved: {path}")


# ---------------------------------------------------------------------------
# 1. waveform_comparison.png  (No Decoupling / Baseline / GA Optimised)
# ---------------------------------------------------------------------------

def plot_comparison():
    with open(os.path.join(ABLATION_DIR, "ablation_data.pkl"), "rb") as f:
        results = pickle.load(f)

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = {"No_Decoupling": "red", "Baseline_Single": "orange", "GA_Optimized": "green"}

    for name, data in results.items():
        t  = (data['tran']['time'] - 0.7e-3) * 1e6
        vd = data['tran']['vddq']
        ax.plot(t, vd, label=name.replace("_", " "), color=colors.get(name, "blue"), alpha=0.85)

    ax.axhline(VDDQ_NOM,  color='black', linewidth=0.8)
    ax.axhline(VDDQ_HIGH, color='red',   linestyle='--', alpha=0.5, label='JEDEC Limit')
    ax.axhline(VDDQ_LOW,  color='red',   linestyle='--', alpha=0.5)
    ax.set_title("Transient VDDQ Response (Rowhammer) — Design Comparison", fontsize=14)
    ax.set_xlabel("Time (µs)", fontsize=12)
    ax.set_ylabel("Voltage (V)", fontsize=12)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    _save(fig, "waveform_comparison.png")


# ---------------------------------------------------------------------------
# 2. waveform_baseline_vs_optimised.png  (side-by-side VDDQ + VTT)
# ---------------------------------------------------------------------------

def plot_baseline_vs_optimised():
    with open(os.path.join(ABLATION_DIR, "ablation_data.pkl"), "rb") as f:
        results = pickle.load(f)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)
    styles = {
        "No_Decoupling":  ("red",    "--", 0.7),
        "Baseline_Single":("orange", "-",  0.8),
        "GA_Optimized":   ("green",  "-",  1.0),
    }

    for name, data in results.items():
        t   = (data['tran']['time'] - 0.7e-3) * 1e6
        col, ls, alpha = styles.get(name, ("blue", "-", 0.8))
        axes[0].plot(t, data['tran']['vddq'], label=name.replace("_", " "),
                     color=col, linestyle=ls, alpha=alpha, linewidth=1.5)
        axes[1].plot(t, data['tran']['vtt'],  label=name.replace("_", " "),
                     color=col, linestyle=ls, alpha=alpha, linewidth=1.5)

    for ax, rail, nom, tol in [
        (axes[0], "VDDQ", 1.20, 0.060),
        (axes[1], "VTT",  0.60, 0.040),
    ]:
        ax.axhline(nom,       color='black', linewidth=0.8)
        ax.axhline(nom + tol, color='red', linestyle='--', alpha=0.5, label='JEDEC Limit')
        ax.axhline(nom - tol, color='red', linestyle='--', alpha=0.5)
        ax.set_title(f"{rail} — Baseline vs GA Optimised", fontsize=13)
        ax.set_xlabel("Time (µs)", fontsize=11)
        ax.set_ylabel("Voltage (V)", fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Rowhammer Transient Response: Both Rails", fontsize=14, fontweight='bold')
    fig.tight_layout()
    _save(fig, "waveform_baseline_vs_optimised.png")


# ---------------------------------------------------------------------------
# 3. waveform_all_workloads.png  (GA optimised across streaming/random/rowhammer)
# ---------------------------------------------------------------------------

def plot_all_workloads():
    pkl = os.path.join(ABLATION_DIR, "workload_waveforms.pkl")
    if not os.path.exists(pkl):
        print(f"[SKIP] {pkl} not found — run run_ablation.py first")
        return

    with open(pkl, "rb") as f:
        data = pickle.load(f)

    colors = {"streaming": "#1f77b4", "random_access": "#ff7f0e", "rowhammer": "#2ca02c"}

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)

    for workload, tran in data.items():
        t   = (tran['time'] - 0.7e-3) * 1e6
        lbl = workload.replace("_", " ").title()
        col = colors.get(workload, "blue")
        axes[0].plot(t, tran['vddq'], label=lbl, color=col, alpha=0.85, linewidth=1.3)
        axes[1].plot(t, tran['vtt'],  label=lbl, color=col, alpha=0.85, linewidth=1.3)

    for ax, rail, nom, tol in [
        (axes[0], "VDDQ", 1.20, 0.060),
        (axes[1], "VTT",  0.60, 0.040),
    ]:
        ax.axhline(nom,       color='black', linewidth=0.8)
        ax.axhline(nom + tol, color='red', linestyle='--', alpha=0.5, label='JEDEC Limit')
        ax.axhline(nom - tol, color='red', linestyle='--', alpha=0.5)
        ax.set_title(f"{rail} — GA Optimised Network", fontsize=13)
        ax.set_xlabel("Time (µs)", fontsize=11)
        ax.set_ylabel("Voltage (V)", fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle("All Workloads: GA Optimised Decoupling Network", fontsize=14, fontweight='bold')
    fig.tight_layout()
    _save(fig, "waveform_all_workloads.png")


if __name__ == "__main__":
    plot_comparison()
    plot_baseline_vs_optimised()
    plot_all_workloads()
