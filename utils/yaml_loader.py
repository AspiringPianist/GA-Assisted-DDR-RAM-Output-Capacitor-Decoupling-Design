"""
YAML configuration loader with validation for DDR4 PDN Optimizer.

Loads and validates ddr4_params.yaml and pdn_constraints.yaml,
ensuring all required parameters are present and within physical bounds.
"""

import os
import yaml
import sys


# Base directory: two levels up from utils/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_config_path(filename: str) -> str:
    """Resolve a config filename to its full path in the config/ directory."""
    return os.path.join(BASE_DIR, "config", filename)


def load_ddr4_params(path: str = None) -> dict:
    """
    Load and validate DDR4 electrical parameters.

    Parameters
    ----------
    path : str, optional
        Path to ddr4_params.yaml. Defaults to config/ddr4_params.yaml.

    Returns
    -------
    dict
        Validated DDR4 parameters under the 'ddr4' key.

    Raises
    ------
    FileNotFoundError
        If the config file does not exist.
    ValueError
        If required keys are missing or values are out of physical range.
    """
    if path is None:
        path = _resolve_config_path("ddr4_params.yaml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"DDR4 params config not found: {path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    # Validate top-level key
    if "ddr4" not in config:
        raise ValueError("Config must contain a 'ddr4' top-level key")

    ddr4 = config["ddr4"]

    # Required keys and their valid ranges (min, max)
    required = {
        "vddq_v":               (0.5, 3.3),
        "vddq_tolerance_v":     (0.001, 0.5),
        "odt_ohm":              (10, 240),
        "chips_per_dimm":       (1, 36),
        "max_simultaneous_nets": (1, 256),
        "clock_mhz":            (100, 4800),
        "switching_time_ns":    (0.01, 10.0),
    }

    for key, (vmin, vmax) in required.items():
        if key not in ddr4:
            raise ValueError(f"Missing required DDR4 parameter: '{key}'")
        val = ddr4[key]
        if not (vmin <= val <= vmax):
            raise ValueError(
                f"DDR4 parameter '{key}' = {val} is out of range [{vmin}, {vmax}]"
            )

    return config


def load_pdn_constraints(path: str = None) -> dict:
    """
    Load and validate PDN constraints (rail tolerances, Lmax targets, via params).

    Parameters
    ----------
    path : str, optional
        Path to pdn_constraints.yaml. Defaults to config/pdn_constraints.yaml.

    Returns
    -------
    dict
        Validated PDN constraints.
    """
    if path is None:
        path = _resolve_config_path("pdn_constraints.yaml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"PDN constraints config not found: {path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    # Validate rails section
    if "rails" not in config:
        raise ValueError("Config must contain a 'rails' section")

    for rail_name, rail in config["rails"].items():
        for key in ["nominal_v", "tolerance_v", "lmax_pH", "nmax_caps"]:
            if key not in rail:
                raise ValueError(f"Rail '{rail_name}' missing required key: '{key}'")

    # Validate via section
    if "via" not in config:
        raise ValueError("Config must contain a 'via' section")

    via = config["via"]
    for key in ["board_thickness_in", "via_diameter_in", "l_via_nH"]:
        if key not in via:
            raise ValueError(f"Via section missing required key: '{key}'")

    return config


def load_cap_library(path: str = None) -> list:
    """
    Load the capacitor library from YAML.

    Parameters
    ----------
    path : str, optional
        Path to cap_library.yaml. Defaults to stage6_ga/cap_library.yaml.

    Returns
    -------
    list
        List of capacitor dicts with keys: part, C_F, ESR_ohm, ESL_H, package.
    """
    if path is None:
        path = os.path.join(BASE_DIR, "stage6_ga", "cap_library.yaml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Capacitor library not found: {path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    caps = config.get("capacitors", [])
    if not caps:
        raise ValueError("Capacitor library is empty")

    required_keys = {"part", "C_F", "ESR_ohm", "ESL_H", "package"}
    for i, cap in enumerate(caps):
        missing = required_keys - set(cap.keys())
        if missing:
            raise ValueError(
                f"Capacitor entry {i} ('{cap.get('part', '?')}') missing keys: {missing}"
            )
        if cap["C_F"] <= 0:
            raise ValueError(f"Capacitor '{cap['part']}' has non-positive capacitance")
        if cap["ESR_ohm"] < 0:
            raise ValueError(f"Capacitor '{cap['part']}' has negative ESR")
        if cap["ESL_H"] < 0:
            raise ValueError(f"Capacitor '{cap['part']}' has negative ESL")

    return caps


if __name__ == "__main__":
    print("=== Loading DDR4 params ===")
    ddr4 = load_ddr4_params()
    print(yaml.dump(ddr4, default_flow_style=False))

    print("=== Loading PDN constraints ===")
    pdn = load_pdn_constraints()
    print(yaml.dump(pdn, default_flow_style=False))

    print("=== Loading capacitor library ===")
    caps = load_cap_library()
    for cap in caps:
        print(f"  {cap['part']}: {cap['C_F']*1e6:.1f}µF, "
              f"ESR={cap['ESR_ohm']*1e3:.1f}mOhm, "
              f"ESL={cap['ESL_H']*1e9:.2f}nH, "
              f"pkg={cap['package']}")
    print(f"\n  Total: {len(caps)} capacitors in library")
