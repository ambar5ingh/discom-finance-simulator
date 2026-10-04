"""Scenario presets. Values are modelling choices unless a source_id is named in NOTES.
Source IDs refer to data/sources.csv."""
from dataclasses import replace

from .model import Levers

BAU = Levers(
    tariff_hike=0.019,            # I1: median approved hike FY26
    trueup_coverage=0.3, trueup_lag=2,   # lag: C1 (about two years); coverage: DESIGN
    ri_share_end=0.0119, ri_path_end_year=2021,
    subsidy_realisation_end=0.90, subsidy_path_end_year=2025,
    billing_loss_end=0.14, billing_target_end=0.12, billing_path_end_year=2030,
    collection_loss_end=0.04, collection_path_end_year=2030,
    appc_escalation=0.047,        # C1: APPC 2.47 -> 4.68 Rs/kWh over FY07-FY21, about 4.7%/yr
    om_escalation=0.05, demand_growth=0.05,
)

ANNOUNCED = replace(
    BAU,
    tariff_hike=0.03,
    ri_share_end=0.0, ri_path_end_year=2025,              # P1: no new regulatory assets
    ra_liquidation_start=2025, ra_liquidation_years=4,    # P1: liquidate within four years
    subsidy_realisation_end=0.98, subsidy_path_end_year=2027,
    billing_loss_end=0.11, billing_target_end=0.10, billing_path_end_year=2028,
    collection_loss_end=0.02, collection_path_end_year=2030,
)

PROFITABLE_2048 = replace(
    ANNOUNCED,
    tariff_hike=0.045,            # I1: ICRA estimate of hike needed to close the FY24 gap
    trueup_coverage=1.0, trueup_lag=1,
    subsidy_realisation_end=1.0, subsidy_path_end_year=2028,
    billing_loss_end=0.08, billing_target_end=0.08, billing_path_end_year=2035,  # P2: single-digit AT&C
    collection_loss_end=0.005, collection_path_end_year=2032,                    # C1: ~0.5% allowed loss
    legacy_interest_relief=0.5, legacy_relief_year=2028,
    cost_reflective_after_close=True, target_surplus=0.03,
)

VIKSIT_2070 = replace(PROFITABLE_2048, appc_escalation=0.03, ci_migration=0.0)

STRESS = replace(
    BAU, tariff_hike=0.0, appc_escalation=0.06, subsidy_extra_growth=0.02,
    subsidy_realisation_end=0.80, ci_migration=0.01,
)

PRESETS = {
    "S0 Business as usual": BAU,
    "S1 Announced policies": ANNOUNCED,
    "S2 Profitable by FY2047-48": PROFITABLE_2048,
    "S3 Viksit Bharat DISCOMs by 2070": VIKSIT_2070,
    "S5 Stress": STRESS,
}

NOTES = {
    "tariff_hike": "BAU 1.9% = median approved hike FY26 (I1); S2 4.5% = ICRA's estimate of the hike needed (I1)",
    "trueup_lag": "About two years in practice (C1)",
    "appc_escalation": "4.7%/yr = APPC growth FY07-FY21 (C1)",
    "ri_share_end": "S1 onward: no new regulatory assets, existing ones liquidated in 4 years (P1)",
    "billing_loss_end": "S2: single-digit AT&C goal (P2)",
    "collection_loss_end": "S2: 0.5% allowed collection loss used in tariff norms (C1)",
    "cost_reflective_after_close": "S2/S3: after the gap closes, tariffs follow cost plus a 3% surplus (DESIGN)",
    "other": "All other preset values are design choices (DESIGN)",
}
