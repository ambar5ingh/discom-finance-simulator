"""Load the sourced data files that ship with the repository."""
from io import StringIO
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def read_csv(name, text=None):
    """Read data/<name>, or parse `text` if given (used by the in-browser build)."""
    return pd.read_csv(StringIO(text)) if text is not None else pd.read_csv(DATA_DIR / name)
