# recovery_logic.py

"""
Recovery / fatigue math.

Takes:
- logged sets (from storage.get_all_sets)
- daily sleep + steps (from storage.get_all_daily)

Outputs:
- per-muscle readiness 0–100
- classification for muscles (fresh / slightly_fatigued / fatigued)
- classification for exercises (full_power / moderate / fatigued)
"""
from collections import defaultdict
from datetime import datetime, timedelta
from math import exp, log
from typing import Dict, Optional

from model import EXERCISES, MUSCLES
from storage import get_all_sets, get_all_daily

# ---- Recovery parameters ----

# Fallback half-life (days) if muscle not listed explicitly
DEFAULT_HALF_LIFE_DAYS = 2.0  # ~48h

# Per-muscle half-lives (days) – small muscles faster, big ones slower
MUSCLE_HALF_LIFE_DAYS = {
    # Big lower body
    "quads": 2.7,
    "hamstrings": 2.7,
    "glutes": 2.7,
    "calves": 2.3,
    "lower_back": 2.8,

    # Big upper
    "back": 2.3,
    "lats": 2.2,
    "chest": 2.2,

    # Delts
    "front_delts": 2.0,
    "side_delts": 1.8,
    "rear_delts": 1.8,

    # Arms & small upper
    "biceps": 1.6,
    "triceps": 1.6,

    # Forearm complex
    "forearm_flexors": 1.3,
    "forearm_extensors": 1.3,
    "brachioradialis": 1.3,

    # Neck & trunk
    "neck_flexors": 1.6,
    "neck_extensors": 1.6,
    "abs": 1.5,
}


def get_half_life_days(muscle: str) -> float:
    return MUSCLE_HALF_LIFE_DAYS.get(muscle, DEFAULT_HALF_LIFE_DAYS)


# After this many days, any session is treated as fully recovered
RECOVERY_HORIZON_DAYS = 5.0


# ---- Helper functions ----

def effort_multiplier_from_rir(rir: Optional[int]) -> float:
    """Map RIR to how hard the set was."""
    if rir is None:
        return 0.7
    if rir >= 4:
        return 0.4
    if rir == 3:
        return 0.6
    if rir == 2:
        return 0.8
    if rir == 1:
        return 1.0
    if rir <= 0:
        return 1.2
    return 0.7


def sleep_factor(hours: Optional[float]) -> float:
    """How sleep that night affects recovery speed."""
    if hours is None:
        return 1.0
    if hours < 6:
        return 0.7
    if hours < 7.5:
        return 1.0
    if hours <= 9:
        return 1.1
    return 0.95


def steps_factor(steps: Optional[int]) -> float:
    """How steps that day affect recovery speed (esp. legs)."""
    if steps is None:
        return 1.0
    if steps < 3000:
        return 0.8
    if steps <= 10000:
        return 1.0
    if steps <= 15000:
        return 0.95
    return 0.9


def classify_muscle(readiness: float) -> str:
    """
    Turn a readiness % into a descriptive label with emojis.

    Bands:
    - 95–100: 🟢 FULLY FRESH
    - 80–94.9: 🟢 ALMOST FRESH
    - 60–79.9: 🟡 SLIGHTLY FATIGUED
    - 40–59.9: 🟠 MODERATLY FATIGUED
    - 0: 💀 YOU DESTROYED THIS MUSCLE
    - 0.1–39.9: 🔴 VERY FATIGUED
    """
    if readiness >= 95:
        return "🟢 FULLY FRESH"
    if readiness >= 80:
        return "🟢 ALMOST FRESH"
    if readiness >= 60:
        return "🟡 SLIGHTLY FATIGUED"
    if readiness >= 40:
        return "🟠 MODERATLY FATIGUED"
    if readiness == 0:
        return "💀 YOU DESTROYED THIS MUSCLE"
    return "🔴 VERY FATIGUED"


# ---- Core readiness computation ----

def compute_current_muscle_readiness(
    user_id: str,
    as_of: Optional[datetime] = None,
) -> Dict[str, float]:
    """
    Return {muscle_name: readiness_percent} for the given user,
    as of a given time. If as_of is None, use current time.

    Readiness is 100 - fatigue, clamped 0–100, with tiny fatigue treated as 0.
    """
    if as_of is None:
        as_of = datetime.now()

    sets = [s for s in get_all_sets() if s.get("user_id") == user_id]
    daily = [d for d in get_all_daily() if d.get("user_id") == user_id]

    # quick lookup: date -> {sleep_hours, steps}
    daily_by_date = {d["date"]: d for d in daily if "date" in d}

    # accumulate fatigue per muscle
    fatigue = defaultdict(float)

    for s in sets:
        ts = datetime.fromisoformat(s["timestamp"])
        days_since = (as_of - ts).total_seconds() / 86400.0

        # Skip weird future timestamps
        if days_since < 0:
            continue

        # Hard recovery horizon: ignore sets older than RECOVERY_HORIZON_DAYS
        if days_since >= RECOVERY_HORIZON_DAYS:
            continue

        date_key = ts.date().isoformat()
        day_info = daily_by_date.get(date_key)

        sf = sleep_factor(day_info["sleep_hours"]) if day_info else 1.0
        stf = steps_factor(day_info["steps"]) if day_info else 1.0

        ex_id = s["exercise_id"]
        ex = EXERCISES.get(ex_id)
        if ex is None:
            # unknown exercise id, ignore
            continue

        sfr = float(ex["sfr"])
        # higher SFR = less fatigue cost per set
        fatigue_factor = 1.0 / sfr

        effort_mult = effort_multiplier_from_rir(s.get("rir"))
        # base "size" of this set before decay
        base_set_fatigue = effort_mult * fatigue_factor

        # Primary and secondary muscles, with their weights
        muscles_and_weights = (
            [(m, 1.0) for m in ex.get("primary", [])]
            + [(m, 0.5) for m in ex.get("secondary", [])]
        )

        for muscle, weight in muscles_and_weights:
            # per-muscle half-life
            half_life = get_half_life_days(muscle)
            base_lambda = log(2.0) / half_life

            # day-level modifiers (sleep, steps)
            effective_lambda = base_lambda * sf * stf

            decay = exp(-effective_lambda * days_since)
            contrib_now = base_set_fatigue * weight * decay

            fatigue[muscle] += contrib_now

    # convert raw fatigue → readiness 0–100
    readiness: Dict[str, float] = {}
    SCALE_PER_UNIT = 60.0  # tune overall "aggressiveness"
    EPS = 9.9              # % fatigue: treat less than this as fully recovered

    for m in MUSCLES:
        raw = fatigue[m]
        scaled_fatigue = raw * SCALE_PER_UNIT

        # If fatigue is tiny, treat as fully recovered
        if scaled_fatigue < EPS:
            scaled_fatigue = 0.0
        else:
            scaled_fatigue = min(scaled_fatigue, 100.0)

        r = max(0.0, 100.0 - scaled_fatigue)
        readiness[m] = r

    return readiness


def compute_muscle_readiness_days_ahead(user_id: str, days_ahead: float) -> Dict[str, float]:
    """
    Convenience helper: readiness as if 'days_ahead' days have passed.
    """
    as_of = datetime.now() + timedelta(days=days_ahead)
    return compute_current_muscle_readiness(user_id, as_of=as_of)


def classify_exercise(exercise_id: str, muscle_readiness: Dict[str, float]) -> str:
    """
    Classify an exercise based on its muscles’ readiness:
    - full_power
    - moderate
    - fatigued
    """
    ex = EXERCISES[exercise_id]
    prim = ex.get("primary", [])
    sec = ex.get("secondary", [])

    prim_ready_full = all(muscle_readiness.get(m, 100.0) >= 80.0 for m in prim)
    sec_ready_full = all(muscle_readiness.get(m, 100.0) >= 60.0 for m in sec)
    if prim_ready_full and sec_ready_full:
        return "full_power"

    prim_ready_mod = all(muscle_readiness.get(m, 100.0) >= 60.0 for m in prim)
    sec_ready_mod = all(muscle_readiness.get(m, 100.0) >= 50.0 for m in sec)
    if prim_ready_mod and sec_ready_mod:
        return "moderate"

    return "fatigued"

