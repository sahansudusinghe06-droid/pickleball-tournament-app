import requests
import streamlit as st
import pandas as pd

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

MATCH_TEMPLATES = {
    4: [(0, 1), (2, 3), (0, 2), (1, 3)],
    3: [(0, 1), (1, 2), (0, 2)]
}

COURT_CODES = {
    "Court 1": "11",
    "Court 2": "22",
    "Court 3": "33",
    "Court 4": "44",
    "Court 5": "55"
}

ADMIN_CODE = "IMF"


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
        raise RuntimeError(
            f"Supabase API error {response.status_code} on {path}: {response.text}"
        )

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
    courts_rows = _api_request("GET", "courts", params={"select": "*"})
    teams_rows = _api_request("GET", "teams", params={"select": "*"})
    matches_rows = _api_request("GET", "matches", params={"select": "*"})
    knockout_rows = _api_request("GET", "knockout_matches", params={"select": "*"})

    try:
        settings_rows = _api_request("GET", "settings", params={"select": "*"})
    except Exception:
        settings_rows = []

    courts_rows = sorted(courts_rows or [], key=lambda x: x["id"])
    teams_rows = sorted(teams_rows or [], key=lambda x: (x["court_id"], x["id"]))
    matches_rows = sorted(matches_rows or [], key=lambda x: (x["court_id"], x["match_number"]))
    knockout_rows = sorted(
        knockout_rows or [],
        key=lambda x: (
            {"Quarterfinal": 1, "Semifinal": 2, "Final": 3}.get(x["round"], 99),
            x["match_number"]
        )
    )

    data = {
        "courts": {},
        "quarterfinals": [],
        "semifinals": [],
        "final": {"team1": "", "team2": "", "score1": "", "score2": ""},
        "settings": {"teams_locked": False}
    }

    court_id_to_name = {}

    for court in courts_rows:
        court_name = court["name"]
        court_id = court["id"]
        court_id_to_name[court_id] = court_name

        data["courts"][court_name] = {
            "group": court.get("group_name", ""),
            "teams": [],
            "matches": []
        }

    for team in teams_rows:
        court_name = court_id_to_name.get(team["court_id"])
        if court_name:
            data["courts"][court_name]["teams"].append(team["team_name"])

    for match in matches_rows:
        court_name = court_id_to_name.get(match["court_id"])
        if court_name:
            data["courts"][court_name]["matches"].append({
                "team1": match.get("team1", "") or "",
                "team2": match.get("team2", "") or "",
                "score1": _score_from_db(match.get("score1")),
                "score2": _score_from_db(match.get("score2"))
            })

    for row in settings_rows:
        if row.get("key") == "teams_locked":
            data["settings"]["teams_locked"] = str(row.get("value", "")).lower() == "true"

    for row in knockout_rows:
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
    courts_rows = _api_request("GET", "courts", params={"select": "*"})
    teams_rows = _api_request("GET", "teams", params={"select": "*"})
    matches_rows = _api_request("GET", "matches", params={"select": "*"})
    knockout_rows = _api_request("GET", "knockout_matches", params={"select": "*"})

    courts_rows = sorted(courts_rows or [], key=lambda x: x["id"])
    teams_rows = sorted(teams_rows or [], key=lambda x: (x["court_id"], x["id"]))
    matches_rows = sorted(matches_rows or [], key=lambda x: (x["court_id"], x["match_number"]))
    knockout_rows = sorted(
        knockout_rows or [],
        key=lambda x: (
            {"Quarterfinal": 1, "Semifinal": 2, "Final": 3}.get(x["round"], 99),
            x["match_number"]
        )
    )

    court_name_to_id = {court["name"]: court["id"] for court in courts_rows}

    # Save teams and court matches
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

    # Save knockout matches
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

    # Save settings
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


def render_home_button():
    col1, col2 = st.columns([1, 5])
    with col1:
        st.page_link("streamlit_app.py", label="⬅ Home")


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


def render_court_page(court_name):
    st.set_page_config(page_title=court_name, page_icon="🏓", layout="wide")

    init_session_state()
    render_home_button()
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