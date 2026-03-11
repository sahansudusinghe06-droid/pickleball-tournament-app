import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from shared_utils import render_public_home

render_public_home()