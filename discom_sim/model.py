"""Core engine of the DISCOM Finance Simulator.

One entity (a DISCOM, a state, or an aggregate) is simulated year by year.
Every year the cash-basis gap is split into the five CSEP components:

    cash_gap = D + C + S + RI + Residual

    D        excess billing (distribution) loss beyond the regulator's target,
             valued at gross input energy x APPC
    C        consumer tariff booked but not collected
    S        subsidy booked but not paid by the state
    RI       regulatory income: approved cost whose recovery is deferred
    Residual everything left over, i.e. tariffs that do not cover cost

Money is in Rs crore, energy in million kWh (MU). 1 MU x 1 Rs/kWh = 0.1 Rs crore.
Years are labelled by the year in which the financial year ends (2021 = FY2020-21).
"""
from dataclasses import dataclass, asdict, replace

import pandas as pd

MU_RS_TO_CRORE = 0.1


@dataclass
class Levers:
    """Policy and assumption settings. Share values are fractions (0.05 = 5%)."""

    end_year: int = 2070

    # Tariff and regulatory process
    tariff_hike: float = 0.019          # annual change in consumer and subsidy rates
    trueup_coverage: float = 0.3        # share of an earlier year's residual recovered (or passed back if negative)
    trueup_lag: int = 2                 # years between the gap and its true-up recovery
    cost_reflective_after_close: bool = False  # once the gap closes, tariffs track cost plus a target surplus
    target_surplus: float = 0.02        # surplus aimed for, as share of cost, in cost-reflective mode
    ri_share_end: float = 0.0119        # new regulatory income as share of booked revenue
    ri_path_end_year: int = 2021
    ra_liquidation_start: int = 2100    # year existing regulatory assets start being recovered
    ra_liquidation_years: int = 4

    # State government and subsidy
    subsidy_realisation_end: float = 0.8435
    subsidy_path_end_year: int = 2021
    subsidy_extra_growth: float = 0.0   # subsidy rate growth above the tariff hike (e.g. free units)
    loss_takeover_share: float = 0.0    # share of the previous year's cash gap the state funds as a grant

    # DISCOM operations
    billing_loss_end: float = 0.1638
    billing_target_end: float = 0.12855
    billing_path_end_year: int = 2021
    collection_loss_end: float = 0.0464  # consumer tariff not collected, share of consumer billing
    collection_path_end_year: int = 2021

    # Costs
    appc_escalation: float = 0.047      # annual change in power purchase cost per kWh
    om_escalation: float = 0.05         # employee + other cost growth
    depreciation_growth: float = 0.05
    interest_rate_new: float = 0.09     # rate on new financing of cash gaps
    legacy_interest_relief: float = 0.0  # share of base-year interest removed by a debt takeover
    legacy_relief_year: int = 2100

    # Demand
    demand_growth: float = 0.05
    ci_migration: float = 0.0           # share of sales lost each year to open access/captive/rooftop
    ci_tariff_premium: float = 0.3      # migrating sales paid this much above the average consumer rate

    def as_dict(self):
        return asdict(self)


def _path(start, end, t, t0, t1):
    """Linear move from start (year t0) to end (year t1), flat afterwards."""
    if t <= t0:
        return start
    if t1 <= t0:
        return end
    f = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return start + (end - start) * f


def base_from_table(df):
    """Turn a baseline CSV (key, value, ...) into a dict of floats."""
    return {k: float(v) for k, v in zip(df["key"], df["value"])}


def simulate(base, lv):
    """Run the model from the base year to lv.end_year. Returns a DataFrame, one row per year."""
    t0 = int(base["base_fy"])
    bl0, blt0 = base["billing_loss"], base["billing_loss_target"]
    cl0 = 1 - base["tariff_collected"] / base["tariff_booked"]
    real0 = base["subsidy_realised"] / base["subsidy_booked"]
    ri0 = base["regulatory_income"] / (base["tariff_booked"] + base["subsidy_booked"])

    sales = base["sales_mu"]
    cons_rate = base["tariff_booked"] / sales / MU_RS_TO_CRORE     # Rs/kWh sold
    sub_rate = base["subsidy_booked"] / sales / MU_RS_TO_CRORE
    appc = base["appc"]
    input0 = sales / (1 - bl0)
    ppc_fixed = base["power_purchase_cost"] - appc * input0 * MU_RS_TO_CRORE
    om = base["employee_cost"] + base["other_cost"]
    dep = base["depreciation"]
    interest_legacy = base["interest_cost"]
    other_inc = base["other_income_grants"]

    ra = base["regulatory_assets"]
    receivables = base["trade_receivables"]
    net_worth = base["net_worth"]
    financing = 0.0            # cumulative new borrowing/payables since the base year
    unpaid_subsidy = 0.0
    ra_liq_per_year = None
    closed = False
    acs_hist = {}
    residual_hist = {}
    prev_cash_gap, prev_cost = 0.0, 1.0
    rows = []

    for t in range(t0, lv.end_year + 1):
        first = t == t0
        if not first:
            grown = sales * (1 + lv.demand_growth)
            migrated = grown * lv.ci_migration
            new_sales = grown - migrated
            # migrating consumers paid above average; the remaining base pays less on average
            cons_rate = (cons_rate * grown - cons_rate * (1 + lv.ci_tariff_premium) * migrated) / new_sales
            sales = new_sales
            hike = lv.tariff_hike
            if closed and lv.cost_reflective_after_close and t - 2 in acs_hist:
                surplus_share = -prev_cash_gap / prev_cost
                hike = acs_hist[t - 1] / acs_hist[t - 2] - 1 + 0.5 * (lv.target_surplus - surplus_share)
            cons_rate *= 1 + hike
            sub_rate *= (1 + hike) * (1 + lv.subsidy_extra_growth)
            appc *= 1 + lv.appc_escalation
            ppc_fixed *= 1 + lv.appc_escalation
            om *= 1 + lv.om_escalation
            dep *= 1 + lv.depreciation_growth

        bl = _path(bl0, lv.billing_loss_end, t, t0, lv.billing_path_end_year)
        blt = _path(blt0, lv.billing_target_end, t, t0, lv.billing_path_end_year)
        cl = _path(cl0, lv.collection_loss_end, t, t0, lv.collection_path_end_year)
        realisation = _path(real0, lv.subsidy_realisation_end, t, t0, lv.subsidy_path_end_year)
        ri_share = _path(ri0, lv.ri_share_end, t, t0, lv.ri_path_end_year)

        input_mu = sales / (1 - bl)
        ppc = appc * input_mu * MU_RS_TO_CRORE + ppc_fixed
        relief = lv.legacy_interest_relief if t >= lv.legacy_relief_year else 0.0
        interest = interest_legacy * (1 - relief) + lv.interest_rate_new * max(financing, 0.0)
        cost = ppc + om + dep + interest

        # true-up of earlier residuals and recovery of regulatory assets add to consumer billing
        # true-up recovers the underlying residual of an earlier year (the residual before any
        # true-up revenue was received). Surpluses are passed back too, except in cost-reflective
        # mode after closure, where the tariff controller manages the surplus instead.
        earlier = residual_hist.get(t - lv.trueup_lag, 0.0)
        if closed and lv.cost_reflective_after_close:
            earlier = max(earlier, 0.0)
        trueup = 0.0 if first else lv.trueup_coverage * earlier
        if t >= lv.ra_liquidation_start and ra_liq_per_year is None:
            ra_liq_per_year = ra / max(lv.ra_liquidation_years, 1)
        ra_liq = min(ra, ra_liq_per_year or 0.0)

        tariff_booked = sales * cons_rate * MU_RS_TO_CRORE + trueup + ra_liq
        subsidy_booked = sales * sub_rate * MU_RS_TO_CRORE
        ri = ri_share * (tariff_booked + subsidy_booked)
        grants = (base["uday_grant"] if first else 0.0) + (0.0 if first else lv.loss_takeover_share * max(prev_cash_gap, 0.0))
        oi = other_inc if first else other_inc * (sales / base["sales_mu"])
        if first:
            ri = base["regulatory_income"]

        C = tariff_booked * cl
        S = subsidy_booked * (1 - realisation)
        D = (bl - blt) * input_mu * appc * MU_RS_TO_CRORE
        realised = tariff_booked - C + subsidy_booked - S + grants + oi
        cash_gap = cost - realised
        residual = cash_gap - (D + C + S + ri)
        residual_hist[t] = residual + trueup * (1 - cl)   # underlying residual before true-up

        book_pat = -(D + residual)                 # accrual result: booked revenue incl. RI minus cost
        ra = ra + ri - ra_liq
        receivables += C
        unpaid_subsidy += S
        net_worth += book_pat
        financing += cash_gap
        prev_cash_gap, prev_cost = cash_gap, cost
        closed = closed or cash_gap <= 0
        acs_hist[t] = cost / sales

        ce = (tariff_booked - C + subsidy_booked - S) / (tariff_booked + subsidy_booked)
        rows.append(dict(
            fy=t, sales_mu=sales, input_mu=input_mu, billing_loss=bl, billing_target=blt,
            collection_loss=cl, subsidy_realisation=realisation, atc_loss=1 - (1 - bl) * ce,
            consumer_rate=cons_rate, subsidy_rate=sub_rate, appc=appc,
            power_purchase_cost=ppc, om_cost=om, depreciation=dep, interest=interest, cost=cost,
            tariff_booked=tariff_booked, subsidy_booked=subsidy_booked, trueup=trueup, ra_recovery=ra_liq,
            grants=grants, other_income=oi, realised_revenue=realised,
            D=D, C=C, S=S, RI=ri, residual=residual, cash_gap=cash_gap,
            acs=cost / sales / MU_RS_TO_CRORE, arr_realised=realised / sales / MU_RS_TO_CRORE,
            gap_per_kwh=cash_gap / sales / MU_RS_TO_CRORE, book_pat=book_pat,
            regulatory_assets=ra, ra_share=ra / (tariff_booked + subsidy_booked),
            trade_receivables=receivables, unpaid_subsidy_stock=unpaid_subsidy,
            cumulative_financing=financing, net_worth=net_worth,
        ))
    return pd.DataFrame(rows).set_index("fy")


# ---- Target tests (thresholds are design choices; see docs/methodology.md) ----

def profitable_test(res, year=2048, run=3, atc_max=0.10, realisation_min=0.99, ra_max=0.03):
    """FY2047-48 test: cash gap <= 0 for `run` consecutive years ending in `year`,
    single-digit AT&C, subsidy paid in full, regulatory assets <= 3% of booked revenue."""
    years = [y for y in range(year - run + 1, year + 1) if y in res.index]
    if len(years) < run:
        return dict(passed=False, checks={"enough years": False})
    r = res.loc[year]
    checks = {
        f"cash gap <= 0 for {run} years": bool((res.loc[years, "cash_gap"] <= 1e-6).all()),
        "AT&C below 10%": bool(r.atc_loss < atc_max),
        "subsidy paid in full": bool(r.subsidy_realisation >= realisation_min),
        "regulatory assets <= 3% of revenue": bool(r.ra_share <= ra_max),
    }
    return dict(passed=all(checks.values()), checks=checks)


def viksit_test(res, year=2070):
    """2070 test: FY48 test passed, no cash gap in any year 2048-2070, net worth >= 0 by 2070."""
    p48 = profitable_test(res)
    span = [y for y in range(2048, year + 1) if y in res.index]
    checks = {
        "FY2047-48 test passed": p48["passed"],
        "no cash gap 2048-2070": bool(span) and bool((res.loc[span, "cash_gap"] <= 1e-6).all()),
        "net worth >= 0 in 2070": bool(year in res.index and res.loc[year, "net_worth"] >= 0),
    }
    return dict(passed=all(checks.values()), checks=checks)


def first_gap_close_year(res):
    closed = res.index[res["cash_gap"] <= 0]
    return int(closed[0]) if len(closed) else None


def solve_tariff_hike(base, lv, lo=-0.05, hi=0.25, tol=1e-4):
    """Smallest uniform annual tariff hike at which the cash gap is <= 0 in 2046-2048.
    Returns None if even the upper bound fails."""
    def ok(h):
        res = simulate(base, replace(lv, tariff_hike=h, end_year=max(lv.end_year, 2048)))
        return bool((res.loc[2046:2048, "cash_gap"] <= 0).all())
    if not ok(hi):
        return None
    if ok(lo):
        return lo
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi
