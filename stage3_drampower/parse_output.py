"""
parse_output.py — Parse DRAMPower log output to structured per-cycle current CSV.

Reads DRAMPower's verbose output and extracts the per-cycle total current
waveform, producing a two-column CSV: time_ps, current_mA.

If DRAMPower traces are not available, can also generate synthetic
current waveforms based on DDR4 IDD values for testing purposes.
"""

import argparse
import csv
import os
import re
import sys
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def parse_drampower_log(input_path: str, output_path: str) -> dict:
    """
    Parse DRAMPower log and extract per-cycle current waveform.

    Parameters
    ----------
    input_path : str
        Path to DRAMPower .log output file.
    output_path : str
        Path to write output CSV (time_ps, current_mA).

    Returns
    -------
    dict
        Summary statistics of the parsed waveform.
    """
    time_ps = []
    current_mA = []

    # DRAMPower log format varies by version — support multiple patterns
    patterns = [
        # Pattern 1: "Time: <ps> Current: <mA>"
        re.compile(r"Time:\s*([\d.]+)\s*(?:ps)?\s*Current:\s*([\d.]+)\s*(?:mA)?"),
        # Pattern 2: Tab-separated "time\tcurrent"
        re.compile(r"^([\d.]+)\t([\d.]+)$"),
        # Pattern 3: Comma-separated CSV
        re.compile(r"^([\d.]+),([\d.]+)$"),
    ]

    with open(input_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    time_ps.append(float(match.group(1)))
                    current_mA.append(float(match.group(2)))
                    break

    if not time_ps:
        raise ValueError(f"No current data found in {input_path}. "
                         "Check DRAMPower log format.")

    # Write output CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_ps", "current_mA"])
        for t, i in zip(time_ps, current_mA):
            writer.writerow([f"{t:.1f}", f"{i:.4f}"])

    stats = {
        "n_samples": len(time_ps),
        "duration_ps": time_ps[-1] - time_ps[0],
        "peak_mA": max(current_mA),
        "mean_mA": sum(current_mA) / len(current_mA),
        "min_mA": min(current_mA),
    }

    print(f"[parse_output] Parsed {stats['n_samples']} samples")
    print(f"  Duration:  {stats['duration_ps']:.0f} ps "
          f"({stats['duration_ps']/1e6:.2f} µs)")
    print(f"  Peak:      {stats['peak_mA']:.1f} mA")
    print(f"  Mean:      {stats['mean_mA']:.1f} mA")

    return stats


def generate_synthetic_waveform(
    workload: str,
    output_path: str,
    duration_us: float = 10.0,
    tCK_ns: float = 0.625,
) -> dict:
    """
    Generate a synthetic DDR4 current waveform for testing when
    DRAMPower/gem5 traces are not available.

    Uses IDD values from DDR4-3200 datasheet and workload-specific
    patterns to create realistic current profiles.

    Parameters
    ----------
    workload : str
        One of "streaming", "random_access", "rowhammer".
    output_path : str
        Path to write output CSV.
    duration_us : float
        Waveform duration in microseconds.
    tCK_ns : float
        Clock period in nanoseconds (0.625ns for DDR4-3200).

    Returns
    -------
    dict
        Summary statistics.
    """
    # DDR4-3200 IDD values (mA) from Micron datasheet
    IDD0   = 58    # ACT-PRE current
    IDD2N  = 37    # Precharge standby
    IDD3N  = 47    # Active standby
    IDD4R  = 225   # Read burst
    IDD4W  = 232   # Write burst
    IDD5   = 280   # Refresh
    IDD6   = 12    # Self-refresh

    tCK_ps = tCK_ns * 1000  # Convert to picoseconds
    n_cycles = int(duration_us * 1e6 / tCK_ps)

    # Generate time array
    time_ps = np.arange(n_cycles) * tCK_ps
    current_mA = np.full(n_cycles, IDD2N, dtype=float)  # baseline: standby

    # Refresh events every 7.8µs (tREFI)
    tREFI_cycles = int(7.8e3 / tCK_ns)
    tRFC_cycles = 350  # ~219ns at DDR4-3200

    rng = np.random.default_rng(42)

    if workload == "streaming":
        # Sequential access: steady moderate current with periodic bursts
        # Low ACT rate (row hits), mostly read/write bursts
        burst_interval = 16  # BL=8, so burst every 16 cycles (row hit)
        for i in range(0, n_cycles, burst_interval):
            end = min(i + 8, n_cycles)
            # Alternating read/write
            idd = IDD4W if (i // burst_interval) % 2 == 0 else IDD4R
            current_mA[i:end] = idd
            # Small idle gap
            if end < n_cycles:
                current_mA[end:min(end + 4, n_cycles)] = IDD3N

    elif workload == "random_access":
        # Random access: high ACT rate, irregular bursts
        # Every access is a row miss → ACT + burst + PRE
        i = 0
        while i < n_cycles:
            gap = rng.integers(4, 40)  # Random gap between accesses
            i += gap
            if i >= n_cycles:
                break

            # ACT phase (tRCD = 22 cycles)
            end_act = min(i + 22, n_cycles)
            current_mA[i:end_act] = IDD0
            i = end_act

            # Burst phase (BL=8 cycles)
            end_burst = min(i + 8, n_cycles)
            current_mA[i:end_burst] = IDD4R if rng.random() > 0.3 else IDD4W
            i = end_burst

            # PRE phase
            end_pre = min(i + 22, n_cycles)
            current_mA[i:end_pre] = IDD3N
            i = end_pre

    elif workload == "rowhammer":
        # Double-sided hammering: maximum ACT rate, no idle
        # ACT row A → PRE → ACT row B → PRE, repeat
        i = 0
        while i < n_cycles:
            # ACT row A
            end = min(i + 22, n_cycles)
            current_mA[i:end] = IDD0 * 1.3  # Elevated due to rapid switching
            i = end

            # Brief read
            end = min(i + 8, n_cycles)
            current_mA[i:end] = IDD4R
            i = end

            # PRE + ACT row B
            end = min(i + 22, n_cycles)
            current_mA[i:end] = IDD0 * 1.3
            i = end

            # Brief read
            end = min(i + 8, n_cycles)
            current_mA[i:end] = IDD4R
            i = end
    else:
        raise ValueError(f"Unknown workload: {workload}")

    # Overlay refresh events
    for ref_start in range(0, n_cycles, tREFI_cycles):
        ref_end = min(ref_start + tRFC_cycles, n_cycles)
        current_mA[ref_start:ref_end] = IDD5

    # Add realistic noise (±5% variation)
    noise = rng.normal(1.0, 0.05, n_cycles)
    current_mA *= noise
    current_mA = np.clip(current_mA, 0, None)

    # Write output
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_ps", "current_mA"])
        for t, c in zip(time_ps, current_mA):
            writer.writerow([f"{t:.1f}", f"{c:.4f}"])

    stats = {
        "n_samples": len(time_ps),
        "duration_ps": float(time_ps[-1]),
        "peak_mA": float(np.max(current_mA)),
        "mean_mA": float(np.mean(current_mA)),
        "min_mA": float(np.min(current_mA)),
    }

    print(f"[synthetic] Generated {workload} waveform: "
          f"{stats['n_samples']} samples, "
          f"peak={stats['peak_mA']:.1f}mA, "
          f"mean={stats['mean_mA']:.1f}mA")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Parse DRAMPower output or generate synthetic waveforms"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Parse command
    parse_cmd = subparsers.add_parser("parse", help="Parse DRAMPower log")
    parse_cmd.add_argument("--input", "-i", required=True, help="DRAMPower log file")
    parse_cmd.add_argument("--output", "-o", required=True, help="Output CSV path")

    # Synthetic command
    synth_cmd = subparsers.add_parser("synthetic", help="Generate synthetic waveforms")
    synth_cmd.add_argument("--workload", "-w", required=True,
                           choices=["streaming", "random_access", "rowhammer", "all"])
    synth_cmd.add_argument("--output-dir", "-o", default="current_waveforms",
                           help="Output directory for CSV files")
    synth_cmd.add_argument("--duration", "-d", type=float, default=10.0,
                           help="Duration in microseconds (default: 10)")

    args = parser.parse_args()

    if args.command == "parse":
        parse_drampower_log(args.input, args.output)

    elif args.command == "synthetic":
        workloads = (["streaming", "random_access", "rowhammer"]
                     if args.workload == "all" else [args.workload])

        for wl in workloads:
            output = os.path.join(args.output_dir, f"{wl}_It.csv")
            generate_synthetic_waveform(wl, output, duration_us=args.duration)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
