"""
gem5 SE mode configuration for DDR4 PDN workload simulation.

Configures DerivO3CPU with realistic 3-level cache hierarchy
and DRAMSim3 backend for DDR4-3200 timing.
"""

import m5
from m5.objects import *
from m5.util import addToPath
import os
import sys

# Add gem5 configs to path
addToPath(os.path.join(os.environ.get("GEM5_ROOT", "."), "configs"))


def create_system(workload_elf: str, trace_dir: str) -> System:
    """
    Create a gem5 System with DerivO3CPU + DRAMSim3.

    Parameters
    ----------
    workload_elf : str
        Path to the workload .elf binary.
    trace_dir : str
        Directory for DRAMSim3 trace output.

    Returns
    -------
    System
        Configured gem5 system ready to simulate.
    """
    system = System()
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = "3.2GHz"  # DDR4-3200 → 1600MHz clock
    system.clk_domain.voltage_domain = VoltageDomain()

    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange("2GB")]

    # --- CPU: DerivO3 (out-of-order, models real x86 microarch) ---
    system.cpu = DerivO3CPU()
    system.cpu.clk_domain = SrcClockDomain()
    system.cpu.clk_domain.clock = "3.2GHz"
    system.cpu.clk_domain.voltage_domain = VoltageDomain()

    # --- Cache hierarchy ---
    # L1 Instruction Cache
    system.cpu.icache = Cache()
    system.cpu.icache.size = "32kB"
    system.cpu.icache.assoc = 8
    system.cpu.icache.tag_latency = 1
    system.cpu.icache.data_latency = 1
    system.cpu.icache.response_latency = 1
    system.cpu.icache.mshrs = 16

    # L1 Data Cache
    system.cpu.dcache = Cache()
    system.cpu.dcache.size = "32kB"
    system.cpu.dcache.assoc = 8
    system.cpu.dcache.tag_latency = 2
    system.cpu.dcache.data_latency = 2
    system.cpu.dcache.response_latency = 2
    system.cpu.dcache.mshrs = 16

    # L2 Cache
    system.l2cache = Cache()
    system.l2cache.size = "256kB"
    system.l2cache.assoc = 16
    system.l2cache.tag_latency = 10
    system.l2cache.data_latency = 10
    system.l2cache.response_latency = 10
    system.l2cache.mshrs = 32

    # Connect cache hierarchy
    system.cpu.icache_port = system.cpu.icache.cpu_side
    system.cpu.dcache_port = system.cpu.dcache.cpu_side

    system.l2bus = L2XBar()
    system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
    system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports
    system.l2cache.cpu_side = system.l2bus.mem_side_ports

    # --- Memory controller: DRAMSim3 ---
    system.membus = SystemXBar()
    system.l2cache.mem_side = system.membus.cpu_side_ports

    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DRAMSim3(
        configFile=os.path.join(
            os.path.dirname(__file__),
            "dramsim3_configs", "DDR4_8Gb_x8_3200.ini"
        ),
        filePath=os.path.join(
            os.path.dirname(__file__),
            "dramsim3_configs"
        ),
        outputDir=trace_dir,
    )
    system.mem_ctrl.port = system.membus.mem_side_ports

    # Connect system port for initialization
    system.system_port = system.membus.cpu_side_ports

    # Interrupt controller (required for x86)
    system.cpu.createInterruptController()

    # --- Workload ---
    process = Process()
    process.cmd = [workload_elf]
    system.cpu.workload = process
    system.cpu.createThreads()

    system.workload = SEWorkload.init_compatible(workload_elf)

    return system


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: gem5 se_config.py <workload.elf> [trace_dir]")
        sys.exit(1)

    workload = sys.argv[1]
    trace_dir = sys.argv[2] if len(sys.argv) > 2 else "traces/"

    os.makedirs(trace_dir, exist_ok=True)

    system = create_system(workload, trace_dir)
    root = Root(full_system=False, system=system)

    m5.instantiate()
    print(f"[gem5] Starting simulation: {workload}")
    exit_event = m5.simulate()
    print(f"[gem5] Exiting: {exit_event.getCause()} @ tick {m5.curTick()}")
