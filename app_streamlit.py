
# app_streamlit.py

import streamlit as st
import pandas as pd
from model import EXERCISES, MUSCLES
from datetime import datetime
import altair as alt
from storage import log_set, log_daily_recovery, get_all_sets, delete_set_by_timestamp
from recovery_logic import (
    compute_current_muscle_readiness,
    compute_muscle_readiness_days_ahead,
    classify_muscle,
    classify_exercise,
)

# Simple in-file user "database".
# Change these usernames/passwords to whatever you want.
VALID_USERS = {
    "Ahmed": "password123",
    "Mitchell": "password123",
    "Radek": "password123",
    "Wiktoria": "password123",
    "Immanuel": "password123",
    "Arun": "password123",
    "Anjika": "password123"
}


def login_screen():
    """Very simple login form using Streamlit session state."""
    st.title("Muscle Recovery Dashboard – Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        if username in VALID_USERS and VALID_USERS[username] == password:
            st.session_state["user_id"] = username
            st.rerun()
        else:
            st.error("Invalid username or password")


st.set_page_config(
    page_title="Muscle Recovery Dashboard",
    layout="wide",
)


if "user_id" not in st.session_state:
    login_screen()
    st.stop()

USER_ID = st.session_state["user_id"]

# ----- SIDEBAR: INPUTS / LOGGING ----- #

st.sidebar.markdown(f"**Logged in as:** `{USER_ID}`")
if st.sidebar.button("Log out"):
    st.session_state.pop("user_id", None)
    st.rerun()

st.sidebar.title("Log data")


st.sidebar.subheader("Today's recovery (sleep + steps)")
sleep_hours = st.sidebar.number_input(
    "Sleep last night (hours)",
    min_value=0.0,
    max_value=24.0,
    value=7.5,
    step=0.25,
)
steps = st.sidebar.number_input(
    "Steps yesterday",
    min_value=0,
    max_value=200_000,
    value=9000,
    step=500,
)

if st.sidebar.button("Save sleep & steps"):
    log_daily_recovery(USER_ID, sleep_hours=sleep_hours, steps=steps)
    st.sidebar.success("Saved daily recovery ✅")
    
    
st.sidebar.subheader("Log a set")

# build options like "Bench Press (bench_press)"
exercise_options = {
    f"{ex['name']} ({ex_id})": ex_id for ex_id, ex in EXERCISES.items()
}
selected_label = st.sidebar.selectbox(
    "Exercise",
    options=sorted(exercise_options.keys()),
)
selected_ex_id = exercise_options[selected_label]

reps = st.sidebar.number_input(
    "Reps",
    min_value=1,
    max_value=100,
    value=8,
)
weight = st.sidebar.number_input(
    "Weight (kg)",
    min_value=0.0,
    max_value=1000.0,
    value=60.0,
)

rir_input = st.sidebar.number_input(
    "RIR (0–5, use 3 if unsure)",
    min_value=0,
    max_value=5,
    value=2,
)

# Custom time controls
use_custom_time = st.sidebar.checkbox("Log this set at a custom time", value=False)

if use_custom_time:
    set_date = st.sidebar.date_input("Date of set")
    set_time = st.sidebar.time_input("Time of set")
else:
    set_date = None
    set_time = None

if st.sidebar.button("Add set"):
    # Build timestamp if custom time is used
    ts = None
    if use_custom_time and set_date is not None and set_time is not None:
        ts = datetime.combine(set_date, set_time)

    log_set(
        USER_ID,
        selected_ex_id,
        reps=int(reps),
        weight=float(weight),
        rir=int(rir_input),
        timestamp=ts,
    )
    st.sidebar.success("Set logged ✅")


# ----- MAIN LAYOUT ----- #

st.title("Muscle Recovery Dashboard")

# Slider to simulate future recovery
days_ahead = st.slider(
    "Simulate days ahead",
    min_value=0.0,
    max_value=7.0,
    value=0.0,
    step=0.5,
    help="0 = right now, 1 = tomorrow, 2 = in two days, up to one week.",
)

if days_ahead == 0.0:
    readiness = compute_current_muscle_readiness(USER_ID)
    st.caption("Showing readiness **right now**.")
else:
    readiness = compute_muscle_readiness_days_ahead(USER_ID, days_ahead)
    st.caption(f"Showing readiness **{days_ahead:.1f} days** from now (assuming no new training).")


# ---- MUSCLE READINESS TABLE ---- #

st.subheader("Muscle readiness")

rows = []
for muscle, r in readiness.items():
    rows.append(
        {
            "Muscle": muscle,
            "Readiness %": round(r, 1),
            "Status": classify_muscle(r),
        }
    )

df = pd.DataFrame(rows)
df = df.sort_values("Readiness %")  # most fatigued at top

st.dataframe(df, use_container_width=True)




# ---- EXERCISE SUGGESTIONS BY MUSCLE ---- #

st.subheader("Exercise suggestions by muscle group")

st.write(
    "Each section shows exercises that hit that muscle, split into "
    "`full power`, `moderate`, and `fatigued` based on your current recovery."
)

# Sort muscles by readiness: least fatigued (highest readiness) first
muscles_sorted = sorted(
    MUSCLES,
    key=lambda m: readiness.get(m, 100.0),
    reverse=True,  # highest readiness → lowest
)

for muscle in muscles_sorted:
    muscle_readiness = readiness.get(muscle, 100.0)
    muscle_status = classify_muscle(muscle_readiness)

    # Collect all exercises that involve this muscle
    muscle_exercises = []
    for ex_id, ex in EXERCISES.items():
        if muscle in ex["primary"] or muscle in ex["secondary"]:
            status = classify_exercise(ex_id, readiness)
            muscle_exercises.append((ex["name"], status))

    # Skip muscles that have no mapped exercises at all
    if not muscle_exercises:
        continue

    # Expander per muscle group
    header = f"{muscle} – {muscle_readiness:.1f}% ({muscle_status})"
    with st.expander(header, expanded=False):
        # Group by status
        status_buckets = {"full_power": [], "moderate": [], "fatigued": []}
        for name, status in muscle_exercises:
            status_buckets[status].append(name)

        # Full power
        st.markdown("**✅ Full power**")
        if status_buckets["full_power"]:
            for name in sorted(status_buckets["full_power"]):
                st.write(f"- {name}")
        else:
            st.write("_None_")

        # Moderate
        st.markdown("**🟡 Moderate**")
        if status_buckets["moderate"]:
            for name in sorted(status_buckets["moderate"]):
                st.write(f"- {name}")
        else:
            st.write("_None_")

        # Fatigued
        st.markdown("**🔴 Fatigued / deprioritize**")
        if status_buckets["fatigued"]:
            for name in sorted(status_buckets["fatigued"]):
                st.write(f"- {name}")
        else:
            st.write("_None_")
            
# ---- RECOVERY CURVE FOR A SINGLE MUSCLE ---- #

st.subheader("Recovery curve for one muscle (next 7 days)")

selected_muscle = st.selectbox(
    "Select muscle to visualize",
    options=MUSCLES,
)

# build a list of days ahead: 0, 0.5, 1.0, ..., 7.0
days_ahead_values = [round(x * 0.5, 1) for x in range(0, 15)]  # 0 to 7.0 in 0.5 steps

curve_rows = []
for d in days_ahead_values:
    r_future = compute_muscle_readiness_days_ahead(USER_ID, d)
    curve_rows.append(
        {
            "Days ahead": d,
            "Readiness %": r_future.get(selected_muscle, 100.0),
        }
    )

df_curve = pd.DataFrame(curve_rows)

# Fixed-scale, non-zoomable line chart
chart = (
    alt.Chart(df_curve)
    .mark_line()
    .encode(
        x=alt.X("Days ahead:Q", scale=alt.Scale(domain=[0, 7])),
        y=alt.Y("Readiness %:Q", scale=alt.Scale(domain=[0, 100])),
    )
)

st.altair_chart(chart, use_container_width=True)

# ---- RECENT SETS + DELETE ---- #

st.subheader("Recent logged sets")

all_sets = [s for s in get_all_sets() if s["user_id"] == USER_ID]
# sort by timestamp descending
all_sets = sorted(all_sets, key=lambda s: s["timestamp"], reverse=True)
recent = all_sets[:20]

if recent:
    set_rows = []
    for s in recent:
        ex = EXERCISES.get(s["exercise_id"], {"name": s["exercise_id"]})
        set_rows.append(
            {
                "Time": s["timestamp"],
                "Exercise": ex["name"],
                "Reps": s["reps"],
                "Weight": s["weight"],
                "RIR": s["rir"],
            }
        )

    df_sets = pd.DataFrame(set_rows)
    st.dataframe(df_sets, use_container_width=True)

    # Build dropdown for deletion
    st.markdown("### Delete a set")

    # label each set with a readable string, map -> timestamp
    options = {
        f"{row['Time']} – {row['Exercise']} ({row['Reps']}x{row['Weight']}kg @ RIR {row['RIR']})": row["Time"]
        for row in set_rows
    }

    selected_label = st.selectbox(
        "Select a set to delete",
        options=["(none)"] + list(options.keys()),
        index=0,
    )

    if selected_label != "(none)":
        if st.button("Delete selected set"):
            ts = options[selected_label]
            ok = delete_set_by_timestamp(USER_ID, ts)
            if ok:
                st.success("Set deleted ✅")
                # Force refresh so table updates
                st.rerun()
            else:
                st.error("Could not delete set (maybe it was already removed).")
else:
    st.write("No sets logged yet.")

