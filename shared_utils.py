import os
import requests
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

REST_URL = f"{SUPABASE_URL}/rest/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

WRITE_HEADERS = {
    **HEADERS,
    "Prefer": "return=minimal"
}

UPSERT_HEADERS = {
    **HEADERS,
    "Prefer": "resolution=merge-duplicates,return=minimal"
}

COURT_CODES = {
    "Court 1": "11",
    "Court 2": "22",
    "Court 3": "33",
    "Court 4": "44",
    "Court 5": "55"
}

ADMIN_CODE = "IMF"

MATCH_TEMPLATES = {
    4: [(0, 1), (2, 3), (0, 2), (1, 3)],
    3: [(0, 1), (1, 2), (0, 2)]
}


def enable_public_autorefresh(seconds=5):
    st_autorefresh(interval=seconds * 1000, key=f"public_refresh_{seconds}")


def init_session_state():
    defaults = {
        "authorized_courts": [],
        "admin_authorized": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _api_request(method, path, params=None, payload=None, headers=None):
    url = f"{REST_URL}/{path}"
    response = requests.request(
        method=method,
        url=url,
        headers=headers or HEADERS,
        params=params,
        json=payload,
        timeout=20
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Supabase API error {response.status_code} on {path}: {response.text}")

    if not response.text.strip():
        return None

    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return response.json()

    return response.text


def _score_to_db(value):
    if value in ("", None):
        return None
    return int(value)


def _score_from_db(value):
    if value is None:
        return ""
    return str(value)


def build_matches_for_teams(team_list, existing_matches=None):
    template = MATCH_TEMPLATES[len(team_list)]
    new_matches = []

    for idx, (a, b) in enumerate(template):
        score1 = ""
        score2 = ""

        if existing_matches and idx < len(existing_matches):
            score1 = existing_matches[idx].get("score1", "")
            score2 = existing_matches[idx].get("score2", "")

        new_matches.append({
            "team1": team_list[a],
            "team2": team_list[b],
            "score1": score1,
            "score2": score2
        })

    return new_matches


@st.cache_data(ttl=3, show_spinner=False)
def _load_data_cached():
    courts_rows = _api_request("GET", "courts", params={"select": "*", "order": "id"})
    teams_rows = _api_request("GET", "teams", params={"select": "*", "order": "id"})
    matches_rows = _api_request("GET", "matches", params={"select": "*", "order": "court_id,match_number"})
    knockout_rows = _api_request("GET", "knockout_matches", params={"select": "*", "order": "id"})

    try:
        settings_rows = _api_request("GET", "settings", params={"select": "*"})
    except Exception:
        settings_rows = []

    data = {
        "courts": {},
        "quarterfinals": [],
        "semifinals": [],
        "final": {"team1": "", "team2": "", "score1": "", "score2": ""},
        "settings": {"teams_locked": False}
    }

    court_id_to_name = {}

    for court in courts_rows or []:
        court_name = court["name"]
        court_id = court["id"]
        court_id_to_name[court_id] = court_name

        data["courts"][court_name] = {
            "group": court.get("group_name", ""),
            "teams": [],
            "matches": []
        }

    for team in teams_rows or []:
        court_name = court_id_to_name.get(team["court_id"])
        if court_name:
            data["courts"][court_name]["teams"].append(team["team_name"])

    for match in matches_rows or []:
        court_name = court_id_to_name.get(match["court_id"])
        if court_name:
            data["courts"][court_name]["matches"].append({
                "team1": match.get("team1", "") or "",
                "team2": match.get("team2", "") or "",
                "score1": _score_from_db(match.get("score1")),
                "score2": _score_from_db(match.get("score2"))
            })

    for row in settings_rows or []:
        if row.get("key") == "teams_locked":
            data["settings"]["teams_locked"] = str(row.get("value", "")).lower() == "true"

    for row in knockout_rows or []:
        match = {
            "team1": row.get("team1", "") or "",
            "team2": row.get("team2", "") or "",
            "score1": _score_from_db(row.get("score1")),
            "score2": _score_from_db(row.get("score2"))
        }

        if row["round"] == "Quarterfinal":
            data["quarterfinals"].append(match)
        elif row["round"] == "Semifinal":
            data["semifinals"].append(match)
        elif row["round"] == "Final":
            data["final"] = match

    return data


def load_data():
    return _load_data_cached()


def save_data(data):
    courts_rows = _api_request("GET", "courts", params={"select": "*", "order": "id"})
    teams_rows = _api_request("GET", "teams", params={"select": "*", "order": "id"})
    matches_rows = _api_request("GET", "matches", params={"select": "*", "order": "court_id,match_number"})
    knockout_rows = _api_request("GET", "knockout_matches", params={"select": "*", "order": "id"})

    court_name_to_id = {court["name"]: court["id"] for court in courts_rows or []}

    for court_name, court_data in data["courts"].items():
        court_id = court_name_to_id[court_name]

        court_team_rows = [r for r in teams_rows if r["court_id"] == court_id]
        court_match_rows = [r for r in matches_rows if r["court_id"] == court_id]

        for db_row, team_name in zip(court_team_rows, court_data["teams"]):
            _api_request(
                "PATCH",
                f"teams?id=eq.{db_row['id']}",
                payload={"team_name": team_name},
                headers=WRITE_HEADERS
            )

        for db_row, match in zip(court_match_rows, court_data["matches"]):
            _api_request(
                "PATCH",
                f"matches?id=eq.{db_row['id']}",
                payload={
                    "team1": match["team1"],
                    "team2": match["team2"],
                    "score1": _score_to_db(match["score1"]),
                    "score2": _score_to_db(match["score2"])
                },
                headers=WRITE_HEADERS
            )

    qf_rows = [r for r in knockout_rows if r["round"] == "Quarterfinal"]
    sf_rows = [r for r in knockout_rows if r["round"] == "Semifinal"]
    final_rows = [r for r in knockout_rows if r["round"] == "Final"]

    for db_row, match in zip(qf_rows, data["quarterfinals"]):
        _api_request(
            "PATCH",
            f"knockout_matches?id=eq.{db_row['id']}",
            payload={
                "team1": match["team1"],
                "team2": match["team2"],
                "score1": _score_to_db(match["score1"]),
                "score2": _score_to_db(match["score2"])
            },
            headers=WRITE_HEADERS
        )

    for db_row, match in zip(sf_rows, data["semifinals"]):
        _api_request(
            "PATCH",
            f"knockout_matches?id=eq.{db_row['id']}",
            payload={
                "team1": match["team1"],
                "team2": match["team2"],
                "score1": _score_to_db(match["score1"]),
                "score2": _score_to_db(match["score2"])
            },
            headers=WRITE_HEADERS
        )

    if final_rows:
        _api_request(
            "PATCH",
            f"knockout_matches?id=eq.{final_rows[0]['id']}",
            payload={
                "team1": data["final"]["team1"],
                "team2": data["final"]["team2"],
                "score1": _score_to_db(data["final"]["score1"]),
                "score2": _score_to_db(data["final"]["score2"])
            },
            headers=WRITE_HEADERS
        )

    try:
        _api_request(
            "POST",
            "settings?on_conflict=key",
            payload=[{
                "key": "teams_locked",
                "value": str(data["settings"]["teams_locked"])
            }],
            headers=UPSERT_HEADERS
        )
    except Exception:
        pass

    _load_data_cached.clear()


def compute_standings(court_data):
    teams = court_data["teams"]
    matches = court_data["matches"]

    standings = {
        team: {"Team": team, "Wins": 0, "PF": 0, "PA": 0, "Diff": 0}
        for team in teams
    }

    for match in matches:
        team1 = match["team1"]
        team2 = match["team2"]
        score1 = match["score1"]
        score2 = match["score2"]

        if score1 == "" or score2 == "":
            continue

        score1 = int(score1)
        score2 = int(score2)

        standings[team1]["PF"] += score1
        standings[team1]["PA"] += score2

        standings[team2]["PF"] += score2
        standings[team2]["PA"] += score1

        if score1 > score2:
            standings[team1]["Wins"] += 1
        elif score2 > score1:
            standings[team2]["Wins"] += 1

    for team in standings:
        standings[team]["Diff"] = standings[team]["PF"] - standings[team]["PA"]

    df = pd.DataFrame(list(standings.values()))
    df = df.sort_values(
        by=["Wins", "Diff", "PF"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    df.index = df.index + 1
    df.index.name = "Rank"
    return df


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


def render_home_button(home_target="app.py"):
    col1, col2 = st.columns([1, 5])
    with col1:
        st.page_link(home_target, label="⬅ Home")


@st.dialog("Volunteer / Admin Access")
def access_dialog():
    st.write("Enter your code to unlock editing for your page.")
    code = st.text_input("Access Code", type="password")

    if st.button("Unlock"):
        matched = False

        for court_name, court_code in COURT_CODES.items():
            if code == court_code:
                if court_name not in st.session_state["authorized_courts"]:
                    st.session_state["authorized_courts"].append(court_name)
                st.success(f"{court_name} editing unlocked.")
                matched = True
                st.rerun()

        if code == ADMIN_CODE:
            st.session_state["admin_authorized"] = True
            st.success("Admin / Knockout access unlocked.")
            matched = True
            st.rerun()

        if not matched:
            st.error("Invalid code.")


def render_access_bar():
    init_session_state()

    c1, c2, c3 = st.columns([1, 1, 4])

    with c1:
        if st.button("Volunteer"):
            access_dialog()

    with c2:
        if st.button("Logout"):
            st.session_state["authorized_courts"] = []
            st.session_state["admin_authorized"] = False
            st.success("Access cleared for this session.")
            st.rerun()


def court_edit_allowed(court_name):
    init_session_state()
    return court_name in st.session_state["authorized_courts"]


def admin_edit_allowed():
    init_session_state()
    return st.session_state["admin_authorized"]


def reset_court_scores(data, court_name):
    for match in data["courts"][court_name]["matches"]:
        match["score1"] = ""
        match["score2"] = ""
    return data


def reset_knockout(data):
    data["quarterfinals"] = [
        {"team1": "", "team2": "", "score1": "", "score2": ""},
        {"team1": "", "team2": "", "score1": "", "score2": ""},
        {"team1": "", "team2": "", "score1": "", "score2": ""},
        {"team1": "", "team2": "", "score1": "", "score2": ""}
    ]

    data["semifinals"] = [
        {"team1": "", "team2": "", "score1": "", "score2": ""},
        {"team1": "", "team2": "", "score1": "", "score2": ""}
    ]

    data["final"] = {
        "team1": "",
        "team2": "",
        "score1": "",
        "score2": ""
    }

    return data


def reset_all_scores(data):
    for court_name in data["courts"]:
        data = reset_court_scores(data, court_name)
    data = reset_knockout(data)
    return data


def render_public_home():
    st.set_page_config(page_title="Pickleball Tournament", page_icon="🏓", layout="wide")
    enable_public_autorefresh(5)

    banner_path = os.path.join(os.path.dirname(__file__), "assets", "banner.png")

    st.markdown("""
    <style>
    .main-title {
        background: linear-gradient(90deg, #1F4E78 0%, #2C6AA0 100%);
        color: white;
        padding: 22px;
        border-radius: 16px;
        text-align: center;
        font-size: 38px;
        font-weight: 800;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.15);
    }
    .blue-note {
        background-color: #EAF2FF;
        border-left: 6px solid #1F4E78;
        padding: 14px;
        border-radius: 10px;
        margin-top: 10px;
        color: #1F1F1F;
        font-size: 17px;
    }
    .section-title {
        color: white;
        background: linear-gradient(90deg, #0F766E 0%, #149488 100%);
        padding: 12px 16px;
        border-radius: 12px;
        font-weight: bold;
        margin-top: 28px;
        margin-bottom: 16px;
        font-size: 22px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }
    div[data-testid="stPageLink"] a {
        width: 100%;
        min-height: 140px;
        border-radius: 18px;
        border: 1px solid #D8E3F0;
        background: linear-gradient(180deg, #FFFFFF 0%, #F7FBFF 100%);
        color: #1F4E78 !important;
        font-weight: 700;
        font-size: 21px;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.10);
        text-decoration: none !important;
        padding: 14px;
    }
    div[data-testid="stPageLink"] a * {
        color: #1F4E78 !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if os.path.exists(banner_path):
        st.image(banner_path, use_container_width=True)

    st.markdown('<div class="main-title">Pickleball Tournament Dashboard</div>', unsafe_allow_html=True)

    st.markdown("## Tournament Pages")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.page_link("pages/01_Standing.py", label="📊 Standing")
    with c2:
        st.page_link("pages/02_Knockout.py", label="🏆 Knockout")
    with c3:
        st.page_link("pages/03_Rules.py", label="📘 Rules")

    st.markdown(
        '<div class="blue-note"><b>Public View:</b> This site is read-only for players and spectators.</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="section-title">Court Score Pages</div>', unsafe_allow_html=True)

    d1, d2, d3, d4, d5 = st.columns(5)
    with d1:
        st.page_link("pages/11_Court_1.py", label="1️⃣ Court 1")
    with d2:
        st.page_link("pages/12_Court_2.py", label="2️⃣ Court 2")
    with d3:
        st.page_link("pages/13_Court_3.py", label="3️⃣ Court 3")
    with d4:
        st.page_link("pages/14_Court_4.py", label="4️⃣ Court 4")
    with d5:
        st.page_link("pages/15_Court_5.py", label="5️⃣ Court 5")


def render_volunteer_home():
    st.set_page_config(page_title="Volunteer Score Entry", page_icon="🏓", layout="wide")
    init_session_state()
    render_access_bar()

    st.markdown("""
    <style>
    .main-title {
        background: linear-gradient(90deg, #1F4E78 0%, #2C6AA0 100%);
        color: white;
        padding: 22px;
        border-radius: 16px;
        text-align: center;
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.15);
    }
    .blue-note {
        background-color: #EAF2FF;
        border-left: 6px solid #1F4E78;
        padding: 14px;
        border-radius: 10px;
        margin-top: 10px;
        color: #1F1F1F;
        font-size: 17px;
    }
    .section-title {
        color: white;
        background: linear-gradient(90deg, #0F766E 0%, #149488 100%);
        padding: 12px 16px;
        border-radius: 12px;
        font-weight: bold;
        margin-top: 28px;
        margin-bottom: 16px;
        font-size: 22px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }
    div[data-testid="stPageLink"] a {
        width: 100%;
        min-height: 120px;
        border-radius: 18px;
        border: 1px solid #D8E3F0;
        background: linear-gradient(180deg, #FFFFFF 0%, #F7FBFF 100%);
        color: #1F4E78 !important;
        font-weight: 700;
        font-size: 20px;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.10);
        text-decoration: none !important;
        padding: 14px;
    }
    div[data-testid="stPageLink"] a * {
        color: #1F4E78 !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">Volunteer & Admin Score Entry</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Court Entry Pages</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.page_link("pages/11_Court_1.py", label="1️⃣ Court 1")
    with c2:
        st.page_link("pages/12_Court_2.py", label="2️⃣ Court 2")
    with c3:
        st.page_link("pages/13_Court_3.py", label="3️⃣ Court 3")
    with c4:
        st.page_link("pages/14_Court_4.py", label="4️⃣ Court 4")
    with c5:
        st.page_link("pages/15_Court_5.py", label="5️⃣ Court 5")

    st.markdown('<div class="section-title">Control</div>', unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        st.page_link("pages/20_Knockout.py", label="🏆 Knockout")
    with a2:
        st.page_link("pages/99_Admin.py", label="🛠️ Admin")

    st.markdown(
        '<div class="blue-note"><b>Volunteer Access:</b> Use the Volunteer button to unlock your assigned court. Public users should use the public QR code only.</div>',
        unsafe_allow_html=True
    )


def render_standing_page(home_target="app.py", show_access=False):
    if show_access:
        init_session_state()
        render_access_bar()
    else:
        enable_public_autorefresh(5)

    render_home_button(home_target)
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


def render_knockout_page(home_target="app.py", show_access=False):
    if show_access:
        init_session_state()
        render_access_bar()
    else:
        enable_public_autorefresh(5)

    render_home_button(home_target)
    st.title("Knockout")

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

    data = load_data()
    qualified = get_qualified_teams(data)
    can_edit = admin_edit_allowed() if show_access else False

    st.markdown(
        '<div class="info-box"><b>Seeding Rule:</b> Standing seed is used. Quarterfinals are 1 vs 8, 2 vs 7, 3 vs 6, and 4 vs 5.</div>',
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
        return

    pairings = [
        (seeded_teams[0], seeded_teams[7]),
        (seeded_teams[1], seeded_teams[6]),
        (seeded_teams[2], seeded_teams[5]),
        (seeded_teams[3], seeded_teams[4]),
    ]

    qf_display = []
    for i, (team1, team2) in enumerate(pairings):
        stored = data["quarterfinals"][i] if i < len(data["quarterfinals"]) else {"team1": "", "team2": "", "score1": "", "score2": ""}
        qf_display.append({
            "team1": stored["team1"] or team1,
            "team2": stored["team2"] or team2,
            "score1": stored["score1"],
            "score2": stored["score2"]
        })

    st.header("Quarterfinals")

    for i, match in enumerate(qf_display):
        st.markdown('<div class="match-box">', unsafe_allow_html=True)
        st.markdown(f"### Quarterfinal {i + 1}")
        st.write(f"**{match['team1']}** vs **{match['team2']}**")

        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            score1 = st.number_input(
                f"{match['team1']} score (QF{i+1})",
                min_value=0,
                step=1,
                key=f"qf_{i}_s1",
                value=int(match["score1"]) if match["score1"] != "" else 0,
                disabled=not can_edit
            )

        with c2:
            score2 = st.number_input(
                f"{match['team2']} score (QF{i+1})",
                min_value=0,
                step=1,
                key=f"qf_{i}_s2",
                value=int(match["score2"]) if match["score2"] != "" else 0,
                disabled=not can_edit
            )

        with c3:
            st.write("")
            st.write("")
            if can_edit:
                if st.button(f"Save Quarterfinal {i + 1}", key=f"save_qf_{i}"):
                    data["quarterfinals"][i]["team1"] = match["team1"]
                    data["quarterfinals"][i]["team2"] = match["team2"]
                    data["quarterfinals"][i]["score1"] = str(score1)
                    data["quarterfinals"][i]["score2"] = str(score2)
                    save_data(data)
                    st.success(f"Quarterfinal {i + 1} saved")
                    st.rerun()
            else:
                st.button(f"Save Quarterfinal {i + 1}", key=f"save_qf_{i}", disabled=True)

        winner = get_match_winner({
            "team1": match["team1"],
            "team2": match["team2"],
            "score1": str(score1) if can_edit else match["score1"],
            "score2": str(score2) if can_edit else match["score2"]
        })
        if winner and winner != "Tie":
            st.success(f"Winner: {winner}")
        elif winner == "Tie":
            st.warning("Tie detected. Please correct the score.")

        st.markdown('</div>', unsafe_allow_html=True)

    qf_winners = [get_match_winner(m) for m in qf_display]
    valid_qf_winners = [w for w in qf_winners if w not in ["", "Tie"]]

    sf_display = []
    for i in range(2):
        stored = data["semifinals"][i] if i < len(data["semifinals"]) else {"team1": "", "team2": "", "score1": "", "score2": ""}
        sf_display.append(stored.copy())

    if len(valid_qf_winners) == 4:
        derived_sf = [
            (valid_qf_winners[0], valid_qf_winners[3]),
            (valid_qf_winners[1], valid_qf_winners[2])
        ]
        for i, (t1, t2) in enumerate(derived_sf):
            if not sf_display[i]["team1"]:
                sf_display[i]["team1"] = t1
            if not sf_display[i]["team2"]:
                sf_display[i]["team2"] = t2

    st.header("Semifinals")

    for i, match in enumerate(sf_display):
        st.markdown('<div class="match-box">', unsafe_allow_html=True)
        st.markdown(f"### Semifinal {i + 1}")

        if not match["team1"] or not match["team2"]:
            st.info("Waiting for quarterfinal results.")
            st.markdown('</div>', unsafe_allow_html=True)
            continue

        st.write(f"**{match['team1']}** vs **{match['team2']}**")

        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            score1 = st.number_input(
                f"{match['team1']} score (SF{i+1})",
                min_value=0,
                step=1,
                key=f"sf_{i}_s1",
                value=int(match["score1"]) if match["score1"] != "" else 0,
                disabled=not can_edit
            )

        with c2:
            score2 = st.number_input(
                f"{match['team2']} score (SF{i+1})",
                min_value=0,
                step=1,
                key=f"sf_{i}_s2",
                value=int(match["score2"]) if match["score2"] != "" else 0,
                disabled=not can_edit
            )

        with c3:
            st.write("")
            st.write("")
            if can_edit:
                if st.button(f"Save Semifinal {i + 1}", key=f"save_sf_{i}"):
                    data["semifinals"][i]["team1"] = match["team1"]
                    data["semifinals"][i]["team2"] = match["team2"]
                    data["semifinals"][i]["score1"] = str(score1)
                    data["semifinals"][i]["score2"] = str(score2)
                    save_data(data)
                    st.success(f"Semifinal {i + 1} saved")
                    st.rerun()
            else:
                st.button(f"Save Semifinal {i + 1}", key=f"save_sf_{i}", disabled=True)

        winner = get_match_winner({
            "team1": match["team1"],
            "team2": match["team2"],
            "score1": str(score1) if can_edit else match["score1"],
            "score2": str(score2) if can_edit else match["score2"]
        })
        if winner and winner != "Tie":
            st.success(f"Winner: {winner}")
        elif winner == "Tie":
            st.warning("Tie detected. Please correct the score.")

        st.markdown('</div>', unsafe_allow_html=True)

    sf_winners = [get_match_winner(m) for m in sf_display if m["team1"] and m["team2"]]
    valid_sf_winners = [w for w in sf_winners if w not in ["", "Tie"]]

    final_display = data["final"].copy()

    if len(valid_sf_winners) == 2:
        if not final_display["team1"]:
            final_display["team1"] = valid_sf_winners[0]
        if not final_display["team2"]:
            final_display["team2"] = valid_sf_winners[1]

    st.header("Final")
    st.markdown('<div class="match-box">', unsafe_allow_html=True)

    if not final_display["team1"] or not final_display["team2"]:
        st.info("Waiting for semifinal results.")
    else:
        st.write(f"**{final_display['team1']}** vs **{final_display['team2']}**")

        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            final_score1 = st.number_input(
                f"{final_display['team1']} score (Final)",
                min_value=0,
                step=1,
                key="final_s1",
                value=int(final_display["score1"]) if final_display["score1"] != "" else 0,
                disabled=not can_edit
            )

        with c2:
            final_score2 = st.number_input(
                f"{final_display['team2']} score (Final)",
                min_value=0,
                step=1,
                key="final_s2",
                value=int(final_display["score2"]) if final_display["score2"] != "" else 0,
                disabled=not can_edit
            )

        with c3:
            st.write("")
            st.write("")
            if can_edit:
                if st.button("Save Final", key="save_final"):
                    data["final"]["team1"] = final_display["team1"]
                    data["final"]["team2"] = final_display["team2"]
                    data["final"]["score1"] = str(final_score1)
                    data["final"]["score2"] = str(final_score2)
                    save_data(data)
                    st.success("Final saved")
                    st.rerun()
            else:
                st.button("Save Final", key="save_final", disabled=True)

        final_winner = get_match_winner({
            "team1": final_display["team1"],
            "team2": final_display["team2"],
            "score1": str(final_score1) if can_edit else final_display["score1"],
            "score2": str(final_score2) if can_edit else final_display["score2"]
        })
        if final_winner and final_winner != "Tie":
            st.success(f"Champion: {final_winner}")
        elif final_winner == "Tie":
            st.warning("Tie detected. Please correct the score.")

    st.markdown('</div>', unsafe_allow_html=True)


def render_rules_page(home_target="app.py", show_access=False):
    if show_access:
        init_session_state()
        render_access_bar()
    else:
        enable_public_autorefresh(5)

    render_home_button(home_target)

    st.markdown("""
    <style>
    .page-title {
        background-color: #1F4E78;
        color: white;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .rule-box {
        background-color: #EAF2FF;
        padding: 16px;
        border-radius: 10px;
        border-left: 6px solid #1F4E78;
        margin-bottom: 18px;
        color: #1F1F1F;
    }
    .section-header {
        background-color: #0F766E;
        color: white;
        padding: 10px 14px;
        border-radius: 10px;
        font-weight: bold;
        margin-top: 25px;
        margin-bottom: 12px;
        font-size: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-title">Pickleball Tournament Rules</div>', unsafe_allow_html=True)
    st.markdown('<div class="rule-box"><b>Purpose:</b> This is a friendly competition designed for fun, fairness, and fast-paced play.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Tournament Format</div>', unsafe_allow_html=True)
    st.markdown("""
- 18 teams total
- Court 1: 4 teams
- Court 2: 4 teams
- Court 3: 4 teams
- Court 4: 3 teams
- Court 5: 3 teams
- Short custom court-stage format
""")

    st.markdown('<div class="section-header">Scoring System</div>', unsafe_allow_html=True)
    st.markdown("""
- Each match is played to 8 points
- Win = 1 win recorded
- PF = Points For
- PA = Points Against
- Diff = PF − PA
""")

    st.markdown('<div class="section-header">Ranking</div>', unsafe_allow_html=True)
    st.markdown("""
1. Wins  
2. Point Difference  
3. Total Points Scored  
""")

    st.markdown('<div class="section-header">Qualification</div>', unsafe_allow_html=True)
    st.markdown("""
- 5 Court Winners qualify automatically
- 3 Best Remaining Teams qualify as Wild Cards
- Total qualified teams = 8
""")

    st.markdown('<div class="section-header">Knockout</div>', unsafe_allow_html=True)
    st.markdown("""
- Quarterfinals: 1 vs 8, 2 vs 7, 3 vs 6, 4 vs 5
- Quarterfinal winners advance to Semifinals
- Semifinal winners advance to Final
- Final winner becomes Champion
""")


def render_admin_page(home_target="app.py"):
    init_session_state()
    render_home_button(home_target)
    render_access_bar()

    st.title("Admin Page")

    if not admin_edit_allowed():
        st.warning("Read-only mode. Use Volunteer button and enter code IMF to unlock Admin access.")
        st.stop()

    data = load_data()

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


def render_court_page(court_name, home_target="app.py"):
    st.set_page_config(page_title=court_name, page_icon="🏓", layout="wide")

    init_session_state()
    render_home_button(home_target)
    render_access_bar()

    st.markdown("""
        <style>
        .page-title {
            background-color: #1F4E78;
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .sub-box {
            background-color: #EAF2FF;
            padding: 12px;
            border-radius: 10px;
            border-left: 5px solid #1F4E78;
            margin-bottom: 16px;
            color: #1F1F1F;
        }
        .match-box {
            background-color: white;
            border: 1px solid #d9e2f3;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        </style>
    """, unsafe_allow_html=True)

    data = load_data()
    court = data["courts"][court_name]
    group_name = court["group"]
    can_edit = court_edit_allowed(court_name)

    st.markdown(
        f'<div class="page-title">{court_name} – Score Entry</div>',
        unsafe_allow_html=True
    )

    mode_text = "Edit mode unlocked." if can_edit else "Read-only mode. Use Volunteer button and enter code to unlock editing."
    st.markdown(
        f'<div class="sub-box"><b>Group:</b> {group_name}<br><b>Status:</b> {mode_text}</div>',
        unsafe_allow_html=True
    )

    st.subheader("Teams")
    team_cols = st.columns(len(court["teams"])) if len(court["teams"]) > 0 else [st.container()]

    for idx, team in enumerate(court["teams"]):
        with team_cols[idx]:
            st.info(team)

    st.subheader("Match Scores")

    for i, match in enumerate(court["matches"]):
        st.markdown('<div class="match-box">', unsafe_allow_html=True)

        st.markdown(f"### Match {i+1}")
        st.write(f"**{match['team1']}** vs **{match['team2']}**")

        col1, col2, col3 = st.columns([1, 1, 1])

        current_score1 = int(match["score1"]) if match["score1"] != "" else 0
        current_score2 = int(match["score2"]) if match["score2"] != "" else 0

        with col1:
            score1 = st.number_input(
                f"{match['team1']} score",
                min_value=0,
                step=1,
                key=f"{court_name}_m{i}_s1",
                value=current_score1,
                disabled=not can_edit
            )

        with col2:
            score2 = st.number_input(
                f"{match['team2']} score",
                min_value=0,
                step=1,
                key=f"{court_name}_m{i}_s2",
                value=current_score2,
                disabled=not can_edit
            )

        with col3:
            st.write("")
            st.write("")
            if can_edit:
                if st.button(f"Save Match {i+1}", key=f"{court_name}_save_{i}"):
                    data["courts"][court_name]["matches"][i]["score1"] = str(score1)
                    data["courts"][court_name]["matches"][i]["score2"] = str(score2)
                    save_data(data)
                    st.success(f"Match {i+1} saved")
                    st.rerun()
            else:
                st.button(f"Save Match {i+1}", key=f"{court_name}_save_{i}", disabled=True)

        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Current Standings")
    standings_df = compute_standings(court)
    st.dataframe(standings_df, use_container_width=True)


def render_public_court_page(court_name, home_target="app.py"):
    st.set_page_config(page_title=court_name, page_icon="🏓", layout="wide")
    enable_public_autorefresh(5)

    render_home_button(home_target)

    st.markdown("""
        <style>
        .page-title {
            background-color: #1F4E78;
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .sub-box {
            background-color: #EAF2FF;
            padding: 12px;
            border-radius: 10px;
            border-left: 5px solid #1F4E78;
            margin-bottom: 16px;
            color: #1F1F1F;
        }
        .match-box {
            background-color: white;
            border: 1px solid #d9e2f3;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        </style>
    """, unsafe_allow_html=True)

    data = load_data()
    court = data["courts"][court_name]
    group_name = court["group"]

    st.markdown(
        f'<div class="page-title">{court_name} – Public Score View</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="sub-box"><b>Group:</b> {group_name}<br><b>Status:</b> Read-only public view.</div>',
        unsafe_allow_html=True
    )

    st.subheader("Teams")

    team_cols = st.columns(len(court["teams"])) if len(court["teams"]) > 0 else [st.container()]

    for idx, team in enumerate(court["teams"]):
        with team_cols[idx]:
            st.info(team)

    st.subheader("Match Scores")

    for i, match in enumerate(court["matches"]):
        st.markdown('<div class="match-box">', unsafe_allow_html=True)

        st.markdown(f"### Match {i+1}")
        st.write(f"**{match['team1']}** vs **{match['team2']}**")

        score1 = match["score1"] if match["score1"] != "" else "-"
        score2 = match["score2"] if match["score2"] != "" else "-"

        c1, c2 = st.columns(2)
        with c1:
            st.metric(label=match["team1"], value=score1)
        with c2:
            st.metric(label=match["team2"], value=score2)

        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Current Standings")
    standings_df = compute_standings(court)
    st.dataframe(standings_df, use_container_width=True)