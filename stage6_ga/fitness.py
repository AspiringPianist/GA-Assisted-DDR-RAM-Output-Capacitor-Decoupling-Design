import numpy as np

# Performance Constraints
VDDQ_TARGET = 1.2
VDDQ_TOL    = 0.060   # ±60 mV JEDEC
VTT_TARGET  = 0.6
VTT_TOL     = 0.040   # ±40 mV JEDEC

# Impedance Constraints
Z_TARGET_VDDQ = 0.050  # 50 mOhm
Z_TARGET_VTT  = 0.100  # 100 mOhm
FREQ_LIMIT    = 200e6  # 200 MHz

# Cap count limits (raised to match realistic DDR4 board budgets)
MAX_CAPS_PER_RAIL = 60
MIN_CAPS_PER_RAIL = 5

# Pre-computed frequency sweep for analytical AC (10 Hz → 1 GHz)
_FREQ_ARRAY = np.logspace(1, 9, 300)


def _analytical_impedance(params):
    """
    Analytical RLC parallel-network impedance — ~1000× faster than LTSpice AC.
    Each cap type contributes count parallel admittances; total Z = 1/sum(Y_i).
    """
    library = params['library']
    omega = 2.0 * np.pi * _FREQ_ARRAY

    def rail_z(counts):
        Y = np.zeros(len(omega), dtype=complex)
        for i, count in enumerate(counts):
            if count > 0 and i < len(library):
                p = library[i]
                Z_cap = p['ESR'] + 1j * omega * p['ESL'] + 1.0 / (1j * omega * p['C'])
                Y += count / Z_cap
        if not np.any(Y):
            return np.full(len(omega), 1e3)
        return np.abs(1.0 / Y)

    return {
        'freq':   _FREQ_ARRAY,
        'z_vddq': rail_z(params['vddq_network']),
        'z_vtt':  rail_z(params['vtt_network']),
    }


def evaluate(individual, sim_func):
    """
    Multi-objective fitness (minimise):
      1. Hard voltage penalty  — heavily penalise JEDEC violations
      2. Ripple quality score  — keep minimising ripple even after passing spec
      3. Hard impedance penalty — penalise Z_peak above target (raised weight)
      4. Soft BOM cost         — gentle pressure to avoid excessive caps
    """
    params = individual.get_params()

    # --- 1. Transient ripple via LTSpice ---
    try:
        res_tran = sim_func(
            params,
            "stage4_converter/pwl_files/rowhammer.pwl",
            analysis_type='tran',
        )
        vddq = res_tran['vddq']
        vtt  = res_tran['vtt']

        vddq_ripple = float(vddq.max()) - float(vddq.min())
        vtt_ripple  = float(vtt.max())  - float(vtt.min())

        vddq_undershoot = VDDQ_TARGET - float(vddq.min())
        vddq_overshoot  = float(vddq.max()) - VDDQ_TARGET
        vtt_undershoot  = VTT_TARGET - float(vtt.min())
        vtt_overshoot   = float(vtt.max()) - VTT_TARGET

        # Hard violation penalty (keeps GA away from illegal territory)
        v_penalty = 0.0
        if vddq_undershoot > VDDQ_TOL: v_penalty += (vddq_undershoot - VDDQ_TOL) * 8000
        if vddq_overshoot  > VDDQ_TOL: v_penalty += (vddq_overshoot  - VDDQ_TOL) * 8000
        if vtt_undershoot  > VTT_TOL:  v_penalty += (vtt_undershoot  - VTT_TOL)  * 8000
        if vtt_overshoot   > VTT_TOL:  v_penalty += (vtt_overshoot   - VTT_TOL)  * 8000

        # Continuous ripple quality — GA keeps improving even when already passing
        # Scale: 1mV ripple reduction ≈ 1 unit improvement → meaningful signal
        ripple_score = (vddq_ripple + vtt_ripple) * 1000

    except Exception as e:
        print(f"[WARN] Tran sim error: {e}")
        return (1e6,)

    # --- 2. AC impedance (analytical — no LTSpice call) ---
    res_ac     = _analytical_impedance(params)
    mask       = res_ac['freq'] < FREQ_LIMIT
    z_vddq_max = float(np.max(res_ac['z_vddq'][mask]))
    z_vtt_max  = float(np.max(res_ac['z_vtt'][mask]))

    # Raised to 3000× so impedance is taken seriously alongside voltage
    ac_penalty = 0.0
    if z_vddq_max > Z_TARGET_VDDQ: ac_penalty += (z_vddq_max - Z_TARGET_VDDQ) * 3000
    if z_vtt_max  > Z_TARGET_VTT:  ac_penalty += (z_vtt_max  - Z_TARGET_VTT)  * 3000

    # --- 3. BOM / area penalty (relaxed ceiling, softer curve) ---
    total_vddq = sum(params['vddq_network'])
    total_vtt  = sum(params['vtt_network'])
    area_penalty = 0.0
    for count in (total_vddq, total_vtt):
        if count > MAX_CAPS_PER_RAIL:
            # Quadratic above ceiling — strongly discourages runaway growth
            area_penalty += (count - MAX_CAPS_PER_RAIL) ** 2 * 30
        elif count < MIN_CAPS_PER_RAIL:
            area_penalty += (MIN_CAPS_PER_RAIL - count) * 300

    # Linear BOM cost: gentle pressure to prefer fewer caps when performance is equal
    bom_penalty = (total_vddq + total_vtt) * 1.5

    return (v_penalty + ripple_score + ac_penalty + area_penalty + bom_penalty,)


def evaluate_detailed(individual, sim_func):
    """Full LTSpice verification for the final best individual."""
    params    = individual.get_params()
    res_tran  = sim_func(params, "stage4_converter/pwl_files/rowhammer.pwl", 'tran')
    res_ac    = sim_func(params, None, 'ac')

    vddq = res_tran['vddq']
    vtt  = res_tran['vtt']
    freq = res_ac['freq']
    mask = freq < FREQ_LIMIT

    total_caps = sum(individual.vddq_counts) + sum(individual.vtt_counts)
    vddq_pass = (vddq.max() - vddq.min()) * 1e3 <= VDDQ_TOL * 2e3
    vtt_pass  = (vtt.max()  - vtt.min())  * 1e3 <= VTT_TOL  * 2e3

    return {
        "VDDQ": {
            "V_min":       float(vddq.min()),
            "V_max":       float(vddq.max()),
            "ripple_mV":   float((vddq.max() - vddq.min()) * 1e3),
            "Z_peak_mOhm": float(np.max(res_ac['z_vddq'][mask]) * 1e3),
            "JEDEC_pass":  bool(vddq_pass),
        },
        "VTT": {
            "V_min":       float(vtt.min()),
            "V_max":       float(vtt.max()),
            "ripple_mV":   float((vtt.max() - vtt.min()) * 1e3),
            "Z_peak_mOhm": float(np.max(res_ac['z_vtt'][mask]) * 1e3),
            "JEDEC_pass":  bool(vtt_pass),
        },
        "BOM": {
            "vddq_caps":  sum(individual.vddq_counts),
            "vtt_caps":   sum(individual.vtt_counts),
            "total_caps": total_caps,
        },
    }
