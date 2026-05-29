# tvScientific Incrementality Test — Methodology

A one-page reference for the test design and lift measurement. Companion read: [`Readme.md`](Readme.md), [`LAUNCH_DATE.md`](LAUNCH_DATE.md), [`Tvscientific_final_design.csv`](Tvscientific_final_design.csv).

---

## Goal

Measure the incremental impact of **tvScientific CTV ads** on Chime's enrollments (primary KPI), visitors, and CTA taps, in the 14 markets where the ads are running.

---

## Design — DMA-level geo test

A **between-DMAs** experiment: tvScientific ads run only in **14 test DMAs**, with **35 control DMAs** chosen to match the test DMAs' pre-period visitor volume. Test and control sets are **disjoint** (no DMA is in both).

| Group | # DMAs | Notes |
|---|---|---|
| **Test** | 14 | tvScientific ads served only here |
| **Control** | 35 | No tvScientific ads. Disjoint from test |

### Test-to-control assignment

| Type | Test DMAs | Control structure |
|---|---|---|
| **Basket** | 2 (New York, Los Angeles) | NY has a 10-DMA control basket; LA has 13. The basket is treated as one synthetic control whose aggregated volume matches the test market |
| **1:1** | 12 (Atlanta, Philadelphia, Indianapolis, Columbus OH, Detroit, Kansas City, Louisville, Birmingham, Baltimore, Memphis, Pittsburgh, Salt Lake City) | Each paired with one control DMA of similar pre-period visit volume |

Full pairing is in [`Tvscientific_final_design.csv`](Tvscientific_final_design.csv).

---

## Periods

| | Date |
|---|---|
| **Launch** | 2026-05-06 |
| **Pre-period (default)** | 4 weeks before launch (2026-04-08 → 2026-05-05) |
| **In-flight** | 2026-05-06 → data-as-of date (refreshed weekly) |

Sensitivity to baseline length is also reported at 6 and 8 weeks.

---

## Metrics

| Metric | Source | Notes |
|---|---|---|
| **Enrollments** | Chime EDW (Snowflake) — `edw_db.core.member_details` joined to `fivetran.gsheets.zipcode_to_dma` for DMA assignment | Primary KPI |
| **Visitors** | Google Analytics 4 city-level export, rolled up to DMA via `Gma_Geocid_US.csv` (Google City ID → Nielsen DMA) | Upper-funnel signal |
| **CTA taps** | GA4 CTA tap events, same DMA rollup as visitors | Upper-funnel signal |

`DD_30` (direct-deposit-within-30-days) is excluded from this readout pending upstream data maturity.

---

## Lift method — Scaled-control Difference-in-Differences

For each metric, daily counts are aggregated across all 14 test DMAs and across all 35 control DMAs to form two time series:

- `T(t)` = total of the metric across the 14 test DMAs on day `t`
- `C(t)` = total of the metric across the 35 control DMAs on day `t`

Daily averages over each period:

- `T_pre`, `T_post` — test daily mean in pre-period and in-flight
- `C_pre`, `C_post` — control daily mean in pre-period and in-flight

### Counterfactual

The counterfactual answers: *what would test markets have done if they had tracked control's trend?* Built by scaling control to test's baseline level:

```
Counterfactual_T_post = T_pre × (C_post / C_pre)
```

### Incremental lift

```
Incremental per day     = T_post  −  Counterfactual_T_post
Cumulative incremental  = (Incremental per day) × (number of in-flight days)
Lift %                  = Incremental per day  /  T_pre
```

This formulation is **algebraically equivalent** to subtracting % changes (`T_post/T_pre − C_post/C_pre`), just framed as observed-vs-counterfactual instead of test-grew-X% vs control-grew-Y%.

### Why scaled control (and not raw absolute DiD)

The test group sums 14 DMAs; the control group sums 35 DMAs. A raw absolute DiD (`ΔTest − ΔControl`) would conflate control's *size* with control's *trend* — control's larger absolute swings reflect its bigger N, not necessarily a stronger trend. Scaling control to test's baseline level removes that confound.

---

## Confidence intervals — Bootstrap

For each metric:

1. Resample the pre-period dates with replacement (28 of 28 for the 4-week baseline)
2. Resample the in-flight dates with replacement
3. Recompute the lift on those resampled means
4. Repeat 1,000 times

The 95% CI is the 2.5th and 97.5th percentiles of the bootstrap distribution. A metric is flagged **significant** if the 95% CI excludes zero.

---

## Data flow (weekly refresh)

```
Google Analytics 4 city-level export ──┐
                                       │  map via Gma_Geocid_US.csv
                                       ▼
                          Visitors + CTA taps  by DMA × date
                                       │
Chime EDW (Snowflake) ─ enrollments ───┤
                                       ▼
                       Aggregate to Test (14) vs Control (35)
                                       │
                                       ▼
                       Pre / In-flight split @ 2026-05-06
                                       │
                                       ▼
                 Scaled-control DiD  +  Bootstrap CI per metric
```

---

## Known limitations

1. **Las Vegas** (GA4 City ID 9197757) isn't in the `Gma_Geocid_US.csv` crosswalk. ~1.5M visitors (~0.8% of national traffic) are dropped from the visitor rollup. Las Vegas is **not** a test or control DMA, so this gap doesn't bias the lift estimate, only the national total.
2. **Pittsburgh ↔ Mobile-Pensacola** is the worst-balanced 1:1 pair (control/test visit ratio = 0.82). Could warrant per-cell weighting.
3. **NY + LA carry ~36% of test volume.** Aggregate lift is computed by summing test DMAs (not equal-weighting across cells), so these two markets dominate the headline. Per-cell breakdown available on request.
4. **Enrollment SQL** currently filters to marketing-attributable users (`fact_marketing_user_spend` join). All-enrollment view available on request.

---

## Re-running the analysis

See [`Readme.md`](Readme.md) for the weekly refresh steps. Hex project: *tvScientific Incrementality — Weekly DiD Readout*. The notebook produces a downloadable DMA × date CSV (last cell) covering the 4-week pre-period and all in-flight days.

---

*Last updated: 2026-05-29. Owner: Rohith Devarasetty (rohith.devarasetty@chime.com).*
