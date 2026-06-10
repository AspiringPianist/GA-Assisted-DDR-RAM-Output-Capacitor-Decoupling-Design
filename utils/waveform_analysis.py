"""
Waveform analysis utilities for DDR4 PDN Optimizer.

Provides violation counting, worst-case extraction, and waveform statistics.
"""

import numpy as np
from typing import Dict, Optional, Tuple


def count_violations(time, voltage, nominal_v, tolerance_v):
    """
    Count voltage rail violations.

    Returns dict with violation stats: count, duration, worst overshoot/undershoot.
    """
    v_max = nominal_v + tolerance_v
    v_min = nominal_v - tolerance_v

    over_mask = voltage > v_max
    under_mask = voltage < v_min
    violation_mask = over_mask | under_mask

    n_over = int(np.sum(over_mask))
    n_under = int(np.sum(under_mask))
    n_total = int(np.sum(violation_mask))

    worst_overshoot = float(np.max(voltage) - v_max) if n_over > 0 else 0.0
    worst_undershoot = float(v_min - np.min(voltage)) if n_under > 0 else 0.0

    # Estimate violation duration
    if n_total > 0 and len(time) > 1:
        dt = np.mean(np.diff(time))
        violation_duration_s = n_total * dt
    else:
        violation_duration_s = 0.0

    return {
        "n_overshoot": n_over,
        "n_undershoot": n_under,
        "n_total": n_total,
        "worst_overshoot_v": worst_overshoot,
        "worst_undershoot_v": worst_undershoot,
        "violation_duration_s": violation_duration_s,
        "v_max_observed": float(np.max(voltage)),
        "v_min_observed": float(np.min(voltage)),
        "v_mean": float(np.mean(voltage)),
        "v_pk_pk": float(np.max(voltage) - np.min(voltage)),
        "pass": n_total == 0,
    }


def extract_worst_case(time, voltage, nominal_v, tolerance_v):
    """
    Extract worst-case voltage excursion details.

    Returns dict with worst-case timestamps and magnitudes.
    """
    v_max = nominal_v + tolerance_v
    v_min = nominal_v - tolerance_v

    idx_max = np.argmax(voltage)
    idx_min = np.argmin(voltage)

    return {
        "worst_high": {
            "time_s": float(time[idx_max]),
            "voltage_v": float(voltage[idx_max]),
            "margin_v": float(v_max - voltage[idx_max]),
        },
        "worst_low": {
            "time_s": float(time[idx_min]),
            "voltage_v": float(voltage[idx_min]),
            "margin_v": float(voltage[idx_min] - v_min),
        },
    }


def waveform_energy(time, current):
    """Compute total energy (integral of I^2 * dt) from current waveform."""
    # Assume resistive load of 1 ohm for relative comparison
    dt = np.diff(time)
    i_mid = (current[:-1] + current[1:]) / 2.0
    return float(np.sum(i_mid**2 * dt))


def waveform_statistics(time, current):
    """Compute statistics for a current waveform."""
    return {
        "peak_a": float(np.max(current)),
        "min_a": float(np.min(current)),
        "mean_a": float(np.mean(current)),
        "rms_a": float(np.sqrt(np.mean(current**2))),
        "pk_pk_a": float(np.max(current) - np.min(current)),
        "duration_s": float(time[-1] - time[0]),
        "n_samples": len(time),
    }


def validate_pwl_waveform(time, current, expected_peak_range=(0.1, 50.0)):
    """
    Sanity-check a PWL waveform before feeding to LTSpice.

    Returns dict with validation status and issues found.
    """
    issues = []

    # Check monotonicity of time
    dt = np.diff(time)
    if np.any(dt <= 0):
        issues.append("Time is not strictly monotonically increasing")

    # Check peak current range
    peak = np.max(np.abs(current))
    if peak < expected_peak_range[0]:
        issues.append(f"Peak current {peak:.3f}A below expected minimum "
                      f"{expected_peak_range[0]}A")
    if peak > expected_peak_range[1]:
        issues.append(f"Peak current {peak:.3f}A above expected maximum "
                      f"{expected_peak_range[1]}A")

    # Check for NaN/Inf
    if np.any(np.isnan(current)) or np.any(np.isinf(current)):
        issues.append("Waveform contains NaN or Inf values")

    if np.any(np.isnan(time)) or np.any(np.isinf(time)):
        issues.append("Time array contains NaN or Inf values")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "stats": waveform_statistics(time, current),
    }
