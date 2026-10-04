# Methodology

## Scope of version 0.1
- **Entity:** All-India public DISCOMs and power departments (59 utilities), as compiled by CSEP [C1].
- **Base year:** FY2020-21. This is the most recent year for which a complete, internally consistent
  cash-basis decomposition is available in the sources. The model reproduces it exactly
  (see `notebooks/01_calibration_fy2021.ipynb` and `tests/`).
- **Horizon:** to FY2069-70, labelled 2070. Years are named by the year in which the financial year ends.
- **Reference points:** official FY2024-25 values from the single government source [G1] are shown
  for comparison. They are not used as inputs.

## Core identity (CSEP [C1])
```
cost        = power purchase + employee + other + depreciation + interest
realised    = consumer tariff collected + subsidy received + grants + other income
cash gap    = cost − realised = D + C + S + RI + residual
D           = (billing loss − billing-loss target) × input energy × APPC
C           = consumer tariff booked − collected
S           = subsidy booked − subsidy received
RI          = regulatory income (approved, deferred)
residual    = cash gap − (D + C + S + RI)
```

## Dynamics (one step per year)
| Block | Rule | Basis |
|---|---|---|
| Sales | grow at `demand_growth`; a share `ci_migration` leaves each year. Departing consumers paid `ci_tariff_premium` above average, so the average rate of those who remain falls | DESIGN |
| Energy | input = sales ÷ (1 − billing loss); billing loss and target move linearly to their end values | C1 definitions |
| Power purchase | variable part = APPC × input; the base-year remainder is a fixed part; both escalate at `appc_escalation` | C1 base values |
| Other costs | employee and other costs grow at `om_escalation`; depreciation at `depreciation_growth` | DESIGN |
| Interest | base-year interest × (1 − legacy relief) + `interest_rate_new` × cumulative new financing | C1 base; rate DESIGN |
| Tariff | consumer and subsidy rates rise by `tariff_hike` each year; subsidy may rise faster (`subsidy_extra_growth`) | I1 for BAU hike |
| True-up | `trueup_coverage` × the underlying residual from `trueup_lag` years earlier is added to billing, or passed back if negative | C1 (about a two-year lag) |
| Cost-reflective mode | once the gap closes, the hike equals growth in cost per kWh plus a correction toward `target_surplus` | DESIGN |
| Regulatory assets | new RI adds to the stock; from `ra_liquidation_start`, the stock is recovered in equal parts over `ra_liquidation_years` via tariff | P1 (Supreme Court: 3% cap, four years) |
| State support | optional grant covering `loss_takeover_share` of the previous year's cash gap | DESIGN |
| Balance sheet | cash gap adds to cumulative financing; C adds to receivables; S adds to an off-book unpaid-subsidy stock; net worth moves by the accrual result −(D + residual) | C1 mapping |

## Target tests (design choices)
**Profitable DISCOM, FY2047-48:**
- cash gap ≤ 0 in FY2045-46, FY2046-47 and FY2047-48
- AT&C below 10%, in line with the draft NEP's single-digit goal [P2]
- subsidy realisation ≥ 99%
- regulatory assets ≤ 3% of booked revenue [P1]

**Viksit Bharat DISCOM, 2070:** the FY2047-48 test passes, there is no cash gap in any year from 2048 to 2070, and net worth ≥ 0 in 2070.

## Known limitations
1. **No calibration yet for FY2021-22 to FY2024-25.** Those years saw state loss takeovers and
   late-payment-surcharge refinancing. The BAU path therefore diverges from official FY25 values.
2. **All-India aggregate only.** CSEP warns that national totals net profitable DISCOMs against
   loss-making ones. Per-DISCOM baselines are the next step (see `notebooks/03_add_a_state.ipynb`).
3. **Scenarios without bailouts compound interest on unfunded gaps**, so BAU numbers grow very large.
   Read them as a warning about the mechanism, not as a forecast.
4. **Nominal rupees throughout.** There is no deflator yet.
5. **Power-procurement mix is not modelled** (renewables, storage, fuel). It enters only through the APPC path.
