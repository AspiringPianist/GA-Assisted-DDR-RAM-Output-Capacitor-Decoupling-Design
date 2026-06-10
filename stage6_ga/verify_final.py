import os
import pickle
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stage5_ltspice.ltspice_interface import run_simulation
from stage6_ga.fitness import evaluate_detailed

def report_best():
    best_pkl = "stage6_ga/ga_results/best_network.pkl"
    if not os.path.exists(best_pkl):
        print(f"[ERR] Best network pkl not found at {best_pkl}")
        return

    with open(best_pkl, "rb") as f:
        best_net = pickle.load(f)

    print("=" * 70)
    print("  FINAL OPTIMIZED NETWORK REPORT")
    print("=" * 70)
    print(best_net.summary())
    
    print("\nRunning High-Fidelity Verification Simulation...")
    detailed = evaluate_detailed(best_net, run_simulation)
    
    print("\n=== PERFORMANCE METRICS ===")
    for rail in ["VDDQ", "VTT"]:
        res = detailed[rail]
        print(f"  {rail}:")
        print(f"    Voltage Range:  {res['V_min']:.4f}V to {res['V_max']:.4f}V")
        print(f"    Voltage Ripple: {res['ripple_mV']:.2f} mV")
        print(f"    Peak Impedance: {res['Z_peak_mOhm']:.2f} mOhm")
        
        # Check against targets
        target_rip = 60.0 if rail == "VDDQ" else 40.0
        if res['ripple_mV'] < target_rip:
            print(f"    [PASS] Ripple within {target_rip}mV limit.")
        else:
            print(f"    [FAIL] Ripple exceeds {target_rip}mV limit!")

if __name__ == "__main__":
    report_best()
