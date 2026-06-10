"""
Plot the raw current profiles for each DDR4 workload (PWL files).
Generates both an overview (all workloads, full window) and a zoomed
inset showing the sub-microsecond pulse structure.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

PWL_DIR  = os.path.join(os.path.dirname(__file__), "pwl_files")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "pwl_plots")
os.makedirs(OUT_DIR, exist_ok=True)

WORKLOADS = {
    "rowhammer":   {"vddq": "rowhammer.pwl",    "vtt": "rowhammer_vtt.pwl",    "color": "#d62728"},
    "random_access":{"vddq": "random_access.pwl","vtt": "random_access_vtt.pwl","color": "#ff7f0e"},
    "streaming":   {"vddq": "streaming.pwl",     "vtt": "streaming_vtt.pwl",    "color": "#1f77b4"},
}

T_START_PS = 700_000_000.0   # PWL activity begins at 0.7 ms = 700,000,000 ps


def read_pwl(path):
    """Return (time_us, current_A) arrays, time offset to activity start."""
    t, i = [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            t_ps  = float(parts[0].rstrip("ps").rstrip("s") if "ps" in parts[0] else parts[0])
            i_val = float(parts[1])
            t.append(t_ps)
            i.append(i_val)
    t = np.array(t)
    i = np.array(i)
    # Offset so activity starts at t=0, convert ps → µs
    t_us = (t - T_START_PS) / 1e6
    mask = t_us >= -0.5   # keep a tiny pre-activity tail for context
    return t_us[mask], i[mask]


# ---------------------------------------------------------------------------
# Figure 1 — Overview: all workloads side by side (VDDQ only, full window)
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)
fig.suptitle("DDR4 VDDQ Load Current Profiles — All Workloads", fontsize=15, fontweight="bold")

for ax, (name, cfg) in zip(axes, WORKLOADS.items()):
    t, i = read_pwl(os.path.join(PWL_DIR, cfg["vddq"]))
    window = (t >= 0) & (t <= 100)   # first 100 µs of activity
    ax.plot(t[window], i[window], color=cfg["color"], linewidth=0.6, alpha=0.85)
    ax.set_title(name.replace("_", " ").title(), fontsize=12, fontweight="bold")
    ax.set_ylabel("Current (A)", fontsize=10)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.25)

    # Annotate peak and mean
    i_win = i[window]
    ax.axhline(i_win.mean(), color="black", linestyle="--", linewidth=0.8, alpha=0.6,
               label=f"Mean = {i_win.mean():.2f} A")
    ax.axhline(i_win.max(),  color="red",   linestyle=":",  linewidth=0.8, alpha=0.7,
               label=f"Peak = {i_win.max():.2f} A")
    ax.legend(fontsize=9, loc="upper right")

axes[-1].set_xlabel("Time (µs from activity start)", fontsize=11)
fig.tight_layout()
path1 = os.path.join(OUT_DIR, "workload_currents_overview.png")
fig.savefig(path1, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[OK] {path1}")


# ---------------------------------------------------------------------------
# Figure 2 — Zoomed: first 5 µs showing pulse structure + VDDQ vs VTT
# ---------------------------------------------------------------------------

fig = plt.figure(figsize=(16, 9))
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.3)
fig.suptitle("DDR4 Current Profiles — Pulse Structure (first 5 µs)  |  VDDQ vs VTT",
             fontsize=14, fontweight="bold")

for row, (name, cfg) in enumerate(WORKLOADS.items()):
    t_vddq, i_vddq = read_pwl(os.path.join(PWL_DIR, cfg["vddq"]))
    t_vtt,  i_vtt  = read_pwl(os.path.join(PWL_DIR, cfg["vtt"]))

    zoom = 5.0   # µs

    ax_vddq = fig.add_subplot(gs[row, 0])
    ax_vtt  = fig.add_subplot(gs[row, 1])

    for ax, t, i, rail, target in [
        (ax_vddq, t_vddq, i_vddq, "VDDQ", 1.2),
        (ax_vtt,  t_vtt,  i_vtt,  "VTT",  0.6),
    ]:
        w = (t >= 0) & (t <= zoom)
        ax.plot(t[w], i[w], color=cfg["color"], linewidth=0.8)
        ax.set_title(f"{name.replace('_',' ').title()} — {rail}", fontsize=10, fontweight="bold")
        ax.set_ylabel("I (A)", fontsize=9)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.2)

        i_w = i[w]
        stats = (f"peak={i_w.max():.2f}A  mean={i_w.mean():.2f}A  "
                 f"rms={np.sqrt(np.mean(i_w**2)):.2f}A")
        ax.set_xlabel(f"Time (µs)   {stats}", fontsize=8)

path2 = os.path.join(OUT_DIR, "workload_currents_zoomed.png")
fig.savefig(path2, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[OK] {path2}")


# ---------------------------------------------------------------------------
# Figure 3 — Power spectral density (FFT) — what frequencies carry energy
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=False)
fig.suptitle("Current Power Spectral Density — Frequency Content of Each Workload",
             fontsize=13, fontweight="bold")

for ax, (name, cfg) in zip(axes, WORKLOADS.items()):
    t, i = read_pwl(os.path.join(PWL_DIR, cfg["vddq"]))
    w = t >= 0
    t_w, i_w = t[w], i[w]

    # Uniform resampling for FFT (PWL points are evenly spaced at 625 ps = 0.000625 µs)
    dt_us   = np.median(np.diff(t_w))
    freqs   = np.fft.rfftfreq(len(i_w), d=dt_us * 1e-6)   # in Hz
    psd     = np.abs(np.fft.rfft(i_w - i_w.mean())) ** 2

    # Plot up to 500 MHz
    mask = freqs <= 500e6
    ax.semilogy(freqs[mask] / 1e6, psd[mask], color=cfg["color"], linewidth=0.7, alpha=0.85)
    ax.set_title(name.replace("_", " ").title(), fontsize=11, fontweight="bold")
    ax.set_xlabel("Frequency (MHz)", fontsize=10)
    ax.set_ylabel("Power (A²)", fontsize=10)
    ax.grid(True, which="both", alpha=0.2)

    # Mark dominant frequency
    peak_f = freqs[mask][np.argmax(psd[mask])]
    ax.axvline(peak_f / 1e6, color="black", linestyle="--", linewidth=1,
               label=f"Peak @ {peak_f/1e6:.1f} MHz")
    ax.legend(fontsize=9)

fig.tight_layout()
path3 = os.path.join(OUT_DIR, "workload_currents_fft.png")
fig.savefig(path3, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[OK] {path3}")
