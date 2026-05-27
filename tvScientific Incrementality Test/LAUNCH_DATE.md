# tvScientific Incrementality Test — Launch Date

**Experiment kickoff: 2026-05-06**

All analyses should treat this date as the start of the **in-flight (treatment) period**.

| Period | Date range |
|---|---|
| Pre-period (control baseline) | up to and including **2026-05-05** |
| In-flight (treated) | **2026-05-06** onward |

## Data freshness as of this snapshot (file suffix `0526`)

| File | Date range | Notes |
|---|---|---|
| `Visitors_by_DMA_0526.csv` | 2025-05-01 → 2026-05-26 | DMA rollup of GA4 city-level visitor data |
| `Enrollments by DMA 0526.csv` | 2025-02-20 → 2026-05-26 | Daily enrollments by DMA |

That gives **20 days of post-launch data** (2026-05-06 → 2026-05-26) for the first weekly read.

## Mapping coverage (Visitors → DMA via `Gma_Geocid_US.csv`)

- Rows mapped: 96.09%
- Total users mapped: **97.84%**
- CTA taps mapped: 97.94%

### Known gap: Las Vegas
GA4 reports Las Vegas under City ID **9197757**, which is **not** in `Gma_Geocid_US.csv`. That single city accounts for ~1.56M users (~0.8% of national traffic) and is excluded from the DMA rollup.

**Impact on the test:** Las Vegas is **not** a test or control DMA in the current design, so this gap does not bias the lift estimate. It only affects national totals.

**Fix (low priority):** add a manual override row mapping City ID 9197757 → DMA 839 ("Las Vegas, NV") to `Gma_Geocid_US.csv` before the next refresh.
