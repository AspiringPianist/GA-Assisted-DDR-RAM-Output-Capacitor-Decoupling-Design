import os
import subprocess
import numpy as np
import shutil
from PyLTSpice.raw.raw_read import RawRead

# Constants
LTSPICE_EXEC = r"C:\Users\unnat\AppData\Local\Programs\ADI\LTspice\LTspice.exe"
NETLIST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "netlists", "ddr4_pdn.net"))
SIM_OUTPUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "sim_results"))

# Ensure output directory exists
os.makedirs(SIM_OUTPUT, exist_ok=True)

def generate_network_lines(counts, library, rail_name):
    """Generates individual LTspice capacitor lines for a network vector."""
    lines = []
    cap_count = 0
    for i, count in enumerate(counts):
        if i >= len(library): break
        part = library[i]
        for _ in range(int(count)):
            cap_count += 1
            # Format: C_DEC_VDDQ_1 VDDQ 0 10u Rser=5m Lser=0.87n
            line = f"C_DEC_{rail_name}_{cap_count} {rail_name} 0 {part['C']:.3e} Rser={part['ESR']:.3e} Lser={part['ESL']:.3e}"
            lines.append(line)
    return lines

def run_simulation(params, pwl_file, analysis_type='tran', start_time=0.7e-3):
    """
    Run LTSpice simulation (Transient or AC).
    params: dict with 'vddq_network', 'vtt_network', 'library'
    start_time: Time to begin data capture for transient analysis (default 0.7ms)
    """
    with open(NETLIST_PATH, "r", encoding='utf-8') as f:
        netlist = f.read()

    # 1. Prepare Network Lines
    vddq_lines = generate_network_lines(params['vddq_network'], params['library'], "VDDQ")
    vtt_lines = generate_network_lines(params['vtt_network'], params['library'], "VTT")
    
    # 2. Inject into placeholders
    netlist = netlist.replace(";DECOUPLING_NETWORK_VDDQ", "\n".join(vddq_lines))
    netlist = netlist.replace(";DECOUPLING_NETWORK_VTT", "\n".join(vtt_lines))

    # 3. Setup Analysis
    lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "netlists", "LTM4632.sub"))
    netlist = netlist.replace('.lib LTM4632.sub', f'.lib "{lib_path}"')
    
    if analysis_type == 'tran':
        # Transient mode
        abs_pwl = os.path.abspath(pwl_file)
        abs_vtt_pwl = abs_pwl.replace(".pwl", "_vtt.pwl")
        netlist = netlist.replace('PWL file="dummy.pwl"', f'PWL file="{abs_pwl}"')
        netlist = netlist.replace('PWL file="dummy_vtt.pwl"', f'PWL file="{abs_vtt_pwl}"')
    else:
        # AC Analysis mode (Impedance)
        # Use higher resolution and wider bandwidth so DDR harmonics are captured
        # 200 points/decade from 1 kHz to 10 GHz
        netlist = netlist.replace('.tran .8m startup', '.ac dec 200 1k 10G')
        # Replace transient sources with AC sources
        netlist = netlist.replace('Iac_vddq VDDQ 0 AC 0', 'Iac_vddq VDDQ 0 AC 1')
        netlist = netlist.replace('Iac_vtt VTT 0 AC 0', 'Iac_vtt VTT 0 AC 1')
        # Comment out PWL
        netlist = netlist.replace('I1 VDDQ 0 PWL', '* I1 VDDQ 0 PWL')
        netlist = netlist.replace('I2 VTT 0 PWL', '* I2 VTT 0 PWL')

    # 4. Save and Run
    run_netlist = os.path.join(SIM_OUTPUT, f"run_temp_{analysis_type}.net")
    with open(run_netlist, "w", encoding='utf-8') as f:
        f.write("* High-Fidelity GA Simulation\n" + netlist)

    # Run
    subprocess.run([LTSPICE_EXEC, "-b", "-Run", run_netlist], check=True, capture_output=True)
    
    # Parse Results
    raw_path = run_netlist.replace(".net", ".raw")
    if not os.path.exists(raw_path) or os.path.getsize(raw_path) == 0:
        raise FileNotFoundError(f"LTSpice failed to generate results at {raw_path}")

    raw = RawRead(raw_path)
    
    if analysis_type == 'tran':
        # VDDQ is rail 0, VTT is rail 1 (usually)
        # We find them by name
        vddq = raw.get_trace("V(vddq)").get_wave()
        vtt = raw.get_trace("V(vtt)").get_wave()
        time = raw.get_trace("time").get_wave()
        
        # Mask for steady state
        mask = time >= start_time
        return {
            "time": time[mask],
            "vddq": vddq[mask],
            "vtt": vtt[mask]
        }
    else:
        # AC result
        freq = raw.get_trace("frequency").get_wave()
        # V / I = Z. Since I is 1A, V is Z.
        z_vddq = np.abs(raw.get_trace("V(vddq)").get_wave())
        z_vtt = np.abs(raw.get_trace("V(vtt)").get_wave())
        return {
            "freq": freq,
            "z_vddq": z_vddq,
            "z_vtt": z_vtt
        }
