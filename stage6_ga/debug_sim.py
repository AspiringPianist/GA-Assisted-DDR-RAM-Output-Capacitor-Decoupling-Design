import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from stage5_ltspice.ltspice_interface import run_simulation, generate_network_lines
from stage6_ga.chromosome import CAP_LIBRARY

def debug():
    params = {
        "vddq_network": [10, 0, 0, 0, 0, 0, 0, 0],
        "vtt_network": [5, 0, 0, 0, 0, 0, 0, 0],
        "library": CAP_LIBRARY
    }
    
    print("Testing generate_network_lines...")
    lines = generate_network_lines(params['vddq_network'], params['library'], "VDDQ")
    print(f"Generated {len(lines)} lines for VDDQ.")
    for l in lines[:3]:
        print(f"  {l}")

    print("\nTesting full netlist generation (Dry Run)...")
    # We won't actually run LTSpice, just see the generated file
    with open("stage5_ltspice/netlists/ddr4_pdn.net", "r") as f:
        netlist = f.read()
    
    vddq_lines = generate_network_lines(params['vddq_network'], params['library'], "VDDQ")
    vtt_lines = generate_network_lines(params['vtt_network'], params['library'], "VTT")
    
    netlist = netlist.replace(';DECOUPLING_NETWORK_VDDQ', "\n".join(vddq_lines))
    netlist = netlist.replace(';DECOUPLING_NETWORK_VTT', "\n".join(vtt_lines))
    
    print("\nSnippet of injected netlist:")
    # Find the section
    idx = netlist.find("Decoupling Network Placeholders")
    print(netlist[idx:idx+300])

if __name__ == "__main__":
    debug()
