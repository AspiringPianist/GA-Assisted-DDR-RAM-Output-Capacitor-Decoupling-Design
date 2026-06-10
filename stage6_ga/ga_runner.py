import os
import sys
import random
import pickle
import json
import time as time_mod
import numpy as np
from tqdm import tqdm
from deap import base, creator, tools

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stage6_ga.chromosome import CapNetwork, CAP_LIBRARY
from stage6_ga.fitness import evaluate, evaluate_detailed
from stage5_ltspice.ltspice_interface import run_simulation

# ===== GA Hyperparameters =====
# POP=4 + seed, GEN=2 → ~10 min at 50s/eval (worst case 12 evals)
POP_SIZE   = 4
N_GEN      = 2
CX_PROB    = 0.5
MUT_PROB   = 0.5   # higher mutation — more exploration around seed in fewer gens
TOURN_SIZE = 2

# ---------------------------------------------------------------------------
# Seed: load previous GA best from checkpoint, fallback to manual design
# ---------------------------------------------------------------------------
_CHECKPOINT = os.path.join(os.path.dirname(__file__), "ga_results", "checkpoint.json")
_FALLBACK_VDDQ = [7, 6, 10, 8, 3, 8, 4, 4]
_FALLBACK_VTT  = [4, 3,  7, 4, 2, 5, 2, 3]

if os.path.exists(_CHECKPOINT):
    with open(_CHECKPOINT) as _f:
        _ckpt = json.load(_f)
    SEED_VDDQ = _ckpt["vddq"]
    SEED_VTT  = _ckpt["vtt"]
    print(f"[Seed] Loaded checkpoint gen={_ckpt['gen']}  fit={_ckpt['best_fit']:.1f}")
else:
    SEED_VDDQ = _FALLBACK_VDDQ
    SEED_VTT  = _FALLBACK_VTT
    print("[Seed] No checkpoint found — using manual design")

# Results setup
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "ga_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Define fitness and individual
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", CapNetwork, fitness=creator.FitnessMin)


def setup_deap():
    toolbox = base.Toolbox()
    toolbox.register("individual", lambda: creator.Individual())
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate",     lambda ind1, ind2: ind1.mate(ind2))
    toolbox.register("mutate",   lambda ind: ind.mutate(MUT_PROB))
    toolbox.register("select",   tools.selTournament, tournsize=TOURN_SIZE)
    toolbox.register("evaluate", lambda ind: evaluate(ind, run_simulation))
    return toolbox


def build_seeded_population(toolbox):
    """First individual is the hand-designed seed; rest are random."""
    seed = creator.Individual(SEED_VDDQ, SEED_VTT)
    rest = toolbox.population(n=POP_SIZE - 1)
    return [seed] + rest


def save_checkpoint(gen, hof, logbook):
    best = hof[0]
    checkpoint = {
        "gen":      gen,
        "best_fit": float(best.fitness.values[0]),
        "vddq":     best.vddq_counts,
        "vtt":      best.vtt_counts,
    }
    with open(os.path.join(RESULTS_DIR, "checkpoint.json"), "w") as f:
        json.dump(checkpoint, f, indent=4)
    with open(os.path.join(RESULTS_DIR, "best_network.pkl"), "wb") as f:
        pickle.dump(best, f)
    with open(os.path.join(RESULTS_DIR, "ga_logbook.pkl"), "wb") as f:
        pickle.dump(logbook, f)


def run_ga():
    print("=" * 70)
    print("  DDR4 PDN Optimizer — Seeded GA (Sequential Mode)")
    print(f"  Pop={POP_SIZE}  Gens={N_GEN}  CxP={CX_PROB}  MutP={MUT_PROB}")
    print(f"  Seed VDDQ={SEED_VDDQ}  (total {sum(SEED_VDDQ)} caps)")
    print(f"  Seed VTT ={SEED_VTT}   (total {sum(SEED_VTT)} caps)")
    print("=" * 70)

    toolbox = setup_deap()

    pop    = build_seeded_population(toolbox)
    hof    = tools.HallOfFame(5)
    stats  = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("min", np.min)

    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals', 'avg', 'min']

    wall_start = time_mod.time()

    # Evaluate initial population
    print("\nEvaluating Initial Population (includes seed)...")
    invalid_ind = [ind for ind in pop if not ind.fitness.valid]
    for ind in tqdm(invalid_ind, desc="Simulating"):
        ind.fitness.values = toolbox.evaluate(ind)

    hof.update(pop)
    record = stats.compile(pop)
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    print(logbook.stream)

    # Evolution loop
    for gen in range(1, N_GEN + 1):
        elapsed = time_mod.time() - wall_start
        if gen > 1:
            secs_per_gen = elapsed / (gen - 1)
            eta = secs_per_gen * (N_GEN - gen + 1)
            print(f"\n--- Generation {gen}/{N_GEN}  |  elapsed {elapsed/60:.1f}m  |  ETA ~{eta/60:.1f}m ---")
        else:
            print(f"\n--- Generation {gen}/{N_GEN} ---")

        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < CX_PROB:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        for mutant in offspring:
            if random.random() < MUT_PROB:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in tqdm(invalid_ind, desc=f"Gen {gen}"):
            ind.fitness.values = toolbox.evaluate(ind)

        pop[:] = offspring

        hof.update(pop)
        record = stats.compile(pop)
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        print(logbook.stream)

        save_checkpoint(gen, hof, logbook)

    total_mins = (time_mod.time() - wall_start) / 60
    print(f"\n  Total wall time: {total_mins:.1f} minutes")

    print("\n" + "=" * 70)
    print("  OPTIMIZATION COMPLETE")
    print("=" * 70)

    best = hof[0]
    print("\n=== Best Network Configuration ===")
    print(best.summary())

    print("\nRunning Detailed Final Verification...")
    detailed = evaluate_detailed(best, run_simulation)

    print("\n=== Performance Metrics (Detailed) ===")
    for rail in ["VDDQ", "VTT"]:
        res = detailed[rail]
        status = "PASS ✓" if res['JEDEC_pass'] else "FAIL ✗"
        print(f"  {rail}: Ripple {res['ripple_mV']:.2f}mV  Z_peak {res['Z_peak_mOhm']:.2f}mOhm  [{status}]")
    bom = detailed['BOM']
    print(f"  BOM: {bom['vddq_caps']} VDDQ + {bom['vtt_caps']} VTT = {bom['total_caps']} total caps")


if __name__ == "__main__":
    run_ga()
