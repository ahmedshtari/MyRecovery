# model.py

"""
Core definitions for the app:
- MUSCLES: the muscle groups we track fatigue/recovery for
- EXERCISES: the lifts you log, with primary/secondary muscles +  (stimulus fatigue)
"""

# You can tweak this list anytime.
MUSCLES = [
    "chest",
    "traps",
    "lats",
    "front_delts",
    "side_delts",
    "rear_delts",
    "biceps",
    "triceps",
    "forearm_flexors",
    "forearm_extensors",
    "brachioradialis",
    "quads",
    "hamstrings",
    "glutes",
    "calves",
    "lower_back",
    "abs",
    "neck_flexors",
    "neck_extensors",
]


# Exercise database.
# Key = internal id (no spaces, snake_case).
# SFR = stimulus-to-fatigue ratio (higher = better).

# These are dictionaries, so two variables connected. Exercises are dictionaries
# all in one dicitonary called exercises

EXERCISES = {
    "hang_clean": {
        "name": "Hang Clean",
        "primary": ["glutes", "lower_back"],
        "secondary": ["hamstrings", "calves", "front_delts"],
        "sfr": 2.0,
    },
    "wrist_curl": {
        "name": "Wrist Curl",
        "primary": ["forearm_flexors"],
        "secondary": [],
        "sfr": 4.0,
    },
    "reverse_barbell_curl": {
        "name": "Reverse Barbell Curl",
        "primary": ["brachioradialis"],
        "secondary": ["biceps", "forearm_extensors"],
        "sfr": 3.8,
    },
    "dumbbell_pullover": {
        "name": "Dumbbell Pullover",
        "primary": ["lats", "chest", "triceps"],
        "secondary": [],
        "sfr": 3.2,
    },
    "pull_ups": {
        "name": "Pull Ups",
        "primary": ["lats", "traps"],
        "secondary": ["biceps", "rear_delts", "brachioradialis", "forearm_flexors", "abs"],
        "sfr": 3.4,
    },
    "face_pull": {
        "name": "Face Pull",
        "primary": ["rear_delts"],
        "secondary": ["traps"],
        "sfr": 4.0,
    }, #back
    "incline_dumbbell_bench_press": {
        "name": "Incline Dumbbell Bench Press",
        "primary": ["chest", "front_delts"],
        "secondary": ["triceps"],
        "sfr": 3.7,
    },
    "kettlebell_swing": {
        "name": "Kettlebell Swing",
        "primary": ["hamstrings", "glutes"],
        "secondary": ["lower_back", "quads"],
        "sfr": 2.5,
    },
    "neck_extension": {
        "name": "Neck Extension",
        "primary": ["neck_extensors"],
        "secondary": [],
        "sfr": 4.0,
    },
    "neck_curl": {
        "name": "Neck Curl",
        "primary": ["neck_flexors"],
        "secondary": [],
        "sfr": 4.0,
    },
    "bent_over_row": {
        "name": "Bent Over Row",
        "primary": ["traps"],
        "secondary": ["lats", "rear_delts", "biceps", "brachioradialis"],
        "sfr": 3.2,
    },
    "shoulder_press": {
        "name": "Shoulder Press",
        "primary": ["front_delts", "side_delts"],
        "secondary": ["triceps", "traps"],
        "sfr": 3.3,
    },
    "back_extension": {
        "name": "Back Extension",
        "primary": ["lower_back"],
        "secondary": ["glutes", "hamstrings"],
        "sfr": 3.2,
    },
    "dumbbell_lateral_raise": {
        "name": "Dumbbell Lateral Raise",
        "primary": ["side_delts"],
        "secondary": [],
        "sfr": 4.5,
    },
    "treadmill_run": {
        "name": "Treadmill Run",
        "primary": ["quads", "hamstrings", "calves"],
        "secondary": ["glutes"],
        "sfr": 2.5,
    },
    "reverse_wrist_curl": {
        "name": "Reverse Wrist Curl",
        "primary": ["forearm_extensors"],
        "secondary": [],
        "sfr": 3.8,
    },
    "nordic_hamstring_curl": {
        "name": "Nordic Hamstring Curl",
        "primary": ["hamstrings"],
        "secondary": ["glutes"],
        "sfr": 3.8,
    },
    "sled_leg_press": {
        "name": "Sled Leg Press",
        "primary": ["quads", "glutes"],
        "secondary": ["hamstrings"],
        "sfr": 4.0,
    },
    "mace_swings": {
        "name": "Mace Swings",
        "primary": ["triceps", "front_delts"],
        "secondary": ["abs", "forearm_flexors", "brachioradialis"],
        "sfr": 2.5,
    },
    "forearm_riser_rope": {
        "name": "Forearm Riser Rope",
        "primary": ["forearm_flexors", "forearm_extensors"],
        "secondary": [],
        "sfr": 3.8,
    },
    "forearm_pronations_rope": {
        "name": "Forearm Pronations Rope",
        "primary": ["forearm_extensors", "brachioradialis"],
        "secondary": [],
        "sfr": 3.8,
    },
    "bench_press": {
        "name": "Bench Press",
        "primary": ["chest"],
        "secondary": ["triceps", "front_delts"],
        "sfr": 3.5,
    },
    "incline_dumbbell_curl": {
        "name": "Incline Dumbbell Curl",
        "primary": ["biceps"],
        "secondary": ["brachioradialis", "forearm_flexors"],
        "sfr": 4.3,
    },
    "squat": {
        "name": "Squat",
        "primary": ["quads", "glutes"],
        "secondary": ["hamstrings", "lower_back"],
        "sfr": 3.0,
    },
    "cable_bicep_curl": {
        "name": "Cable Bicep Curl",
        "primary": ["biceps"],
        "secondary": ["brachioradialis", "forearm_flexors"],
        "sfr": 4.3,
    },
    "pseudo_planche_push_up": {
        "name": "Pseudo Planche Push Up",
        "primary": ["chest", "front_delts"],
        "secondary": ["triceps", "abs"],
        "sfr": 3.0,
    },
    "rear_pec_fly_with_expander": {
        "name": "Rear Pec Fly with Expander",
        "primary": ["rear_delts", "traps"],
        "secondary": [],
        "sfr": 4.0,
    },
    "deadlift": {
        "name": "Deadlift",
        "primary": ["hamstrings", "glutes", "lower_back"],
        "secondary": ["traps", "forearm_flexors", "brachioradialis"],
        "sfr": 2.0,
    },
    "dumbbell_fly": {
        "name": "Dumbbell Fly",
        "primary": ["chest"],
        "secondary": ["front_delts"],
        "sfr": 3.5,
    },
    "one_arm_pull_ups": {
        "name": "One Arm Pull Ups",
        "primary": ["lats", "traps"],
        "secondary": ["biceps", "brachioradialis", "forearm_flexors"],
        "sfr": 2.8,
    },
    "one_arm_deadhang": {
        "name": "One Arm Deadhang",
        "primary": ["forearm_flexors", "brachioradialis", "lats"],
        "secondary": [],
        "sfr": 3.0,
    },
    "incline_dumbbell_fly": {
        "name": "Incline Dumbbell Fly",
        "primary": ["chest"],
        "secondary": ["front_delts"],
        "sfr": 3.4,
    },
    "hammer_curl": {
        "name": "Hammer Curl",
        "primary": ["biceps", "brachioradialis"],
        "secondary": ["forearm_flexors"],
        "sfr": 4.2,
    },
    "paused_bench_press": {
        "name": "Paused Bench Press",
        "primary": ["chest"],
        "secondary": ["triceps", "front_delts"],
        "sfr": 3.3,
    },
    "alternating_kettlebell_hang_clean": {
        "name": "Alternating Kettlebell Hang Clean",
        "primary": ["quads", "glutes", "lower_back"],
        "secondary": ["hamstrings", "calves", "front_delts"],
        "sfr": 2.3,
    },
    "dumbbell_shoulder_press": {
        "name": "Dumbbell Shoulder Press",
        "primary": ["front_delts"],
        "secondary": ["side_delts", "triceps"],
        "sfr": 3.5,
    },
    "back_press": {
        "name": "Back Press",
        "primary": ["side_delts", "triceps"],
        "secondary": [],
        "sfr": 3.0,
    },
    "seated_cable_row": {
        "name": "Seated Cable Row",
        "primary": ["traps"],
        "secondary": ["lats", "rear_delts", "biceps"],
        "sfr": 3.8,
    },
    "overhead_pullapart_pronated": {
        "name": "Overhead Pullapart (Pronated)",
        "primary": ["rear_delts", "traps"],
        "secondary": [],
        "sfr": 4.0,
    },
    "incline_bench_press": {
        "name": "Incline Bench Press",
        "primary": ["chest", "front_delts"],
        "secondary": ["triceps"],
        "sfr": 3.5,
    },
    "lat_pulldown": {
        "name": "Lat Pulldown",
        "primary": ["lats"],
        "secondary": ["biceps", "rear_delts", "brachioradialis"],
        "sfr": 3.8,
    },
    "dips": {
        "name": "Dips",
        "primary": ["triceps", "chest"],
        "secondary": ["front_delts"],
        "sfr": 3.2,
    },
    "seated_dumbbell_shoulder_press": {
        "name": "Seated Dumbbell Shoulder Press",
        "primary": ["front_delts"],
        "secondary": ["side_delts", "triceps"],
        "sfr": 3.6,
    },
    "romanian_deadlift": {
        "name": "Romanian Deadlift",
        "primary": ["hamstrings", "glutes"],
        "secondary": ["lower_back", "forearm_flexors", "brachioradialis"],
        "sfr": 2.3,
    },
    "bicep_curl": {
        "name": "Dumbbell Bicep Curl",
        "primary": ["biceps"],
        "secondary": ["brachioradialis", "forearm_flexors"],
        "sfr": 4.5,
    },
    "tricep_pushdown": {
        "name": "Cable Tricep Pushdown",
        "primary": ["triceps"],
        "secondary": [],
        "sfr": 4.0,
    },
    "leg_press": {
        "name": "Leg Press",
        "primary": ["quads", "glutes"],
        "secondary": ["hamstrings"],
        "sfr": 4.0,
    },
    "leg_curl": {
        "name": "Leg Curl",
        "primary": ["hamstrings"],
        "secondary": [],
        "sfr": 4.0,
    },
    "calf_raise": {
        "name": "Standing Calf Raise",
        "primary": ["calves"],
        "secondary": [],
        "sfr": 4.0,
    },
    "ab_wheel": {
        "name": "Ab Wheel Rollout",
        "primary": ["abs"],
        "secondary": ["lower_back"],
        "sfr": 3.5,
    },
}

