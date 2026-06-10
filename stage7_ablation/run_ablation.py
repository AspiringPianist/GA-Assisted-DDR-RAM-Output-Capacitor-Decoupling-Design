import os
import copy
import json
import pickle
import numpy as np
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stage5_ltspice.ltspice_interface import run_simulation
from stage6_ga.chromosome import CAP_LIBRARY, CapNetwork

ABLATION_DIR = os.path.join(os.path.dirname(__file__), "ablation_results")
os.makedirs(ABLATION_DIR, exist_ok=True)

VDDQ_TARGET = 1.2
VDDQ_TOL    = 0.060
VTT_TARGET  = 0.6
VTT_TOL     = 0.040


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_best_network():
    pkl = os.path.join(os.path.dirname(__file__), "..", "stage6_ga", "ga_results", "best_network.pkl")
    if os.path.exists(pkl):
        with open(pkl, "rb") as f:
            net = pickle.load(f)
        print(f"[OK] Loaded GA network — VDDQ {sum(net.vddq_counts)} caps, VTT {sum(net.vtt_counts)} caps")
        return net
    print("[WARN] best_network.pkl not found — using hand-designed seed as fallback")
    return CapNetwork(
        vddq_counts=[7, 6, 10, 8, 3, 8, 4, 4],
        vtt_counts= [4, 3,  7, 4, 2, 5, 2, 3],
    )


def tran_metrics(params, pwl_file):
    """Run one transient sim and return summary dict."""
    res = run_simulation(params, pwl_file, analysis_type='tran')
    vddq = res['vddq']
    v_max = float(vddq.max())
    v_min = float(vddq.min())
    return {
        "V_max":          v_max,
        "V_min":          v_min,
        "overshoot_mV":   (v_max - VDDQ_TARGET) * 1e3,
        "undershoot_mV":  (VDDQ_TARGET - v_min) * 1e3,
        "ripple_mV":      (v_max - v_min) * 1e3,
        "pass":           bool(
            abs(v_max - VDDQ_TARGET) <= VDDQ_TOL and
            abs(VDDQ_TARGET - v_min) <= VDDQ_TOL
        ),
    }


def with_via_inductance(params, extra_L):
    """Return params copy where every cap's ESL has extra_L added (series via inductance)."""
    p = copy.deepcopy(params)
    p['library'] = [dict(c, ESL=c['ESL'] + extra_L) for c in p['library']]
    return p


def with_scaled_esr(params, esr_value):
    """Return params copy where every cap's ESR is overridden to esr_value."""
    p = copy.deepcopy(params)
    p['library'] = [dict(c, ESR=esr_value) for c in p['library']]
    return p


def save_json(name, data):
    path = os.path.join(ABLATION_DIR, name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [saved] {path}")


# ---------------------------------------------------------------------------
# Study A — Workload comparison (streaming / random_access / rowhammer)
# ---------------------------------------------------------------------------

def study_a_workload(base_params):
    print("\n--- Study A: Workload Comparison ---")
    pwl_dir = "stage4_converter/pwl_files"
    results = {}
    for workload in ("streaming", "random_access", "rowhammer"):
        pwl = os.path.join(pwl_dir, f"{workload}.pwl")
        print(f"  Simulating {workload}...")
        results[workload] = tran_metrics(base_params, pwl)
    save_json("study_a_workload.json", results)


# ---------------------------------------------------------------------------
# Study B — Via inductance sweep (extra L in series with caps)
# ---------------------------------------------------------------------------

def study_b_via(base_params):
    print("\n--- Study B: Via Inductance Sweep ---")
    # Inductances to add on top of each cap's own ESL
    via_cases = {
        "0.000nH": 0.000e-9,
        "0.300nH": 0.300e-9,
        "0.600nH": 0.600e-9,
        "0.948nH": 0.948e-9,
    }
    pwl = "stage4_converter/pwl_files/rowhammer.pwl"
    results = {}
    for label, extra_L in via_cases.items():
        print(f"  Via inductance = {label}...")
        results[label] = tran_metrics(with_via_inductance(base_params, extra_L), pwl)
    save_json("study_b_via.json", results)


# ---------------------------------------------------------------------------
# Study C — ESR sweep
# ---------------------------------------------------------------------------

def study_c_esr(base_params):
    print("\n--- Study C: ESR Sweep ---")
    esr_cases = {
        "1mOhm":   0.001,
        "5mOhm":   0.005,
        "10mOhm":  0.010,
        "50mOhm":  0.050,
        "100mOhm": 0.100,
    }
    pwl = "stage4_converter/pwl_files/rowhammer.pwl"
    results = {}
    for label, esr in esr_cases.items():
        print(f"  ESR = {label}...")
        results[label] = tran_metrics(with_scaled_esr(base_params, esr), pwl)
    save_json("study_c_esr.json", results)


# ---------------------------------------------------------------------------
# Study D — Topology comparison
# ---------------------------------------------------------------------------

def study_d_topology(base_params):
    print("\n--- Study D: Topology Comparison ---")
    pwl = "stage4_converter/pwl_files/rowhammer.pwl"

    topology_cases = {
        "baseline_single_0603": {
            "vddq_network": [0, 0, 0, 0, 0, 0, 0, 1],  # 1x 10uF 0603
            "vtt_network":  [0, 0, 0, 0, 0, 0, 0, 1],
            "library": CAP_LIBRARY,
        },
        "10x_0402": {
            "vddq_network": [10, 0, 0, 0, 0, 0, 0, 0],  # 10x 10uF 0402
            "vtt_network":  [5,  0, 0, 0, 0, 0, 0, 0],
            "library": CAP_LIBRARY,
        },
        "20x_0201": {
            "vddq_network": [0, 0, 20, 0, 0, 0, 0, 0],  # 20x 100nF 0201
            "vtt_network":  [0, 0, 10, 0, 0, 0, 0, 0],
            "library": CAP_LIBRARY,
        },
        "ga_optimised": base_params,
    }

    results = {}
    for label, params in topology_cases.items():
        print(f"  Topology = {label}...")
        results[label] = tran_metrics(params, pwl)
    save_json("study_d_topology.json", results)


# ---------------------------------------------------------------------------
# Main ablation data (used by plot_waveforms.py)
# ---------------------------------------------------------------------------

def main_ablation_pkl(best_net):
    print("\n--- Main ablation PKL (No_Decoupling / Baseline_Single / GA_Optimized) ---")
    pwl = "stage4_converter/pwl_files/rowhammer.pwl"
    cases = {
        "No_Decoupling": {
            "vddq_network": [0] * 8,
            "vtt_network":  [0] * 8,
            "library": CAP_LIBRARY,
        },
        "Baseline_Single": {
            "vddq_network": [1, 0, 0, 0, 0, 0, 0, 0],
            "vtt_network":  [1, 0, 0, 0, 0, 0, 0, 0],
            "library": CAP_LIBRARY,
        },
        "GA_Optimized": best_net.get_params(),
    }
    results = {}
    for name, params in cases.items():
        print(f"  Simulating {name}...")
        results[name] = {
            "tran": run_simulation(params, pwl, 'tran'),
            "ac":   run_simulation(params, None, 'ac'),
        }
    pkl_path = os.path.join(ABLATION_DIR, "ablation_data.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(results, f)
    print(f"  [saved] {pkl_path}")


# ---------------------------------------------------------------------------
# Extra PKL: full waveform data for each workload (used by plot_waveforms.py)
# ---------------------------------------------------------------------------

def workload_waveforms_pkl(base_params):
    print("\n--- Workload waveforms PKL (streaming / random_access / rowhammer) ---")
    pwl_dir = "stage4_converter/pwl_files"
    data = {}
    for workload in ("streaming", "random_access", "rowhammer"):
        print(f"  Simulating {workload}...")
        data[workload] = run_simulation(
            base_params, os.path.join(pwl_dir, f"{workload}.pwl"), 'tran'
        )
    pkl_path = os.path.join(ABLATION_DIR, "workload_waveforms.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(data, f)
    print(f"  [saved] {pkl_path}")


# ---------------------------------------------------------------------------
# Extra PKL: AC impedance for each via inductance (used by plot_impedance.py)
# ---------------------------------------------------------------------------

def via_impedance_pkl(base_params):
    print("\n--- Via impedance PKL (AC sweep per inductance value) ---")
    via_cases = {
        "0.000 nH": 0.000e-9,
        "0.300 nH": 0.300e-9,
        "0.600 nH": 0.600e-9,
        "0.948 nH": 0.948e-9,
    }
    data = {}
    for label, extra_L in via_cases.items():
        print(f"  Via inductance = {label}...")
        data[label] = run_simulation(with_via_inductance(base_params, extra_L), None, 'ac')
    pkl_path = os.path.join(ABLATION_DIR, "via_impedance.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(data, f)
    print(f"  [saved] {pkl_path}")


# ---------------------------------------------------------------------------

def run_study():
    print("=" * 70)
    print("  DDR4 PDN Ablation Study — All Studies")
    print("=" * 70)

    best_net    = load_best_network()
    base_params = best_net.get_params()

    study_a_workload(base_params)
    study_b_via(base_params)
    study_c_esr(base_params)
    study_d_topology(base_params)
    main_ablation_pkl(best_net)
    workload_waveforms_pkl(base_params)
    via_impedance_pkl(base_params)

    print("\n[DONE] All ablation studies complete.")


if __name__ == "__main__":
    run_study()
