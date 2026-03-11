import streamlit as st
from utils import (
    load_data,
    save_data,
    render_home_button,
    render_access_bar,
    admin_edit_allowed,
    build_matches_for_teams,
    reset_court_scores,
    reset_knockout,
    reset_all_scores
)

st.set_page_config(page_title="Admin", page_icon="🛠️", layout="wide")

render_home_button()
render_access_bar()

st.title("Admin Page")

if not admin_edit_allowed():
    st.warning("Read-only mode. Use Volunteer button and enter code IMF to unlock Admin access.")
    st.stop()

st.markdown("""
<style>
.section-box {
    background-color: #EAF2FF;
    padding: 14px;
    border-radius: 10px;
    border-left: 5px solid #1F4E78;
    margin-bottom: 18px;
    color: #1F1F1F;
}
.admin-card {
    background-color: white;
    border: 1px solid #d9e2f3;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
</style>
""", unsafe_allow_html=True)

data = load_data()

st.header("Tournament Controls")

teams_locked = data["settings"].get("teams_locked", False)

st.markdown(
    f'<div class="section-box"><b>Team Name Status:</b> {"Locked" if teams_locked else "Unlocked"}</div>',
    unsafe_allow_html=True
)

c1, c2 = st.columns(2)

with c1:
    if st.button("🔒 Lock Team Names", use_container_width=True):
        data["settings"]["teams_locked"] = True
        save_data(data)
        st.success("Team names locked.")
        st.rerun()

with c2:
    if st.button("🔓 Unlock Team Names", use_container_width=True):
        data["settings"]["teams_locked"] = False
        save_data(data)
        st.success("Team names unlocked.")
        st.rerun()

st.markdown("---")

st.header("Edit Team Names")

tabs = st.tabs(list(data["courts"].keys()))

for idx, court_name in enumerate(data["courts"].keys()):
    with tabs[idx]:
        court = data["courts"][court_name]
        teams = court["teams"]

        st.markdown(
            f'<div class="admin-card"><b>{court_name}</b> — {court["group"]}</div>',
            unsafe_allow_html=True
        )

        new_team_names = []

        for i, team in enumerate(teams):
            new_name = st.text_input(
                f"{court_name} Team {i+1}",
                value=team,
                key=f"{court_name}_team_{i}",
                disabled=teams_locked
            )
            new_team_names.append(new_name)

        if st.button(f"Save {court_name} Team Names", key=f"save_{court_name}", disabled=teams_locked):
            existing_matches = data["courts"][court_name]["matches"]
            data["courts"][court_name]["teams"] = new_team_names
            data["courts"][court_name]["matches"] = build_matches_for_teams(new_team_names, existing_matches)
            save_data(data)
            st.success(f"{court_name} team names updated.")
            st.rerun()

st.markdown("---")

st.header("Reset Controls")

court_options = list(data["courts"].keys())
selected_court = st.selectbox("Select a court to reset", court_options)

r1, r2, r3 = st.columns(3)

with r1:
    if st.button("Reset Selected Court Scores", use_container_width=True):
        data = reset_court_scores(data, selected_court)
        save_data(data)
        st.success(f"{selected_court} scores reset.")
        st.rerun()

with r2:
    if st.button("Reset Knockout Scores", use_container_width=True):
        data = reset_knockout(data)
        save_data(data)
        st.success("Knockout scores reset.")
        st.rerun()

with r3:
    if st.button("Reset Entire Tournament", use_container_width=True):
        data = reset_all_scores(data)
        save_data(data)
        st.success("Entire tournament scores reset.")
        st.rerun()

st.markdown("---")

st.header("Current Team Snapshot")

for court_name, court in data["courts"].items():
    st.subheader(f"{court_name} — {court['group']}")
    for i, team in enumerate(court["teams"], start=1):
        st.write(f"{i}. {team}")