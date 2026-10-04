"""Run with:  pytest -q"""
from dataclasses import replace

import pytest

from discom_sim import (Levers, PRESETS, base_from_table, read_csv, simulate,
                        profitable_test, solve_tariff_hike)

BASE = base_from_table(read_csv("baseline_all_india_fy2021.csv"))


def test_base_year_reproduces_csep_decomposition():
    row = simulate(BASE, Levers(end_year=2021)).loc[2021]
    for comp in ["D", "C", "S", "RI", "residual"]:
        assert row[comp] == pytest.approx(BASE[f"check_{comp}"], abs=15)
    assert row["cash_gap"] == pytest.approx(BASE["check_cash_gap"], abs=15)


def test_components_always_sum_to_cash_gap():
    for lv in PRESETS.values():
        res = simulate(BASE, lv)
        total = res[["D", "C", "S", "RI", "residual"]].sum(axis=1)
        assert (total - res["cash_gap"]).abs().max() < 1e-6


def test_target_scenario_passes_and_bau_fails():
    assert profitable_test(simulate(BASE, PRESETS["S2 Profitable by FY2047-48"]))["passed"]
    assert not profitable_test(simulate(BASE, PRESETS["S0 Business as usual"]))["passed"]


def test_solver_result_closes_the_gap():
    lv = PRESETS["S1 Announced policies"]
    h = solve_tariff_hike(BASE, lv)
    res = simulate(BASE, replace(lv, tariff_hike=h))
    assert (res.loc[2046:2048, "cash_gap"] <= 0).all()


def test_full_subsidy_payment_removes_S():
    res = simulate(BASE, replace(Levers(), subsidy_realisation_end=1.0, subsidy_path_end_year=2025))
    assert abs(res.loc[2030, "S"]) < 1e-6
