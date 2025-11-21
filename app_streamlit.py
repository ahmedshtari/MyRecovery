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

def muscle_label(muscle: str) -> str:
    """Turn 'rear_delts' into 'Rear delts', 'lower_back' into 'Lower back', etc."""
    return muscle.replace("_", " ").title()


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
        subtitle = "Showing readiness **right now**."
    else:
        readiness = compute_muscle_readiness_days_ahead(view_user_id, days_ahead)
        subtitle = (
            f"Showing readiness **{days_ahead:.1f} days** from now "
            "(assuming no new training for those muscles)."
        )

    st.caption(subtitle)

    # ----- Quick summary cards -----
    if readiness:
        muscles_sorted_fresh = sorted(
            MUSCLES, key=lambda m: readiness.get(m, 100.0), reverse=True
        )
        muscles_sorted_tired = sorted(
            MUSCLES, key=lambda m: readiness.get(m, 100.0)
        )

        most_fresh = [m for m in muscles_sorted_fresh if readiness.get(m, 0) >= 80][:3]
        most_fatigued = muscles_sorted_tired[:3]
        avg_readiness = sum(readiness.values()) / len(readiness)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric(
                "Average readiness",
                f"{avg_readiness:.1f}%",
            )
        with col_b:
            st.markdown("**🟢 Most fresh muscles**")
            for m in most_fresh:
                st.write(f"- {muscle_label(m)}: {readiness[m]:.1f}%")

        with col_c:
            st.markdown("**🔴 Most fatigued muscles**")
            for m in most_fatigued:
                st.write(f"- {muscle_label(m)}: {readiness[m]:.1f}%")


    st.markdown("---")

    # Split main area: left = table + curve, right = suggestions + recent sets
    col_left, col_right = st.columns([1.3, 1.0])

    # ===================== LEFT COLUMN =====================
    with col_left:
        # ---- MUSCLE READINESS TABLE ---- #
        st.subheader("Muscle readiness")

        rows = []
        for muscle, r in readiness.items():
            rows.append(
        {
                "Muscle": muscle_label(muscle),
                "Readiness %": round(r, 1),
                "Status": classify_muscle(r),
        }
    )


        df = pd.DataFrame(rows)
        df = df.sort_values("Readiness %")  # most fatigued at top
        st.dataframe(df, use_container_width=True)

        # Bar chart of readiness
        df_bar = df.copy()
        chart_bar = (
            alt.Chart(df_bar)
            .mark_bar()
            .encode(
                x=alt.X("Readiness %:Q", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Muscle:N", sort="-x"),
          )
)
st.altair_chart(chart_bar, use_container_width=True)

     # ---- RECOVERY CURVE FOR A SINGLE MUSCLE ---- #
    st.subheader("Recovery curve (next 7 days)")

        selected_muscle = st.selectbox(
            "Select muscle to visualize",
            options=MUSCLES,
            key="curve_muscle_select",
        )

        # build a list of days ahead: 0, 0.5, 1.0, ..., 7.0
        days_ahead_values = [round(x * 0.5, 1) for x in range(0, 15)]

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

    # ===================== RIGHT COLUMN =====================
    with col_right:
        # ---- EXERCISE SUGGESTIONS BY MUSCLE ---- #
        st.sub("Exercise suggestions")

        st.write(
            "Browse by muscle. Each section groups exercises into "
            "`full power`, `moderate`, and `fatigued`."
        )

        # slider to hide very fatigued muscles if you want
        min_readiness_for_suggestions = st.slider(
            "Show muscles with readiness at least",
            min_value=0,
            max_value=100,
            value=0,
            step=10,
            help="Filter which muscles appear in the list below.",
        )

        muscles_sorted = sorted(
            MUSCLES,
            key=lambda m: readiness.get(m, 100.0),
            reverse=True,
        )

        for muscle in muscles_sorted:
            muscle_readiness = readiness.get(muscle, 100.0)
            if muscle_readiness < min_readiness_for_suggestions:
                continue

            muscle_status = classify_muscle(muscle_readiness)

            # Collect all exercises that involve this muscle (primary / secondary / tertiary)
            muscle_exercises = []
            for ex_id, ex in EXERCISES.items():
                if (
                    muscle in ex.get("primary", [])
                    or muscle in ex.get("secondary", [])
                    or muscle in ex.get("tertiary", [])
                ):
                    status = classify_exercise(ex_id, readiness)
                    muscle_exercises.append((ex["name"], status))

            if not muscle_exercises:
                continue

            header = f"{muscle_label(muscle)} – {muscle_readiness:.1f}% ({muscle_status})"
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

        st.markdown("---")

        # ---- RECENT SETS + DELETE ---- #
        st.subheader("Recent sets")

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

            st.markdown("**Delete a set**")

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
                    key="delete_select",
                )

                if selected_label != "(none)":
                    if st.button("Delete selected set", key="delete_button"):
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
    st.title("History")

    all_sets = [s for s in get_all_sets() if s.get("user_id") == view_user_id]

    if not all_sets:
        st.info("No sets logged yet for this user.")
    else:
        # Build per-day, per-muscle "sets" with weighting:
        # primary = 1.0, secondary = 0.5, tertiary = 0.25
        rows = []
        for s in all_sets:
            ts = datetime.fromisoformat(s["timestamp"])
            d = ts.date()
            ex = EXERCISES.get(s["exercise_id"])
            if not ex:
                continue

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

            st.subheader("Weekly sets per muscle (weighted)")

            if df_week.empty:
                # No sets at all this week → all muscles at 0
                df_week_sum = pd.DataFrame({"muscle": MUSCLES, "sets": [0.0] * len(MUSCLES)})
            else:
                # Sum by muscle for this week
                df_week_sum_raw = (
                    df_week.groupby("muscle", as_index=False)["sets"].sum()
                )

                # Ensure all muscles appear, fill missing with 0.0
                df_week_sum = (
                    pd.DataFrame({"muscle": MUSCLES})
                    .merge(df_week_sum_raw, on="muscle", how="left")
                    .fillna({"sets": 0.0})
                )

            # 🔹 THIS IS YOUR SNIPPET (plus optional bar chart)
            df_week_sum["Muscle"] = df_week_sum["muscle"].apply(muscle_label)
            df_week_sum = df_week_sum[["Muscle", "sets"]].rename(columns={"sets": "Weighted sets"})

            # Optional: bar chart
            chart_week = (
                alt.Chart(df_week_sum)
                .mark_bar()
                .encode(
                    x=alt.X("Weighted sets:Q"),
                    y=alt.Y("Muscle:N", sort="-x"),
                )
            )
            st.altair_chart(chart_week, use_container_width=True)

            # Sort table and show it
            df_week_sum = df_week_sum.sort_values("Weighted sets", ascending=False)
            st.dataframe(df_week_sum, use_container_width=True)
