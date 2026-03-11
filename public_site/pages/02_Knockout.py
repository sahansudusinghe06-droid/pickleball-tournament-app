import os
import sys
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared_utils import render_knockout_page

st.set_page_config(page_title="Knockout", page_icon="🏆", layout="wide")
render_knockout_page(home_target="app.py", show_access=False)