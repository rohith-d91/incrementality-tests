# tvScientific Incrementality Test

Geo-based incrementality test measuring tvScientific CTV ads on Chime enrollments. Test launched **2026-05-06** (see [`LAUNCH_DATE.md`](LAUNCH_DATE.md)).

## Design

14 test DMAs paired with 35 control DMAs (no overlap). See [`Tvscientific_final_design.csv`](Tvscientific_final_design.csv).

- **2 basket cells** — New York (10 controls) and Los Angeles (13 controls). Synthetic-control style: control basket aggregated to match the test DMA's pre-period visit volume.
- **12 one-to-one cells** — Atlanta, Philadelphia, Indianapolis, Columbus OH, Detroit, Kansas City, Louisville, Birmingham, Baltimore, Memphis, Pittsburgh, Salt Lake City — each paired with a single control DMA of similar visit volume.

Matching variable: average daily **total users** (visits) over the pre-period.

## Files

| File | What it is | Refresh cadence |
|---|---|---|
| `Tvscientific_final_design.csv` | Test → control DMA assignments | Frozen — do not modify |
| `LAUNCH_DATE.md` | Experiment start date + period definitions | Frozen |
| `Gma_Geocid_US.csv` | GA4 City ID → Nielsen DMA crosswalk | Update when GA4 adds new city IDs |
| `Visitors_by_DMA_0526.csv` | Daily visitors (users + CTA taps) rolled up to DMA | Weekly |
| `Enrollments by DMA 0526.csv` | Daily enrollments by DMA | Weekly |
| `map_visitors_to_dma.py` | Script that produces `Visitors_by_DMA_*.csv` from GA4 export | n/a |

The `_0526` suffix on data files is the data-as-of date (`MMDD`). Each weekly refresh should add a new dated snapshot rather than overwriting.

## Weekly refresh — how to re-run

1. Pull the latest GA4 visitor export (city-level, `Date, City, City ID, Total users, CTA Tap Count`) into the local `tvScientific Incrementality Test/` folder. Name it `Visitor data <MMDD>.csv`.
2. Pull the latest `Enrollments by DMA <MMDD>.csv` from the warehouse and commit it to the repo.
3. Run the mapping script:
   ```bash
   python3 "tvScientific Incrementality Test/map_visitors_to_dma.py"
   ```
4. Commit the new `Visitors_by_DMA_<MMDD>.csv` to the repo.
5. Run the analysis (TBD — to be added as `analysis.py` / Hex project).

## Mapping coverage

The GA4 → DMA join via `Gma_Geocid_US.csv` covers **97.84% of users**. Largest unmapped city is **Las Vegas (City ID 9197757, DMA 839)** — see `LAUNCH_DATE.md` for details. Not a test or control DMA, so the gap doesn't bias the lift estimate.

## Planned analysis (next)

Difference-in-differences on the 14 test cells:
- Pre-period (≤ 2026-05-05) vs in-flight (≥ 2026-05-06) means for each cell
- Outcomes: **enrollments** (primary). Visitors used as exposure / sanity check. `dd_30` deferred until upstream data is fully baked.
- Aggregation: basket sum for NY/LA, direct 1:1 for the other 12.
- Lift = (test post − test pre) − (control post − control pre), normalized to test pre.
- Confidence interval: DMA-clustered bootstrap.

## Notes / known issues

- **Las Vegas mapping gap** (above). Optional fix: add manual override row to `Gma_Geocid_US.csv`.
- **Pittsburgh** is the worst-balanced 1:1 pair (control/test visits ratio = 0.822). May warrant weighting or exclusion.
- **NY + LA carry ~36% of test volume.** Decide upfront whether the headline lift number is equal-weighted across the 14 cells or volume-weighted.
- `dd_30` is excluded from the analysis until the upstream pipeline stabilizes.
