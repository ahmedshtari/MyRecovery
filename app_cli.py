# app_cli.py

"""
Tiny menu app so you can actually use the recovery system.

Options:
1) Log workout sets
2) Log today's sleep + steps
3) Show today's muscle readiness + exercise suggestions
4) Exit
"""

from model import EXERCISES
from storage import log_set, log_daily_recovery
from recovery_logic import (
    compute_current_muscle_readiness,
    classify_muscle,
    classify_exercise,
)

USER_ID = "Ahmed"  # change if you ever add friends later


def list_exercises():
    """Print all available exercises with their ids."""
    print("\nAvailable exercises:")
    for ex_id, ex in EXERCISES.items():
        print(f"- {ex_id:35} -> {ex['name']}")
    print()


def choose_exercise_id() -> str:
    """Ask user to pick an exercise id, with a simple loop."""
    while True:
        list_exercises()
        ex_id = input("Type exercise ID (exact, or 'q' to cancel): ").strip()
        if ex_id.lower() == "q":
            return ""
        if ex_id in EXERCISES:
            return ex_id
        print("❌ Unknown exercise id, try again.\n")


def log_workout_sets():
    """Log one or more sets for a chosen exercise."""
    ex_id = choose_exercise_id()
    if not ex_id:
        print("Cancelled logging sets.\n")
        return

    ex_name = EXERCISES[ex_id]["name"]
    print(f"\nLogging sets for: {ex_name}\n")

    while True:
        try:
            reps = int(input("Reps (or 0 to stop): "))
        except ValueError:
            print("Please type a number.\n")
            continue

        if reps == 0:
            break

        try:
            weight = float(input("Weight (kg): "))
        except ValueError:
            print("Please type a number.\n")
            continue

        rir_input = input("RIR (0–5, blank if unknown): ").strip()
        if rir_input == "":
            rir = None
        else:
            try:
                rir = int(rir_input)
            except ValueError:
                print("Invalid RIR, using None.")
                rir = None

        log_set(USER_ID, ex_id, reps=reps, weight=weight, rir=rir)
        print("✅ Set logged.\n")

    print("Done logging sets.\n")


def log_today_recovery():
    """Log sleep + steps for today."""
    sleep_input = input("Sleep hours last night (e.g. 7.5, blank if unknown): ").strip()
    if sleep_input == "":
        sleep_hours = None
    else:
        try:
            sleep_hours = float(sleep_input)
        except ValueError:
            print("Invalid, using None.")
            sleep_hours = None

    steps_input = input("Steps yesterday (e.g. 9000, blank if unknown): ").strip()
    if steps_input == "":
        steps = None
    else:
        try:
            steps = int(steps_input)
        except ValueError:
            print("Invalid, using None.")
            steps = None

    log_daily_recovery(USER_ID, sleep_hours=sleep_hours, steps=steps)
    print("✅ Daily recovery saved.\n")


def show_today():
    """Print muscle readiness and classify exercises."""
    readiness = compute_current_muscle_readiness(USER_ID)

    print("\n=== MUSCLE READINESS ===")
    # sort by readiness ascending so the most fatigued appear first
    for muscle, r in sorted(readiness.items(), key=lambda x: x[1]):
        status = classify_muscle(r)
        print(f"{muscle:20} {r:5.1f}%  {status}")

    print("\n=== EXERCISE SUGGESTIONS ===")
    buckets = {"full_power": [], "moderate": [], "fatigued": []}

    for ex_id, ex in EXERCISES.items():
        status = classify_exercise(ex_id, readiness)
        buckets[status].append(ex["name"])

    print("\nFULL POWER:")
    for name in buckets["full_power"]:
        print(f"- {name}")

    print("\nMODERATE:")
    for name in buckets["moderate"]:
        print(f"- {name}")

    print("\nFATIGUED / PROBABLY SKIP AS MAIN LIFT:")
    for name in buckets["fatigued"]:
        print(f"- {name}")

    print()


def main():
    while True:
        print("=== Muscle Recovery App ===")
        print("1) Log workout sets")
        print("2) Log today's sleep + steps")
        print("3) Show today's readiness + exercise suggestions")
        print("4) Exit")

        choice = input("Choose an option (1–4): ").strip()

        if choice == "1":
            log_workout_sets()
        elif choice == "2":
            log_today_recovery()
        elif choice == "3":
            show_today()
        elif choice == "4":
            print("Goodbye.")
            break
        else:
            print("Unknown option, try again.\n")


if __name__ == "__main__":
    main()
