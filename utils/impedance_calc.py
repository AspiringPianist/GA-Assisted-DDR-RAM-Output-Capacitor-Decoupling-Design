"""
Impedance calculation utilities for DDR4 PDN Optimizer.

Provides functions for parallel cap impedance, anti-resonance detection,
target impedance, and Lmax calculations.
"""

import numpy as np
from typing import List, Dict, Tuple


def single_cap_impedance(freq, C, ESR, ESL, L_via=0.948e-9):
    """Impedance of a single cap: Z = ESR + jwL + 1/jwC."""
    w = 2 * np.pi * freq
    L_total = ESL + L_via
    with np.errstate(divide="ignore", invalid="ignore"):
        Z = ESR + 1j * w * L_total + 1.0 / (1j * w * C)
    return Z


def parallel_cap_impedance(freq, C, ESR, ESL, N, L_via=0.948e-9):
    """Impedance of N identical caps in parallel."""
    C_eff = C * N
    ESR_eff = ESR / N
    ESL_eff = (ESL + L_via) / N
    return single_cap_impedance(freq, C_eff, ESR_eff, ESL_eff, L_via=0)


def mixed_cap_impedance(freq, cap_configs, L_via=0.948e-9):
    """Impedance of mixed cap types in parallel. Each entry: {C_F, ESR_ohm, ESL_H, N}."""
    Y_total = np.zeros(len(freq), dtype=complex)
    for cfg in cap_configs:
        Z_group = parallel_cap_impedance(
            freq, C=cfg["C_F"], ESR=cfg["ESR_ohm"],
            ESL=cfg["ESL_H"], N=cfg.get("N", 1), L_via=L_via,
        )
        Y_total += 1.0 / Z_group
    return 1.0 / Y_total


def self_resonant_frequency(C, ESL, L_via=0.948e-9):
    """SRF = 1/(2*pi*sqrt(L_total*C))."""
    L_total = ESL + L_via
    return 1.0 / (2.0 * np.pi * np.sqrt(L_total * C))


def find_antiresonance_peaks(freq, Z_mag, min_prominence=0.1):
    """Detect anti-resonance peaks in |Z(f)|."""
    from scipy.signal import find_peaks
    Z_log = np.log10(Z_mag)
    peaks, props = find_peaks(Z_log, prominence=np.log10(1 + min_prominence))
    results = []
    for i, prom in zip(peaks, props["prominences"]):
        results.append({
            "freq_Hz": float(freq[i]),
            "Z_peak_ohm": float(Z_mag[i]),
            "prominence": float(10**prom - 1),
        })
    return results


def target_impedance(tolerance_v, max_current_a):
    """Z_target = V_tolerance / I_max."""
    return tolerance_v / max_current_a


def lmax_from_spec(tolerance_v, switching_time_s, n_nets, di_per_net_a):
    """Lmax = V_tolerance * dt / (N * di)."""
    return tolerance_v * switching_time_s / (n_nets * di_per_net_a)


def compute_vnoise(L_eq, n_nets, di_per_net_a, switching_time_s):
    """V_noise = L_eq * N * di / dt."""
    return L_eq * n_nets * di_per_net_a / switching_time_s


def impedance_frequency_sweep(C, ESR, ESL, N, L_via=0.948e-9,
                              f_start=1e6, f_stop=10e9, n_points=5000):
    """Full impedance sweep. Returns (freq, Z_complex, Z_mag)."""
    freq = np.logspace(np.log10(f_start), np.log10(f_stop), n_points)
    Z = parallel_cap_impedance(freq, C, ESR, ESL, N, L_via)
    return freq, Z, np.abs(Z)
