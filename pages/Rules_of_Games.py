import streamlit as st
from utils import render_home_button

st.set_page_config(page_title="Rules of Games", page_icon="📘", layout="wide")

render_home_button()

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

st.markdown(
    '<div class="page-title">Pickleball Tournament Rules</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="rule-box"><b>Purpose:</b> This is a friendly competition designed for fun, fairness, and fast-paced play. Please respect volunteers, opponents, and court schedules.</div>',
    unsafe_allow_html=True
)

st.markdown('<div class="section-header">Tournament Format</div>', unsafe_allow_html=True)

st.markdown("""
• **36 players total** forming **18 teams (pairs)**  
• Teams are **randomly assigned to courts using raffle draw**  
• There are **5 courts** with the following groups:

Court 1 – 4 teams  
Court 2 – 4 teams  
Court 3 – 4 teams  
Court 4 – 3 teams  
Court 5 – 3 teams

• Each court plays a **short round format** to determine rankings
""")

st.markdown('<div class="section-header">Scoring System</div>', unsafe_allow_html=True)

st.markdown("""
• Each match is played to **8 points**

• **Win = 1 win recorded**

• **Points For (PF)** = points scored

• **Points Against (PA)** = points conceded

• **Point Difference (Diff)** = PF − PA
""")

st.markdown('<div class="section-header">Court Standings Ranking</div>', unsafe_allow_html=True)

st.markdown("""
Teams are ranked using the following order:

1️⃣ Total Wins  
2️⃣ Point Difference (PF − PA)  
3️⃣ Total Points Scored (PF)
""")

st.markdown('<div class="section-header">Qualification to Knockout Stage</div>', unsafe_allow_html=True)

st.markdown("""
The **top 8 teams advance** to the knockout stage.

Qualification structure:

• **5 Court Winners** (1 from each court)

PLUS

• **3 Best Remaining Teams** across all courts

These 8 teams become the **Quarterfinalists**.
""")

st.markdown('<div class="section-header">Knockout Seeding</div>', unsafe_allow_html=True)

st.markdown("""
Quarterfinal matchups follow **standing seed order**:

Seed 1 vs Seed 8  
Seed 2 vs Seed 7  
Seed 3 vs Seed 6  
Seed 4 vs Seed 5
""")

st.markdown('<div class="section-header">Knockout Progression</div>', unsafe_allow_html=True)

st.markdown("""
Quarterfinal Winners advance to **Semifinals**

Semifinal Winners advance to **Final**

Final Winner becomes **Tournament Champion**
""")

st.markdown('<div class="section-header">Sportsmanship</div>', unsafe_allow_html=True)

st.markdown("""
• Be respectful to all players and volunteers  
• Call fair lines and scores  
• Keep games moving to stay on schedule  
• Remember the goal is **fun competition**
""")