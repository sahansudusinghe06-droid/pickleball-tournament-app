import os
import sys
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared_utils import render_standing_page

st.set_page_config(page_title="Standing", page_icon="📊", layout="wide")
render_standing_page(home_target="app.py", show_access=False)