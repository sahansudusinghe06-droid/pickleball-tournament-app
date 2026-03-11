import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared_utils import render_public_court_page

render_public_court_page("Court 5", home_target="app.py")