# ═══════════════════════════════════════════════════════════════
# config.py
# Application & GA configuration for IntelliPlan·3D
#
# All values can be overridden via environment variables.
# Example (.env or shell):
#   export FLASK_ENV=production
#   export GA_POPULATION_SIZE=80
#   export SECRET_KEY=your-secret-key
#
# Priority:  env variable  >  this file  >  utils/constants.py defaults
# ═══════════════════════════════════════════════════════════════

import os
from utils.constants import (
    GA_POPULATION_SIZE,
    GA_MAX_GENERATIONS,
    GA_CROSSOVER_RATE,
    GA_MUTATION_RATE,
    GA_TOURNAMENT_SIZE,
    GA_ELITISM_COUNT,
    GA_TOP_LAYOUTS_RETURN,
)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# ════════════════════════════════════════════════════════════════
#  BASE CONFIGURATION  (all environments)
# ════════════════════════════════════════════════════════════════

class Config:
    # ── Flask core ───────────────────────────────────────────────
    SECRET_KEY       = os.environ.get("SECRET_KEY", "intelliplan-dev-secret-change-in-prod")
    JSON_SORT_KEYS   = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024   # 2 MB max request body

    # ── CORS ────────────────────────────────────────────────────
    # Origins allowed to call the API.
    # In development:  also allow localhost on common frontend ports.
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,"
        "http://localhost:5500,"
        "http://127.0.0.1:5500,"
        "http://localhost:8080,"
        "null",           # file:// origin (VS Code Live Server)
    ).split(",")

    # ── GA engine ────────────────────────────────────────────────
    GA_POPULATION_SIZE  = _env_int("GA_POPULATION_SIZE",  GA_POPULATION_SIZE)
    GA_MAX_GENERATIONS  = _env_int("GA_MAX_GENERATIONS",  GA_MAX_GENERATIONS)
    GA_CROSSOVER_RATE   = _env_float("GA_CROSSOVER_RATE", GA_CROSSOVER_RATE)
    GA_MUTATION_RATE    = _env_float("GA_MUTATION_RATE",  GA_MUTATION_RATE)
    GA_TOURNAMENT_SIZE  = _env_int("GA_TOURNAMENT_SIZE",  GA_TOURNAMENT_SIZE)
    GA_ELITISM_COUNT    = _env_int("GA_ELITISM_COUNT",    GA_ELITISM_COUNT)
    GA_TOP_LAYOUTS      = _env_int("GA_TOP_LAYOUTS",      GA_TOP_LAYOUTS_RETURN)

    # ── Plot constraints ─────────────────────────────────────────
    PLOT_MIN_DIMENSION  = _env_int("PLOT_MIN_DIMENSION",  10)    # ft
    PLOT_MAX_DIMENSION  = _env_int("PLOT_MAX_DIMENSION",  500)   # ft

    # ── Export ───────────────────────────────────────────────────
    EXPORT_DIR          = os.environ.get("EXPORT_DIR", "exports")
    PDF_DOWNLOAD_NAME   = "intelliplan-floor-plan.pdf"

    # ── Logging ──────────────────────────────────────────────────
    LOG_LEVEL           = os.environ.get("LOG_LEVEL", "DEBUG")


# ════════════════════════════════════════════════════════════════
#  DEVELOPMENT  (default)
# ════════════════════════════════════════════════════════════════

class DevelopmentConfig(Config):
    DEBUG           = True
    TESTING         = False
    ENV             = "development"


# ════════════════════════════════════════════════════════════════
#  TESTING
# ════════════════════════════════════════════════════════════════

class TestingConfig(Config):
    DEBUG           = False
    TESTING         = True
    ENV             = "testing"

    # Smaller GA for fast test runs
    GA_POPULATION_SIZE = 10
    GA_MAX_GENERATIONS = 5
    GA_TOP_LAYOUTS     = 1


# ════════════════════════════════════════════════════════════════
#  PRODUCTION
# ════════════════════════════════════════════════════════════════

class ProductionConfig(Config):
    DEBUG           = False
    TESTING         = False
    ENV             = "production"
    LOG_LEVEL       = os.environ.get("LOG_LEVEL", "INFO")

    # Use env SECRET_KEY in production; warn if using the default
    SECRET_KEY      = os.environ.get("SECRET_KEY", Config.SECRET_KEY)

    def __post_init__(self):
        if self.SECRET_KEY == Config.SECRET_KEY:
            import warnings
            warnings.warn(
                "SECRET_KEY is using the default dev value in production. "
                "Set SECRET_KEY env variable for security.",
                RuntimeWarning, stacklevel=2,
            )


# ════════════════════════════════════════════════════════════════
#  CONFIG REGISTRY
# ════════════════════════════════════════════════════════════════

_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
}


def get_config() -> Config:
    """
    Return the config class matching the FLASK_ENV environment variable.
    Defaults to DevelopmentConfig.
    """
    env  = os.environ.get("FLASK_ENV", "development").lower()
    cfg  = _CONFIG_MAP.get(env, DevelopmentConfig)
    return cfg()


# ── Convenience singleton used by app.py ────────────────────────
config = get_config()
