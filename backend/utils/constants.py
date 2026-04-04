# ═══════════════════════════════════════════════════════════════
# utils/constants.py
# ═══════════════════════════════════════════════════════════════

ROOM_TYPES = [
    "entrance", "living", "dining", "kitchen",
    "master_bedroom", "bedroom",
    "bathroom", "toilet",
    "bathroom_master", "toilet_master",
    "bathroom_attached", "toilet_attached",
    "pooja", "utility",
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
    "pooja":               "Pooja Room",
    "utility":             "Utility Room",
}

# ── BHK compositions ─────────────────────────────────────────────
# Rules:
#   • NO balcony, NO store room in any plan
#   • Living room is the hall (biggest room)
#   • Kitchen + Dining always adjacent
#   • Pooja room is small
#   • 1BHK: 1 common bathroom + toilet
#   • 2BHK: 1 common bathroom + toilet
#   • 3BHK: 1 common (bathroom + toilet)
#            + 1 attached to master (bathroom_master + toilet_master)
#   • 4BHK: 1 common (bathroom + toilet)
#            + 1 attached to master (bathroom_master + toilet_master)
#            + 1 attached to bedroom 2 (bathroom_attached + toilet_attached)
BHK_ROOM_COMPOSITIONS = {
    "1BHK": [
        "entrance", "living", "kitchen",
        "master_bedroom",
        "bathroom", "toilet",
        "pooja",
    ],
    "2BHK": [
        "entrance", "living", "dining", "kitchen",
        "master_bedroom", "bedroom",
        "bathroom", "toilet",
        "pooja",
    ],
    "3BHK": [
        "entrance", "living", "dining", "kitchen",
        "master_bedroom", "bedroom", "bedroom",
        "bathroom_master", "toilet_master",   # attached to master
        "bathroom", "toilet",                  # common
        "pooja",
    ],
    "4BHK": [
        "entrance", "living", "dining", "kitchen",
        "master_bedroom", "bedroom", "bedroom", "bedroom",
        "bathroom_master", "toilet_master",    # attached to master bedroom
        "bathroom_attached", "toilet_attached",# attached to bedroom 2
        "bathroom", "toilet",                  # common
        "pooja", "utility",
    ],
}

# ── Minimum room sizes (ft × ft) ────────────────────────────────
# Living room min kept large; pooja/toilet/bathroom kept small
ROOM_MIN_SIZES = {
    "entrance":            (5.0,  6.0),
    "living":              (14.0, 16.0),   # hall — must be largest
    "dining":              (9.0,  9.0),
    "kitchen":             (8.0,  9.0),
    "master_bedroom":      (11.0, 12.0),
    "bedroom":             (10.0, 11.0),
    "bathroom":            (5.0,  5.0),   # small
    "toilet":              (4.0,  4.0),   # small
    "bathroom_master":     (5.0,  5.0),   # small — attached to master
    "toilet_master":       (4.0,  4.0),   # small — attached to master
    "bathroom_attached":   (5.0,  5.0),   # small — attached to bedroom
    "toilet_attached":     (4.0,  4.0),   # small — attached to bedroom
    "pooja":               (4.0,  4.0),   # small corner room
    "utility":             (5.0,  6.0),
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
    "pooja":               (1.0, 1.0),
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

# ── Vastu rule weights (derived from reference Vastu images) ─────
# Image 1: Basics of Vasthu  |  Image 2: Room-zone grid
# Image 3: Ideal Placement table (Best / Good / x)
# Total = 120; normalised to 0–100 in vastu_score.py
VASTU_RULE_WEIGHTS = {
    "kitchen_direction":   15,   # Image 3: Kitchen  → Best = SE
    "master_bedroom_dir":  20,   # Image 3: Master Bed → Best = SW
    "living_room_dir":     15,   # Image 3: Living Room → Best = NW
    "pooja_room_dir":      15,   # Image 3: Temple/Pooja → Best = NE
    "bathroom_direction":  10,   # Image 3: Bathroom/Toilet → Best = NW
    "dining_direction":    10,   # Image 2: Dining in E / S
    "entrance_direction":  15,   # Image 1: Good Entry = NE / N / E
}

FITNESS_W_VASTU        = 0.45
FITNESS_W_SPACE_UTIL   = 0.25
FITNESS_W_NO_OVERLAP   = 0.20
FITNESS_W_ASPECT_RATIO = 0.10

# ── BSP zone → preferred room types (priority order) ─────────────
# NE : Pooja, Entrance  (Light, low, auspicious — Image 1)
# NW : Living (Best per Image 3), Toilet/Bathroom, Utility
# SE : Kitchen (Best per Image 3)
# SW : Master Bedroom (Heavy, high — Best per Image 3)
# S  : Secondary Bedrooms, Dining
# E  : Dining, Bedroom
# W  : Bedroom
# N  : Entrance, Living
# C  : Brahmasthana — keep open
BSP_GROUPS = {
    "NE": ["pooja", "entrance"],
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