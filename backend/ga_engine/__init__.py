# ═══════════════════════════════════════════════════════════════
# ga_engine/__init__.py
# Public API for the Genetic Algorithm engine
# ═══════════════════════════════════════════════════════════════

from ga_engine.ga_runner  import run_ga
from ga_engine.chromosome import encode, decode, chromosome_length, random_chromosome
from ga_engine.population import initialise_population, population_diversity
from ga_engine.fitness    import evaluate_fitness, evaluate_population
from ga_engine.selection  import tournament_select, elitism_indices, rank_population
from ga_engine.operators  import crossover, mutate

__all__ = [
    # Main entry point
    "run_ga",
    # Chromosome codec
    "encode", "decode", "chromosome_length", "random_chromosome",
    # Population
    "initialise_population", "population_diversity",
    # Fitness
    "evaluate_fitness", "evaluate_population",
    # Selection
    "tournament_select", "elitism_indices", "rank_population",
    # Operators
    "crossover", "mutate",
]
