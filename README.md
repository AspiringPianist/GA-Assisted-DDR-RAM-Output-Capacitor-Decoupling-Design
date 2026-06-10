# DDR4 PDN Optimization Pipeline Guide

This project contains a comprehensive, 7-stage pipeline to synthesize workload-specific DDR4 power transient waveforms and use a Genetic Algorithm (GA) to optimize a dual-rail decoupling capacitor network (VDDQ and VTT) for a commercial LTSpice regulator (`LTM4632`). This [presentation](https://github.com/AspiringPianist/GA-Assisted-DDR-RAM-Output-Capacitor-Decoupling-Design/blob/main/Output%20Capacitor%20and%20Decoupling%20Design%20for%20DDR%20Power%20Rails%20copy.pdf) explains about 150% of the project.

## Stage 1: Workload Compilation (GEM5/Assembly)

**Objective**: Compile raw assembly traces into executable binaries that mimic edge-case memory access patterns.

```bash
cd stage1_workloads
make all
cd ..
```

## Stage 2: Memory Architecture Simulation (GEM5/DRAMSim3)

**Objective**: Run the binaries through an architectural simulator to extract exact read/write command traces sent to the DDR4 memory controller.

```bash
./stage2_gem5/run_all_workloads.sh
```

## Stage 3: Power Extraction (DRAMPower)

**Objective**: Parse the DRAM command traces using the JEDEC DDR4-3200 device specifications (`DDR4_8Gb_x8_3200.xml`) to calculate exactly how much power/current is consumed per nanosecond.

```bash
./stage3_drampower/run_drampower.sh
```

## Stage 4: Transient Waveform Synthesis

**Objective**: Convert the raw CSVs into highly granular SPICE-compatible Piecewise Linear (`.pwl`) format, synthesizing both the massive VDDQ current swings and the proportional VTT Command/Address bus load.

```bash
python stage4_converter/convert_to_pwl.py
```

## Stage 5: Commercial Regulator Baseline (LTSpice)

**Objective**: Establish a baseline performance metric by injecting the workloads into the default commercial LTM4632 schematic.

1. Save your `LTM4632` schematic with the updated `dummy.pwl` and `dummy_vtt.pwl` placeholders.
2. Export the netlist to `stage5_ltspice/netlists/ddr4_pdn.net`.
3. Run the baseline evaluation script:

```bash
python stage5_ltspice/run_commercial_baseline.py
```

## Stage 6: Dual-Rail Genetic Algorithm Optimization

**Objective**: Optimize the high-frequency decoupling capacitor arrays for both VDDQ and VTT simultaneously. The GA interacts directly with LTSpice in batch mode, dynamically injecting `Ceff`, `ESReff`, etc., and penalizing any configuration that breaches the JEDEC ±60mV (VDDQ) and ±40mV (VTT) boundaries.

```bash
python stage6_ga/ga_runner.py
```

*Outputs:* Optimal BOM selection printed to terminal and saved in `stage6_ga/ga_results/ga_log.txt`.

## Stage 7: Validation and Visualization

**Objective**: Generate presentation-ready analytical graphs (Impedance profiles and Waveform comparisons) comparing the baseline to the GA-optimized design.

```bash
python stage7_ablation/plot_waveforms.py
python stage7_ablation/plot_impedance.py
```
