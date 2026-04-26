# ═══════════════════════════════════════════════════════════════
# utils/constants.py
# ═══════════════════════════════════════════════════════════════

ROOM_TYPES = [
    "entrance", "living", "dining", "kitchen",
    "master_bedroom", "bedroom",
    "bathroom", "toilet",
    "bathroom_master", "toilet_master",
    "bathroom_attached", "toilet_attached",
    "utility",
]

ROOM_LABELS = {
    "entrance":            "Entrance",
    "living":              "Living Room",
    "dining":              "Dining Room",
    "kitchen":             "Kitchen",
    "master_bedroom":      "Master Bedroom",
    "bedroom":             "Bedroom",
    "bathroom":            "Bathroom",
    "toilet":              "Toilet",
    "bathroom_master":     "Bathroom (Master)",
    "toilet_master":       "Toilet (Master)",
    "bathroom_attached":   "Bathroom (Attached)",
    "toilet_attached":     "Toilet (Attached)",
    "utility":             "Utility Room",
}

# ── BHK compositions ─────────────────────────────────────────────
# Rules:
#   • NO balcony, NO store room, NO pooja in any plan
#   • Living room is the hall (biggest room) with Entrance attached
#   • Kitchen + Dining always adjacent
#   • Bathroom/Toilet are small rooms
#   • 1BHK : 1 common bathroom + toilet
#   • 2BHK : 1 common bathroom + toilet
#   • 3BHK : 1 common (bathroom + toilet) in CENTER
#            + 1 attached to master (bathroom_master + toilet_master)
#   • 4BHK : 1 common (bathroom + toilet) in CENTER
#            + 1 attached to master (bathroom_master + toilet_master)
#            + 1 attached to bedroom 2 (bathroom_attached + toilet_attached)
BHK_ROOM_COMPOSITIONS = {
    "1BHK": [
        "entrance", "living", "kitchen",
        "master_bedroom",
        "bathroom", "toilet",
    ],
    "2BHK": [
        "entrance", "living", "dining", "kitchen",
        "master_bedroom", "bedroom",
        "bathroom", "toilet",
    ],
    "3BHK": [
        "entrance", "living", "dining", "kitchen",
        "master_bedroom", "bedroom", "bedroom",
        "bathroom_master", "toilet_master",   # attached to master
        "bathroom", "toilet",                  # common CENTER
    ],
    "4BHK": [
        "entrance", "living", "dining", "kitchen",
        "master_bedroom", "bedroom", "bedroom", "bedroom",
        "bathroom_master", "toilet_master",    # attached to master bedroom
        "bathroom_attached", "toilet_attached",# attached to bedroom 2
        "bathroom", "toilet",                  # common CENTER
        "utility",
    ],
}

# ── Minimum room sizes (ft × ft) ────────────────────────────────
ROOM_MIN_SIZES = {
    "entrance":            (5.0,  5.0),
    "living":              (14.0, 14.0),
    "dining":              (9.0,  9.0),
    "kitchen":             (8.0,  8.0),
    "master_bedroom":      (11.0, 11.0),
    "bedroom":             (10.0, 10.0),
    "bathroom":            (4.5,  4.5),
    "toilet":              (3.5,  3.5),
    "bathroom_master":     (4.5,  4.5),
    "toilet_master":       (3.5,  3.5),
    "bathroom_attached":   (4.5,  4.5),
    "toilet_attached":     (3.5,  3.5),
    "utility":             (5.0,  5.0),
}

ROOM_PREFERRED_RATIOS = {
    "entrance":            (1.0, 1.5),
    "living":              (1.2, 1.6),
    "dining":              (1.0, 1.2),
    "kitchen":             (0.9, 1.2),
    "master_bedroom":      (1.0, 1.3),
    "bedroom":             (1.0, 1.3),
    "bathroom":            (0.8, 1.0),
    "toilet":              (0.7, 0.9),
    "bathroom_master":     (0.8, 1.0),
    "toilet_master":       (0.7, 0.9),
    "bathroom_attached":   (0.8, 1.0),
    "toilet_attached":     (0.7, 0.9),
    "utility":             (1.0, 1.4),
}

FACING_DIRECTIONS = ["North", "East", "South", "West"]
PLOT_MARGIN = 2.0

GA_POPULATION_SIZE     = 60
GA_MAX_GENERATIONS     = 50
GA_CROSSOVER_RATE      = 0.80
GA_MUTATION_RATE       = 0.15
GA_TOURNAMENT_SIZE     = 5
GA_ELITISM_COUNT       = 3
GA_TOP_LAYOUTS_RETURN  = 3

# ── Vastu rule weights ───────────────────────────────────────────
VASTU_RULE_WEIGHTS = {
    "kitchen_direction":   15,   # SE = Best
    "master_bedroom_dir":  20,   # SW = Best
    "living_room_dir":     15,   # NW = Best
    "pooja_room_dir":       0,   # removed — no pooja room
    "bathroom_direction":  10,   # NW = Best
    "dining_direction":    10,   # E/SE
    "entrance_direction":  15,   # NE/N/E
}

FITNESS_W_VASTU        = 0.45
FITNESS_W_SPACE_UTIL   = 0.25
FITNESS_W_NO_OVERLAP   = 0.20
FITNESS_W_ASPECT_RATIO = 0.10

# ── BSP zone → preferred room types ─────────────────────────────
BSP_GROUPS = {
    "NE": ["entrance"],
    "NW": ["living", "toilet", "bathroom", "toilet_master",
           "bathroom_master", "utility"],
    "SE": ["kitchen"],
    "SW": ["master_bedroom"],
    "S":  ["bedroom", "dining"],
    "E":  ["dining", "bedroom"],
    "W":  ["bedroom", "bathroom_attached", "toilet_attached"],
    "N":  ["entrance", "living"],
    "C":  [],
}