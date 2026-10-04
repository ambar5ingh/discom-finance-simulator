"""DISCOM Finance Simulator: web app.

Run locally:   panel serve app/app.py --show
Browser build: python scripts/build_web.py   (creates site/index.html for GitHub Pages)
"""
# --- local imports (stripped in the browser build) ---
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from discom_sim import (Levers, PRESETS, NOTES, base_from_table, read_csv, simulate,  # noqa: E402
                        profitable_test, viksit_test, first_gap_close_year, solve_tariff_hike)
# --- end local imports ---

from dataclasses import replace  # noqa: E402

import pandas as pd  # noqa: E402
import panel as pn  # noqa: E402
from bokeh.models import ColumnDataSource, HoverTool, Label, Span, NumeralTickFormatter  # noqa: E402
from bokeh.plotting import figure  # noqa: E402

pn.extension(sizing_mode="stretch_width")

try:
    EMBEDDED_DATA  # defined only in the browser build
except NameError:
    EMBEDDED_DATA = None


def load(name):
    return read_csv(name, None if EMBEDDED_DATA is None else EMBEDDED_DATA[name])


BASE = base_from_table(load("baseline_all_india_fy2021.csv"))
SOURCES = load("sources.csv")
ANCHORS = load("anchors_fy2025.csv")
STATES = load("state_anchors_fy2025.csv")

INK, PAPER, GRID, ACCENT = "#1E2A32", "#F7F9F8", "#DDE3E1", "#0F6E6E"
COMPONENTS = [
    ("D", "Excess billing loss (DISCOM)", "#3B6EA8"),
    ("C", "Consumer non-collection (DISCOM)", "#E08E2B"),
    ("S", "Unpaid subsidy (state)", "#4E9A5B"),
    ("RI", "Regulatory income deferred (regulator)", "#8E6BB0"),
    ("residual", "Residual: tariff below cost", "#A23E48"),
]

# ---------------------------------------------------------------- widgets
preset = pn.widgets.Select(name="Scenario", options=list(PRESETS), value="S2 Profitable by FY2047-48")

W = {
    "tariff_hike": pn.widgets.FloatSlider(name="Annual tariff hike", start=-0.02, end=0.12, step=0.001, format="0.0%"),
    "trueup_coverage": pn.widgets.FloatSlider(name="Share of past residual recovered in true-up", start=0, end=1, step=0.05, format="0%"),
    "trueup_lag": pn.widgets.IntSlider(name="True-up lag (years)", start=1, end=4),
    "cost_reflective_after_close": pn.widgets.Checkbox(name="Cost-reflective tariffs once the gap closes"),
    "target_surplus": pn.widgets.FloatSlider(name="Target surplus in cost-reflective mode", start=0, end=0.1, step=0.005, format="0.0%"),
    "ri_share_end": pn.widgets.FloatSlider(name="New regulatory income (share of revenue)", start=0, end=0.05, step=0.001, format="0.0%"),
    "ri_path_end_year": pn.widgets.IntSlider(name="…reached by year", start=2021, end=2040),
    "ra_liquidation_start": pn.widgets.IntSlider(name="Regulatory assets recovered from year", start=2022, end=2100),
    "ra_liquidation_years": pn.widgets.IntSlider(name="…over how many years", start=1, end=10),
    "subsidy_realisation_end": pn.widgets.FloatSlider(name="Subsidy paid by state (share of booked)", start=0.6, end=1, step=0.01, format="0%"),
    "subsidy_path_end_year": pn.widgets.IntSlider(name="…reached by year", start=2021, end=2040),
    "subsidy_extra_growth": pn.widgets.FloatSlider(name="Subsidy growth above tariff (e.g. free units)", start=-0.02, end=0.05, step=0.005, format="0.0%"),
    "loss_takeover_share": pn.widgets.FloatSlider(name="State funds this share of last year's gap", start=0, end=1, step=0.05, format="0%"),
    "billing_loss_end": pn.widgets.FloatSlider(name="Billing loss", start=0.03, end=0.25, step=0.005, format="0.0%"),
    "billing_target_end": pn.widgets.FloatSlider(name="Regulator's billing-loss target", start=0.03, end=0.25, step=0.005, format="0.0%"),
    "billing_path_end_year": pn.widgets.IntSlider(name="…both reached by year", start=2021, end=2045),
    "collection_loss_end": pn.widgets.FloatSlider(name="Consumer non-collection", start=0, end=0.1, step=0.0025, format="0.00%"),
    "collection_path_end_year": pn.widgets.IntSlider(name="…reached by year", start=2021, end=2045),
    "appc_escalation": pn.widgets.FloatSlider(name="Power purchase cost growth per kWh", start=0, end=0.1, step=0.0025, format="0.0%"),
    "om_escalation": pn.widgets.FloatSlider(name="Employee and other cost growth", start=0, end=0.1, step=0.0025, format="0.0%"),
    "depreciation_growth": pn.widgets.FloatSlider(name="Depreciation growth", start=0, end=0.1, step=0.0025, format="0.0%"),
    "interest_rate_new": pn.widgets.FloatSlider(name="Interest on new borrowing", start=0.04, end=0.14, step=0.0025, format="0.0%"),
    "legacy_interest_relief": pn.widgets.FloatSlider(name="Legacy debt taken over (share of base interest)", start=0, end=1, step=0.05, format="0%"),
    "legacy_relief_year": pn.widgets.IntSlider(name="…from year", start=2022, end=2100),
    "demand_growth": pn.widgets.FloatSlider(name="Sales growth", start=0, end=0.1, step=0.0025, format="0.0%"),
    "ci_migration": pn.widgets.FloatSlider(name="Sales lost to open access / rooftop each year", start=0, end=0.03, step=0.001, format="0.0%"),
    "ci_tariff_premium": pn.widgets.FloatSlider(name="Tariff premium paid by departing consumers", start=0, end=1, step=0.05, format="0%"),
}

GROUPS = [
    ("Tariffs and regulation", ["tariff_hike", "trueup_coverage", "trueup_lag", "cost_reflective_after_close",
                                "target_surplus", "ri_share_end", "ri_path_end_year", "ra_liquidation_start",
                                "ra_liquidation_years"]),
    ("State government", ["subsidy_realisation_end", "subsidy_path_end_year", "subsidy_extra_growth", "loss_takeover_share"]),
    ("DISCOM operations", ["billing_loss_end", "billing_target_end", "billing_path_end_year",
                           "collection_loss_end", "collection_path_end_year"]),
    ("Costs and finance", ["appc_escalation", "om_escalation", "depreciation_growth", "interest_rate_new",
                           "legacy_interest_relief", "legacy_relief_year"]),
    ("Demand", ["demand_growth", "ci_migration", "ci_tariff_premium"]),
]

solve_btn = pn.widgets.Button(name="Solve for the tariff hike", button_type="primary",
                              description="Finds the smallest uniform annual hike that closes the cash gap by FY2047-48")
solve_msg = pn.pane.Markdown("", margin=(0, 10))
units = pn.widgets.RadioButtonGroup(options=["Rs per kWh sold", "Rs lakh crore"], value="Rs per kWh sold")


def apply_preset(name):
    lv = PRESETS[name]
    for k, w in W.items():
        w.value = getattr(lv, k)
    solve_msg.object = ""


def current_levers():
    return replace(Levers(), **{k: w.value for k, w in W.items()})


def on_solve(_):
    h = solve_tariff_hike(BASE, current_levers())
    if h is None:
        solve_msg.object = "No hike up to 25% a year closes the gap by FY2047-48 with these settings."
    else:
        W["tariff_hike"].value = round(h, 3)
        solve_msg.object = f"A uniform hike of **{h:.1%} a year** closes the cash gap in FY2045-46 to FY2047-48."


preset.param.watch(lambda e: apply_preset(e.new), "value")
solve_btn.on_click(on_solve)
apply_preset(preset.value)

# ---------------------------------------------------------------- charts


def _fig(title, y_label, height=300):
    p = figure(title=title, height=height, sizing_mode="stretch_width", toolbar_location=None,
               background_fill_color=PAPER, border_fill_color="white")
    p.grid.grid_line_color = GRID
    p.outline_line_color = None
    p.yaxis.axis_label = y_label
    p.title.text_color = INK
    p.title.text_font_size = "13pt"
    for yr, label in [(2048, "FY2047-48"), (2070, "2070")]:
        p.add_layout(Span(location=yr, dimension="height", line_color=INK, line_dash="dotted", line_alpha=0.5))
        p.add_layout(Label(x=yr, y=5, y_units="screen", text=label, text_font_size="8pt",
                           text_color=INK, text_alpha=0.7, x_offset=-4, text_align="right"))
    return p


def gap_chart(res, unit):
    scale = (1 / (res["sales_mu"] * 0.1)) if unit == "Rs per kWh sold" else 1 / 1e5
    p = _fig("Where the money goes missing: the cash gap split by cause", unit, 380)
    pos_bottom = pd.Series(0.0, index=res.index)
    neg_bottom = pd.Series(0.0, index=res.index)
    for key, label, colour in COMPONENTS:
        v = res[key] * scale
        pos = v.clip(lower=0)
        neg = v.clip(upper=0)
        src = ColumnDataSource(dict(x=list(res.index), top=(pos_bottom + pos).to_numpy(),
                                    bottom=pos_bottom.to_numpy()))
        p.vbar(x="x", top="top", bottom="bottom", width=0.8, color=colour, legend_label=label, source=src)
        src2 = ColumnDataSource(dict(x=list(res.index), top=neg_bottom.to_numpy(),
                                     bottom=(neg_bottom + neg).to_numpy()))
        p.vbar(x="x", top="top", bottom="bottom", width=0.8, color=colour, source=src2)
        pos_bottom = pos_bottom + pos
        neg_bottom = neg_bottom + neg
    total = ColumnDataSource(dict(x=res.index, y=res["cash_gap"] * scale))
    line = p.line("x", "y", source=total, line_color=INK, line_width=2.5, legend_label="Total cash gap")
    p.add_tools(HoverTool(renderers=[line], tooltips=[("FY ending", "@x"), ("Cash gap", "@y{0.00}")]))
    legend = p.legend[0]
    legend.orientation = "horizontal"
    legend.label_text_font_size = "9pt"
    legend.ncols = 3
    p.add_layout(legend, "below")
    return p


def cost_chart(res):
    p = _fig("Cost of supply vs revenue actually received", "Rs per kWh sold")
    src = ColumnDataSource(dict(x=res.index, acs=res["acs"], arr=res["arr_realised"]))
    a = p.line("x", "acs", source=src, line_color="#A23E48", line_width=2.5, legend_label="Average cost of supply")
    p.line("x", "arr", source=src, line_color=ACCENT, line_width=2.5, legend_label="Revenue realised (cash)")
    p.add_tools(HoverTool(renderers=[a], tooltips=[("FY", "@x"), ("Cost", "@acs{0.00}"), ("Revenue", "@arr{0.00}")]))
    p.legend.location = "top_left"
    return p


def loss_chart(res):
    p = _fig("AT&C loss", "share of input")
    p.line(res.index, res["atc_loss"], line_color=ACCENT, line_width=2.5, legend_label="Model (cash basis)")
    a = ANCHORS.set_index("indicator").loc["atc_loss_national"]
    p.scatter([int(a.fy)], [float(a.value)], size=10, color=INK, legend_label="Official FY2024-25 (G1)")
    p.yaxis.formatter = NumeralTickFormatter(format="0%")
    return p


def balance_chart(res):
    p = _fig("Net worth and cumulative new financing", "Rs lakh crore")
    p.line(res.index, res["net_worth"] / 1e5, line_color=INK, line_width=2.5, legend_label="Net worth")
    p.line(res.index, res["cumulative_financing"] / 1e5, line_color="#E08E2B", line_width=2.5,
           legend_label="Borrowing/payables added since FY21")
    p.legend.location = "top_left"
    return p


def verdict(res):
    p48, p70 = profitable_test(res), viksit_test(res)
    close = first_gap_close_year(res)

    def lines(t):
        return "\n".join(f"- {'✔' if ok else '✘'} {name}" for name, ok in t["checks"].items())

    close_txt = (f"The cash gap first closes in **FY{close - 1}-{str(close)[2:]}**." if close
                 else "The cash gap **never closes** under these settings.")
    return pn.Row(
        pn.pane.Markdown(f"### {close_txt}\nBase year FY2020-21: gap ₹1,04,091 crore (₹1.14/kWh sold), "
                         "reproduced exactly from CSEP (C1).", width=380),
        pn.pane.Markdown(f"**Profitable by FY2047-48: {'passes' if p48['passed'] else 'fails'}**\n\n{lines(p48)}"),
        pn.pane.Markdown(f"**Viksit Bharat DISCOM by 2070: {'passes' if p70['passed'] else 'fails'}**\n\n{lines(p70)}"),
        styles={"background": PAPER, "border-left": f"4px solid {ACCENT}", "padding": "4px 12px"},
    )


def results(*_):
    res = simulate(BASE, current_levers())
    download = pn.widgets.FileDownload(callback=lambda: __import__("io").StringIO(res.to_csv()),
                                       filename="discom_finance_simulator_results.csv",
                                       label="Download results (CSV)", button_type="light", width=240)
    return pn.Column(
        verdict(res),
        units,
        pn.pane.Bokeh(gap_chart(res, units.value)),
        pn.Row(pn.pane.Bokeh(cost_chart(res)), pn.pane.Bokeh(loss_chart(res))),
        pn.pane.Bokeh(balance_chart(res)),
        download,
    )


live = pn.bind(results, *W.values(), units)

# ---------------------------------------------------------------- tabs
data_tab = pn.Column(
    pn.pane.Markdown("### Sources\nEvery input row in `data/` carries one of these IDs. "
                     "`DESIGN` marks a modelling choice, not a sourced fact."),
    pn.widgets.Tabulator(SOURCES, show_index=False, disabled=True, layout="fit_data_table"),
    pn.pane.Markdown("### Base year: All-India public DISCOMs, FY2020-21 (C1)"),
    pn.widgets.Tabulator(load("baseline_all_india_fy2021.csv"), show_index=False, disabled=True, layout="fit_data_table"),
    pn.pane.Markdown("### Official FY2024-25 reference values (G1)"),
    pn.widgets.Tabulator(ANCHORS, show_index=False, disabled=True, layout="fit_data_table"),
    pn.pane.Markdown("### State debt and payable days, FY2024-25 (G1)\n"
                     "State-level simulation needs a full baseline per state; see `data/templates/`."),
    pn.widgets.Tabulator(STATES, show_index=False, disabled=True, layout="fit_data_table", height=420),
)

method_tab = pn.pane.Markdown("""
### How the model works
Each year the model computes cost and cash revenue for the entity and splits the cash gap into the five
components identified by CSEP (C1):

`cash gap = D + C + S + RI + residual`

- **D**: billing loss above the regulator's target, valued at gross input energy × average power purchase cost.
- **C**: consumer billing not collected.
- **S**: subsidy booked but not paid by the state.
- **RI**: approved cost whose recovery the regulator deferred (becomes a regulatory asset).
- **Residual**: what remains, meaning tariffs below cost after all of the above.

Unfunded gaps are financed by new borrowing or payables, which carry interest into later years.
Past residuals come back through true-ups after a lag. Net worth moves with the accrual result
(−(D + residual)).

### Reading the results
- The base year reproduces CSEP's FY2020-21 numbers exactly. Years after that are projections, not history.
  The model is not yet calibrated to FY2021-22 to FY2024-25, which saw state loss takeovers and
  late-payment-surcharge refinancing. Compare with the official FY2024-25 point on the AT&C chart.
- Scenarios without bailouts spiral, because interest compounds on unfunded gaps. That is the mechanism,
  not a forecast.
- The FY2047-48 and 2070 test thresholds are design choices. See `docs/methodology.md`.

### Preset notes
""" + "\n".join(f"- **{k}**: {v}" for k, v in NOTES.items()))

sidebar = [preset,
           pn.pane.Markdown("Moving any slider re-runs the model.", margin=(0, 10)),
           solve_btn, solve_msg,
           *[pn.Card(*[W[k] for k in keys], title=title, collapsed=i > 0) for i, (title, keys) in enumerate(GROUPS)]]

template = pn.template.BootstrapTemplate(
    title="DISCOM Finance Simulator",
    sidebar=sidebar,
    main=[pn.Tabs(("Results", live), ("Data and sources", data_tab), ("Method", method_tab), dynamic=True)],
    header_background=ACCENT,
    sidebar_width=360,
)
template.servable()
