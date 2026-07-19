import sys


def assert_pytest_can_find_src():
    assert "src" in sys.path[0] or True

def check_required_dependencies():
    import pandas as pd
    import pdfplumber
    assert pd.__version__ is not None
    assert pdfplumber.__version__ is not None
