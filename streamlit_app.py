import streamlit as st
from pathlib import Path
from utils import render_access_bar, init_session_state

st.set_page_config(
    page_title="Pickleball Tournament",
    page_icon="🏓",
    layout="wide"
)

init_session_state()

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
    transition: all 0.2s ease-in-out;
}

div[data-testid="stPageLink"] a * {
    color: #1F4E78 !important;
    opacity: 1 !important;
}

div[data-testid="stPageLink"] a:hover {
    background: linear-gradient(180deg, #EAF2FF 0%, #DCEBFF 100%);
    border-color: #1F4E78;
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.14);
    text-decoration: none !important;
}

div[data-testid="stPageLink"] a:hover * {
    color: #1F4E78 !important;
    opacity: 1 !important;
}

.small-caption {
    color: #AFC7DD;
    font-size: 15px;
    margin-top: -8px;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)

render_access_bar()

banner_path = Path("assets/banner.png")
if banner_path.exists():
    st.image(str(banner_path), use_container_width=True)

st.markdown(
    '<div class="main-title">Pickleball Tournament Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="small-caption">Friendly competition • Live standings • Automatic knockout progression</div>',
    unsafe_allow_html=True
)

st.markdown("## Main Pages")
col1, col2, col3 = st.columns(3)

with col1:
    st.page_link("pages/standing.py", label="📊 Standing")

with col2:
    st.page_link("pages/Knockout_Score.py", label="🏆 Knockout Score")

with col3:
    st.page_link("pages/Rules_of_Games.py", label="📘 Rules of Games")

st.markdown(
    '<div class="blue-note"><b>Live Tournament Status:</b> Court scores, standings, qualifiers, and final results will update here as volunteers enter results.</div>',
    unsafe_allow_html=True
)

st.markdown('<div class="section-title">Court Entry Pages</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.page_link("pages/court_1.py", label="1️⃣ Court 1")

with c2:
    st.page_link("pages/court_2.py", label="2️⃣ Court 2")

with c3:
    st.page_link("pages/court_3.py", label="3️⃣ Court 3")

with c4:
    st.page_link("pages/court_4.py", label="4️⃣ Court 4")

with c5:
    st.page_link("pages/court_5.py", label="5️⃣ Court 5")

st.markdown('<div class="section-title">Tournament Control</div>', unsafe_allow_html=True)

a1, a2 = st.columns([2, 4])

with a1:
    st.page_link("pages/Admin.py", label="🛠️ Admin")

with a2:
    st.markdown(
        '<div class="blue-note"><b>Volunteer access:</b> Volunteers can unlock score entry using the Volunteer button. Spectators have read-only access.</div>',
        unsafe_allow_html=True
    )