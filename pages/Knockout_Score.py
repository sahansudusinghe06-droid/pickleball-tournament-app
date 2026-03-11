import streamlit as st
import pandas as pd
from utils import (
    load_data,
    save_data,
    compute_standings,
    render_home_button,
    render_access_bar,
    admin_edit_allowed
)

st.set_page_config(page_title="Knockout Score", page_icon="🏆", layout="wide")

render_home_button()
render_access_bar()

st.title("Knockout Score")

st.markdown("""
<style>
.match-box {
    background-color: white;
    border: 1px solid #d9e2f3;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.info-box {
    background-color: #EAF2FF;
    padding: 12px;
    border-radius: 10px;
    border-left: 5px solid #1F4E78;
    margin-bottom: 16px;
    color: #1F1F1F;
}
</style>
""", unsafe_allow_html=True)


def get_qualified_teams(data):
    all_rows = []

    for court_name, court_data in data["courts"].items():
        standings = compute_standings(court_data)

        for rank, row in standings.iterrows():
            all_rows.append({
                "Court": court_name,
                "Team": row["Team"],
                "Wins": row["Wins"],
                "Diff": row["Diff"],
                "PF": row["PF"],
                "Rank": rank
            })

    all_df = pd.DataFrame(all_rows)

    winners = all_df[all_df["Rank"] == 1].copy()
    winners["Qualified As"] = "Court Winner"

    others = all_df[all_df["Rank"] != 1].copy()

    wildcards = others.sort_values(
        by=["Wins", "Diff", "PF"],
        ascending=[False, False, False]
    ).head(3).copy()

    wildcards["Qualified As"] = "Wild Card"

    qualified = pd.concat([winners, wildcards], ignore_index=True)

    qualified = qualified.sort_values(
        by=["Wins", "Diff", "PF"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    qualified.index = qualified.index + 1
    qualified.index.name = "Seed"

    return qualified


def get_match_winner(match):
    if match["score1"] == "" or match["score2"] == "":
        return ""
    if int(match["score1"]) > int(match["score2"]):
        return match["team1"]
    if int(match["score2"]) > int(match["score1"]):
        return match["team2"]
    return "Tie"


data = load_data()
qualified = get_qualified_teams(data)
can_edit = admin_edit_allowed()

mode_text = "Edit mode unlocked." if can_edit else "Read-only mode. Use Volunteer button and enter code IMF to unlock knockout editing."
st.markdown(
    f'<div class="info-box"><b>Status:</b> {mode_text}<br><b>Seeding Rule:</b> Standing seed is used. Quarterfinals are 1 vs 8, 2 vs 7, 3 vs 6, and 4 vs 5.</div>',
    unsafe_allow_html=True
)

st.subheader("1st Round Qualified Teams")
st.dataframe(
    qualified[["Team", "Qualified As", "Court", "Wins", "Diff", "PF"]],
    use_container_width=True
)

seeded_teams = qualified["Team"].tolist()

if len(seeded_teams) < 8:
    st.warning("Not enough qualified teams yet. Complete court scores first.")
    st.stop()

pairings = [
    (seeded_teams[0], seeded_teams[7]),
    (seeded_teams[1], seeded_teams[6]),
    (seeded_teams[2], seeded_teams[5]),
    (seeded_teams[3], seeded_teams[4]),
]

for i, (team1, team2) in enumerate(pairings):
    data["quarterfinals"][i]["team1"] = team1
    data["quarterfinals"][i]["team2"] = team2

save_data(data)

st.header("Quarterfinals")

for i, match in enumerate(data["quarterfinals"]):
    st.markdown('<div class="match-box">', unsafe_allow_html=True)
    st.markdown(f"### Quarterfinal {i + 1}")
    st.write(f"**{match['team1']}** vs **{match['team2']}**")

    c1, c2, c3 = st.columns([1, 1, 1])

    current_score1 = int(match["score1"]) if match["score1"] != "" else 0
    current_score2 = int(match["score2"]) if match["score2"] != "" else 0

    with c1:
        score1 = st.number_input(
            f"{match['team1']} score (QF{i+1})",
            min_value=0,
            step=1,
            key=f"qf_{i}_s1",
            value=current_score1,
            disabled=not can_edit
        )

    with c2:
        score2 = st.number_input(
            f"{match['team2']} score (QF{i+1})",
            min_value=0,
            step=1,
            key=f"qf_{i}_s2",
            value=current_score2,
            disabled=not can_edit
        )

    with c3:
        st.write("")
        st.write("")
        if can_edit:
            if st.button(f"Save Quarterfinal {i + 1}", key=f"save_qf_{i}"):
                data["quarterfinals"][i]["score1"] = score1
                data["quarterfinals"][i]["score2"] = score2
                save_data(data)
                st.success(f"Quarterfinal {i + 1} saved")
                st.rerun()
        else:
            st.button(f"Save Quarterfinal {i + 1}", key=f"save_qf_{i}", disabled=True)

    winner = get_match_winner(data["quarterfinals"][i])
    if winner and winner != "Tie":
        st.success(f"Winner: {winner}")
    elif winner == "Tie":
        st.warning("Tie detected. Please correct the score.")

    st.markdown('</div>', unsafe_allow_html=True)

qf_winners = [get_match_winner(m) for m in data["quarterfinals"]]
valid_qf_winners = [w for w in qf_winners if w not in ["", "Tie"]]

if len(valid_qf_winners) == 4:
    data["semifinals"][0]["team1"] = valid_qf_winners[0]
    data["semifinals"][0]["team2"] = valid_qf_winners[3]
    data["semifinals"][1]["team1"] = valid_qf_winners[1]
    data["semifinals"][1]["team2"] = valid_qf_winners[2]
    save_data(data)

st.header("Semifinals")

for i, match in enumerate(data["semifinals"]):
    st.markdown('<div class="match-box">', unsafe_allow_html=True)
    st.markdown(f"### Semifinal {i + 1}")

    if not match["team1"] or not match["team2"]:
        st.info("Waiting for quarterfinal results.")
        st.markdown('</div>', unsafe_allow_html=True)
        continue

    st.write(f"**{match['team1']}** vs **{match['team2']}**")

    c1, c2, c3 = st.columns([1, 1, 1])

    current_score1 = int(match["score1"]) if match["score1"] != "" else 0
    current_score2 = int(match["score2"]) if match["score2"] != "" else 0

    with c1:
        score1 = st.number_input(
            f"{match['team1']} score (SF{i+1})",
            min_value=0,
            step=1,
            key=f"sf_{i}_s1",
            value=current_score1,
            disabled=not can_edit
        )

    with c2:
        score2 = st.number_input(
            f"{match['team2']} score (SF{i+1})",
            min_value=0,
            step=1,
            key=f"sf_{i}_s2",
            value=current_score2,
            disabled=not can_edit
        )

    with c3:
        st.write("")
        st.write("")
        if can_edit:
            if st.button(f"Save Semifinal {i + 1}", key=f"save_sf_{i}"):
                data["semifinals"][i]["score1"] = score1
                data["semifinals"][i]["score2"] = score2
                save_data(data)
                st.success(f"Semifinal {i + 1} saved")
                st.rerun()
        else:
            st.button(f"Save Semifinal {i + 1}", key=f"save_sf_{i}", disabled=True)

    winner = get_match_winner(data["semifinals"][i])
    if winner and winner != "Tie":
        st.success(f"Winner: {winner}")
    elif winner == "Tie":
        st.warning("Tie detected. Please correct the score.")

    st.markdown('</div>', unsafe_allow_html=True)

sf_winners = [get_match_winner(m) for m in data["semifinals"]]
valid_sf_winners = [w for w in sf_winners if w not in ["", "Tie"]]

if len(valid_sf_winners) == 2:
    data["final"]["team1"] = valid_sf_winners[0]
    data["final"]["team2"] = valid_sf_winners[1]
    save_data(data)

st.header("Final")

final_match = data["final"]
st.markdown('<div class="match-box">', unsafe_allow_html=True)

if not final_match["team1"] or not final_match["team2"]:
    st.info("Waiting for semifinal results.")
else:
    st.write(f"**{final_match['team1']}** vs **{final_match['team2']}**")

    current_final_score1 = int(final_match["score1"]) if final_match["score1"] != "" else 0
    current_final_score2 = int(final_match["score2"]) if final_match["score2"] != "" else 0

    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        final_score1 = st.number_input(
            f"{final_match['team1']} score (Final)",
            min_value=0,
            step=1,
            key="final_s1",
            value=current_final_score1,
            disabled=not can_edit
        )

    with c2:
        final_score2 = st.number_input(
            f"{final_match['team2']} score (Final)",
            min_value=0,
            step=1,
            key="final_s2",
            value=current_final_score2,
            disabled=not can_edit
        )

    with c3:
        st.write("")
        st.write("")
        if can_edit:
            if st.button("Save Final", key="save_final"):
                data["final"]["score1"] = final_score1
                data["final"]["score2"] = final_score2
                save_data(data)
                st.success("Final saved")
                st.rerun()
        else:
            st.button("Save Final", key="save_final", disabled=True)

    final_winner = get_match_winner(data["final"])
    if final_winner and final_winner != "Tie":
        st.success(f"Champion: {final_winner}")
    elif final_winner == "Tie":
        st.warning("Tie detected. Please correct the score.")

st.markdown('</div>', unsafe_allow_html=True)