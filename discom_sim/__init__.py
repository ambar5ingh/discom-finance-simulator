"""DISCOM Finance Simulator: an open-source model of Indian electricity distribution finances."""
from .model import (Levers, simulate, base_from_table, profitable_test, viksit_test,
                    first_gap_close_year, solve_tariff_hike)
from .scenarios import PRESETS, NOTES
from .io import read_csv

__version__ = "0.1.0"
