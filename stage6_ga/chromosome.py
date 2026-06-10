import random
import yaml
import os

lib_path = os.path.join(os.path.dirname(__file__), "cap_library.yaml")
with open(lib_path, "r") as f:
    _raw_lib = yaml.safe_load(f)["capacitors"]

CAP_LIBRARY = []
for p in _raw_lib:
    CAP_LIBRARY.append({
        "name": p["part"],
        "C":   p["C_F"],
        "ESR": p["ESR_ohm"],
        "ESL": p["ESL_H"],
    })


class CapNetwork:
    """
    Decoupling capacitor network for VDDQ and VTT rails.
    Each rail is a count vector — one entry per cap type in CAP_LIBRARY.
    """
    def __init__(self, vddq_counts=None, vtt_counts=None):
        n_types = len(CAP_LIBRARY)
        self.vddq_counts = (
            [random.randint(0, 12) for _ in range(n_types)]
            if vddq_counts is None else list(vddq_counts)
        )
        self.vtt_counts = (
            [random.randint(0, 8) for _ in range(n_types)]
            if vtt_counts is None else list(vtt_counts)
        )
        # Do NOT set self.fitness — DEAP manages it via creator.create

    def get_params(self):
        return {
            "vddq_network": self.vddq_counts,
            "vtt_network":  self.vtt_counts,
            "library":      CAP_LIBRARY,
        }

    def mate(self, other):
        """One-point crossover modifying both individuals in-place."""
        if len(self.vddq_counts) > 1:
            cp = random.randint(1, len(self.vddq_counts) - 1)
            self.vddq_counts[cp:], other.vddq_counts[cp:] = (
                other.vddq_counts[cp:], self.vddq_counts[cp:]
            )
        if len(self.vtt_counts) > 1:
            cp = random.randint(1, len(self.vtt_counts) - 1)
            self.vtt_counts[cp:], other.vtt_counts[cp:] = (
                other.vtt_counts[cp:], self.vtt_counts[cp:]
            )
        return self, other

    def mutate(self, mutation_rate=0.2):
        for i in range(len(self.vddq_counts)):
            if random.random() < mutation_rate:
                self.vddq_counts[i] = max(0, self.vddq_counts[i] + random.randint(-2, 2))
        for i in range(len(self.vtt_counts)):
            if random.random() < mutation_rate:
                self.vtt_counts[i] = max(0, self.vtt_counts[i] + random.randint(-1, 1))

    def summary(self):
        s = "VDDQ Network:\n"
        for i, count in enumerate(self.vddq_counts):
            if count > 0:
                s += f"  - {count}x {CAP_LIBRARY[i]['name']} ({CAP_LIBRARY[i]['C']*1e6:.2f}uF)\n"
        s += "VTT Network:\n"
        for i, count in enumerate(self.vtt_counts):
            if count > 0:
                s += f"  - {count}x {CAP_LIBRARY[i]['name']} ({CAP_LIBRARY[i]['C']*1e6:.2f}uF)\n"
        return s
