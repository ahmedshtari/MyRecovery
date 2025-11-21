# app_streamlit.py

import streamlit as st
from auth import create_user, verify_user, _load_users
import pandas as pd
from model import EXERCISES, MUSCLES
from datetime import datetime, date, timedelta
import altair as alt
from storage import log_set, get_all_sets, delete_set_by_id
from recovery_logic import (
    compute_current_muscle_readiness,
    compute_muscle_readiness_days_ahead,
    classify_muscle,
    classify_exercise,
)

# Who is allowed to use the admin tools
ADMIN_USERS = {"Ahmed"}


def login_screen():
    """Simple login / signup form using Streamlit session state."""
    st.title("Muscle Recovery Dashboard – Login")
    st.info("Use a unique password you don't reuse anywhere else.")

    mode = st.radio("Mode", ["Log in", "Create account"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Create account":
        password2 = st.text_input("Confirm password", type="password")

        if st.button("Create account"):
            if password != password2:
                st.error("Passwords do not match.")
            else:
                ok, msg = create_user(username, password)
                if ok:
                    st.success(msg)
                    st.info("You can now switch to 'Log in' and sign in.")
                else:
                    st.error(msg)

    else:  # Log in
        if st.button("Log in"):
            if verify_user(username, password):
                st.session_state["user_id"] = username.strip()
                st.rerun()
            else:
                st.error("Invalid username or password.")


st.set_page_config(
    page_title="Muscle Recovery Dashboard",
    layout="wide",
)

# ---- AUTH GATE ---- #

if "user_id" not in st.session_state:
    login_screen()
    st.stop()

USER_ID = st.session_state["user_id"]

# ---- ADMIN IMPERSONATION (VIEW OTHER USERS' DATA) ---- #

# By default, you view your own data
view_user_id = USER_ID

if USER_ID in ADMIN_USERS:
    st.sidebar.markdown("### Admin tools")
    st.sidebar.markdown("**View data for user:**")

    users_data = _load_users()
    usernames = [u.get("username") for u in users_data.get("users", [])]

    if usernames:
        default_idx = usernames.index(USER_ID) if USER_ID in usernames else 0

        selected_view_user = st.sidebar.selectbox(
            "Select user to view",
            options=usernames,
            index=default_idx,
        )

        view_user_id = selected_view_user

    st.sidebar.caption(f"Viewing data for: `{view_user_id}`")
else:
    st.sidebar.caption(f"Viewing data for: `{view_user_id}`")

# ----- SIDEBAR: INPUTS / LOGGING ----- #

st.sidebar.markdown(f"**Logged in as:** `{USER_ID}`")
if st.sidebar.button("Log out"):
    st.session_state.pop("user_id", None)
    st.rerun()

st.sidebar.title("Log data")

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

# ---------------------- MAIN LAYOUT ---------------------- #

tab_dashboard, tab_history = st.tabs(["Dashboard", "History"])

# =========================================================
# DASHBOARD TAB
# =========================================================
with tab_dashboard:
    st.title("Muscle Recovery Dashboard")

    # ----- Time simulation slider -----
    days_ahead = st.slider(
        "Simulate days ahead",
        min_value=0.0,
        max_value=7.0,
        value=0.0,
        step=0.5,
        help="0 = right now, 1 = tomorrow, up to one week ahead (assuming no new training).",
    )

    if days_ahead == 0.0:
        readiness = compute_current_muscle_readiness(view_user_id)
        st.caption("Showing readiness **right now**.")
    else:
        readiness = compute_muscle_readiness_days_ahead(view_user_id, days_ahead)
        st.caption(
            f"Showing readiness **{days_ahead:.1f} days** from now "
            "(assuming no new training for those muscles)."
        )

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
            if (
                muscle in ex.get("primary", [])
                or muscle in ex.get("secondary", [])
                or muscle in ex.get("tertiary", [])
            ):
                status = classify_exercise(ex_id, readiness)
                muscle_exercises.append((ex["name"], status))

        # Skip muscles that have no mapped exercises at all
        if not muscle_exercises:
            continue

        header = f"{muscle} – {muscle_readiness:.1f}% ({muscle_status})"
        with st.expander(header, expanded=False):
            status_buckets = {"full_power": [], "moderate": [], "fatigued": []}
            for name, status in muscle_exercises:
                status_buckets[status].append(name)

            st.markdown("**✅ Full power**")
            if status_buckets["full_power"]:
                for name in sorted(status_buckets["full_power"]):
                    st.write(f"- {name}")
            else:
                st.write("_None_")

            st.markdown("**🟡 Moderate**")
            if status_buckets["moderate"]:
                for name in sorted(status_buckets["moderate"]):
                    st.write(f"- {name}")
            else:
                st.write("_None_")

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
        r_future = compute_muscle_readiness_days_ahead(view_user_id, d)
        curve_rows.append(
            {
                "Days ahead": d,
                "Readiness %": r_future.get(selected_muscle, 100.0),
            }
        )

    df_curve = pd.DataFrame(curve_rows)

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

    all_sets = [s for s in get_all_sets() if s.get("user_id") == view_user_id]
    all_sets = sorted(all_sets, key=lambda s: s["timestamp"], reverse=True)
    recent = all_sets[:20]

    if recent:
        set_rows = []
        for s in recent:
            ex = EXERCISES.get(s["exercise_id"], {"name": s["exercise_id"]})
            set_rows.append(
                {
                    "ID": s.get("id", ""),
                    "Time": s["timestamp"],
                    "Exercise": ex["name"],
                    "Reps": s["reps"],
                    "Weight": s["weight"],
                    "RIR": s["rir"],
                }
            )

        df_sets = pd.DataFrame(set_rows)
        st.dataframe(df_sets.drop(columns=["ID"]), use_container_width=True)

        st.markdown("### Delete a set")

        options = {
            f"{row['Time']} – {row['Exercise']} ({row['Reps']}x{row['Weight']}kg @ RIR {row['RIR']})": row["ID"]
            for row in set_rows
            if row["ID"]
        }

        if options:
            selected_label = st.selectbox(
                "Select a set to delete",
                options=["(none)"] + list(options.keys()),
                index=0,
            )

            if selected_label != "(none)":
                if st.button("Delete selected set"):
                    set_id = options[selected_label]
                    ok = delete_set_by_id(view_user_id, set_id)
                    if ok:
                        st.success("Set deleted ✅")
                        st.rerun()
                    else:
                        st.error("Could not delete set (maybe it was already removed).")
        else:
            st.write("No deletable sets (old entries might be missing IDs).")
    else:
        st.write("No sets logged yet.")

# =========================================================
# HISTORY TAB
# =========================================================
with tab_history:
    st.title("History & Weekly Calendar")

    all_sets = [s for s in get_all_sets() if s.get("user_id") == view_user_id]

    if not all_sets:
        st.info("No sets logged yet for this user.")
    else:
        rows = []
        for s in all_sets:
            ts = datetime.fromisoformat(s["timestamp"])
            d = ts.date()
            ex = EXERCISES.get(s["exercise_id"])
            if not ex:
                continue

            # primary = 1.0, secondary = 0.5, tertiary = 0.25
            for m in ex.get("primary", []):
                rows.append({"date": d, "muscle": m, "sets": 1.0})
            for m in ex.get("secondary", []):
                rows.append({"date": d, "muscle": m, "sets": 0.5})
            for m in ex.get("tertiary", []):
                rows.append({"date": d, "muscle": m, "sets": 0.25})

        if not rows:
            st.info("No muscle data found for this user's sets.")
        else:
            df_hist = pd.DataFrame(rows)
            df_hist = df_hist.groupby(["date", "muscle"], as_index=False)["sets"].sum()

            today = date.today()
            selected_day = st.date_input(
                "Pick a date to inspect its week",
                value=today,
            )

            # Monday of that week
            week_start = selected_day - timedelta(days=selected_day.weekday())
            week_days = [week_start + timedelta(days=i) for i in range(7)]

            st.markdown(
                f"### Week of {week_start.strftime('%d.%m.%Y')} "
                f"to {(week_start + timedelta(days=6)).strftime('%d.%m.%Y')}"
            )

            df_week = df_hist[df_hist["date"].isin(week_days)]

            # Weekly sets per muscle
            st.subheader("Weekly sets per muscle (weighted)")

            if df_week.empty:
                st.info("No sets logged in this week.")
            else:
                df_week_sum = (
                    df_week.groupby("muscle", as_index=False)["sets"].sum()
                    .sort_values("sets", ascending=False)
                )
                st.dataframe(df_week_sum, use_container_width=True)

                # Calendar-style week row
                st.subheader("Weekly calendar (per day)")

                cols = st.columns(7)
                for i, day in enumerate(week_days):
                    with cols[i]:
                        st.markdown(f"**{day.strftime('%a %d.%m')}**")

                        df_day = df_week[df_week["date"] == day]
                        if df_day.empty:
                            st.caption("Rest / no logged sets")
                        else:
                            df_day_sum = (
                                df_day.groupby("muscle", as_index=False)["sets"].sum()
                                .sort_values("sets", ascending=False)
                            )
                            for _, row in df_day_sum.head(5).iterrows():
                                muscle = row["muscle"]
                                sets_val = row["sets"]
                                st.write(f"- {muscle}: {sets_val:.1f} sets")
