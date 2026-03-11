import streamlit as st
import pandas as pd
from utils import load_data, compute_standings, render_home_button

st.set_page_config(page_title="Standing", page_icon="📊", layout="wide")

render_home_button()

st.title("Tournament Standing")

data = load_data()

all_rows = []

st.header("Court Standings")

for court_name, court_data in data["courts"].items():
    st.subheader(court_name)

    standings = compute_standings(court_data)
    st.dataframe(standings, use_container_width=True)

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

st.markdown("---")
st.header("1st Round Qualified Teams")

display_df = qualified[["Team", "Qualified As", "Court", "Wins", "Diff", "PF"]]
st.dataframe(display_df, use_container_width=True)