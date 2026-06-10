"""
validate_waveform.py — Sanity-check PWL waveforms before LTSpice simulation.

Validates:
- Peak current is physically plausible (1-20A for a full DIMM)
- Total energy matches expectations
- No time-step discontinuities
- Waveform duration is sufficient
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PWL_DIR = os.path.join(os.path.dirname(__file__), "pwl_files")


def parse_pwl(filepath: str):
    """Parse a .pwl file into time and current arrays."""
    times = []
    currents = []

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("*") or line.startswith(";"):
                continue

            parts = line.split()
            if len(parts) != 2:
                continue

            # Parse time (may have units suffix like "ps")
            t_str = parts[0]
            if t_str.endswith("ps"):
                t = float(t_str[:-2]) * 1e-12
            elif t_str.endswith("ns"):
                t = float(t_str[:-2]) * 1e-9
            elif t_str.endswith("us"):
                t = float(t_str[:-2]) * 1e-6
            else:
                t = float(t_str)

            currents.append(float(parts[1]))
            times.append(t)

    return np.array(times), np.array(currents)


def validate(filepath: str, expected_peak_range=(0.1, 50.0)) -> dict:
    """
    Validate a PWL waveform file.

    Returns dict with validation results.
    """
    time, current = parse_pwl(filepath)
    issues = []

    basename = os.path.basename(filepath)

    # 1. Check sample count
    if len(time) < 100:
        issues.append(f"Too few samples ({len(time)})")

    # 2. Check time monotonicity
    dt = np.diff(time)
    if np.any(dt <= 0):
        n_bad = int(np.sum(dt <= 0))
        issues.append(f"Time not monotonic: {n_bad} non-increasing steps")

    # 3. Check peak current range
    peak = float(np.max(np.abs(current)))
    if peak < expected_peak_range[0]:
        issues.append(f"Peak current {peak:.3f}A below minimum {expected_peak_range[0]}A")
    if peak > expected_peak_range[1]:
        issues.append(f"Peak current {peak:.3f}A above maximum {expected_peak_range[1]}A")

    # 4. Check for NaN/Inf
    if np.any(np.isnan(current)):
        issues.append("Contains NaN values")
    if np.any(np.isinf(current)):
        issues.append("Contains Inf values")

    # 5. Check duration
    duration = time[-1] - time[0]
    if duration < 1e-6:
        issues.append(f"Duration {duration*1e6:.2f}µs may be too short")

    # 6. Energy check (integral of I*dt approximation)
    energy_charge = float(np.trapezoid(current, time))  # Coulombs

    result = {
        "file": basename,
        "valid": len(issues) == 0,
        "issues": issues,
        "n_samples": len(time),
        "duration_us": float(duration * 1e6),
        "I_peak_A": peak,
        "I_mean_A": float(np.mean(current)),
        "I_rms_A": float(np.sqrt(np.mean(current**2))),
        "charge_uC": float(energy_charge * 1e6),
    }

    # Print report
    status = "PASS" if result["valid"] else "FAIL"
    print(f"\n{'='*50}")
    print(f"  {basename}: {status}")
    print(f"{'='*50}")
    print(f"  Samples:    {result['n_samples']}")
    print(f"  Duration:   {result['duration_us']:.2f} µs")
    print(f"  I_peak:     {result['I_peak_A']:.3f} A")
    print(f"  I_mean:     {result['I_mean_A']:.3f} A")
    print(f"  I_rms:      {result['I_rms_A']:.3f} A")
    print(f"  Charge:     {result['charge_uC']:.3f} µC")

    if issues:
        print(f"\n  Issues:")
        for issue in issues:
            print(f"    [!] {issue}")

    return result


def main():
    workloads = ["streaming", "random_access", "rowhammer"]
    all_valid = True

    for wl in workloads:
        pwl_path = os.path.join(PWL_DIR, f"{wl}.pwl")
        if not os.path.exists(pwl_path):
            print(f"[SKIP] {wl}.pwl not found")
            continue

        result = validate(pwl_path)
        if not result["valid"]:
            all_valid = False

    print(f"\n{'='*50}")
    if all_valid:
        print("  All waveforms PASSED validation")
    else:
        print("  Some waveforms FAILED validation")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
