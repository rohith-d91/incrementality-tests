# DSP Yahoo Geo Test — Project Context
**Ticket:** MDF-1629  
**Last updated:** 2026-05-14

---

## Goal
Run a **3-cell DMA geo-level incrementality test** to measure whether Yahoo DSP and/or Scope3 DSP advertising drives incremental Chime enrollments vs. a pure control holdout.

---

## Test Design

### Cells
| # | Label | Purpose |
|---|---|---|
| 1 | Yahoo Test | DMAs exposed to Yahoo DSP ads |
| 2 | DSP (Scope3) Test | DMAs exposed to Scope3 DSP ads |
| 3 | Control Holdout | No DSP ads (pure holdout) |

### Two parallel designs
1. **Full Geo Test** — all eligible DMAs balanced across 3 cells on enrollment volume
2. **Matched Market Test (MMT)** — 10 matched triplets (1 DMA per cell per triplet) selected by time-series correlation + enrollment similarity

---

## Key Files

| File | Description |
|---|---|
| `May 2025- 2026 Data by DMA.csv` | Raw daily data: `geo, assignment, date, total users, cta taps, enrollments, dd_30` — 88K rows, ~424 days |
| `dma_paid_spend.csv` | Paid marketing spend by DMA + date pulled from Snowflake (`edw_db` via `SNOWFLAKE_PROD_ANALYST_OKTA` role, `ANALYTICS_WH`) |
| `fetch_spend.py` | Snowflake pull script — queries `fact_marketing_user_spend` joined to `member_details` + zipcode-to-DMA mapping |
| `balance_dma_groups.py` | Main script: loads enrollment + spend data, applies exclusions, selects top 27 DMAs, runs dual-metric LPT + local search balancing, power analysis, MMT selection, generates charts |
| `dma_group_assignments.csv` | Output: full geo test DMA → cell assignments (includes `total_paid_spend` column) |
| `mmt_group_assignments.csv` | Output: 10 matched triplets × 3 cells |
| `dma_group_balance.png` | Chart: weekly enrollment trend + weekly paid spend trend by cell (parallel trends check on both metrics) |
| `dma_power_analysis.png` | Chart: weeks needed & budget vs. assumed lift |
| `mmt_balance_power.png` | Chart: MMT enrollment trend, profile, MDE curve |
| `Yahoo_DSP_Geo_Test_Design.docx` | Design document |
| `generate_docx.py` / `generate_doc.py` | Scripts for generating the design doc |
| `creator_pulse_test.py` | Empty — future use |

---

## Data Schema (`May 2025- 2026 Data by DMA.csv`)
```
index, geo (DMA code), assignment (prior cell), date, total users, cta taps, enrollments, dd_30
```
- `dd_30`: likely 30-day direct deposit metric
- `cta taps`: call-to-action taps (ad engagement proxy)
- `assignment`: prior test assignment (Cell A YouTube / Cell B Meta / Cell C Control / Excluded)

---

## Exclusions (applied in `balance_dma_groups.py`)

### (A) In another active geo test (~20 DMAs)
Jackson MS (718), Shreveport LA (612), Cincinnati OH (515), Little Rock AR (693), Norfolk VA (544), Greensboro NC (518), El Paso TX (765), Harlingen TX (636), Harrisburg PA (566), West Palm Beach FL (548), Macon GA (503), Columbus GA (522), Charleston WV (564), Dayton OH (542), Fresno CA (866), San Diego CA (825), Greenville SC/NC (567), Minneapolis MN (514), Chattanooga TN (575), Baton Rouge LA (716)

### (B) Large markets excluded by test design (~26 DMAs)
New York (501), Los Angeles (803), Houston (618), Memphis (640), Indianapolis (527), Kansas City (616), Detroit (505), Birmingham (630), Baltimore (512), Charlotte (517), Atlanta (524), Louisville (529), Columbus OH (535), Philadelphia (504), San Francisco (807), Phoenix (753), Nashville (659), Chicago (602), New Orleans (622), Pittsburgh (508), Oklahoma City (650), St. Louis (609), Las Vegas (839), San Antonio (641), Jacksonville (561), Milwaukee (617)

---

## Balancing Algorithm
1. **Dual-metric composite**: min-max normalise `total_enrollments` and `total_paid_spend`, combine 50/50 into a `composite` score per DMA
2. **DMA selection**: take top `N_PER_CELL × N_CELLS` DMAs by composite score (currently 9 × 3 = 27 DMAs, i.e. 8–10 per cell)
3. **LPT Greedy**: sort selected DMAs descending by composite, assign each to the lowest-sum group
4. **Local Search**: 50k iterations of random single-DMA moves and pair swaps to minimise max−min imbalance
5. **Target**: CV < 2%, max-min imbalance < 5% on both enrollment and spend
6. **Config knobs**: `N_PER_CELL` (default 9), `ENROLL_WEIGHT` / `SPEND_WEIGHT` (default 0.5 each)

---

## MMT Design
- Drop bottom-50 DMAs by enrollment from pool
- Sort remaining DMAs into 10 strata by size
- Within each stratum, pick the triplet maximising: `avg_pairwise_corr − 1.5 × enrollment_CV`
- Assign cells greedily to balance totals across Yahoo / DSP / Control
- Uses paired t-test for power (df = n_triplets − 1 = 9)

---

## Power Analysis Parameters
- α = 0.05, two-sided; power = 80%
- iCPE (incremental cost per enrollment) = $400
- Budget cap = $300,000 per partner
- Autocorrelation correction: Newey-West lag-1 variance inflation
- Pre-period noise estimated from historical weekly (treatment − control) / control relative differences

---

## Current Cell Assignments (Full Geo Test)

### Cell 1 — Yahoo Test (top DMAs by enrollment)
Dallas-Ft. Worth TX (267K), Cleveland-Akron OH (104K), Riverside-San Bernardino CA (99K), Portland OR (67K), La Crosse-Eau Claire WI (59K), Flint-Saginaw MI (56K), Richmond-Petersburg VA (47K), Waco-Temple-Bryan TX (43K), Kansas City MO (37K), Hattiesburg-Laurel MS (36K), Denver CO (35K), Albany-Schenectady-Troy NY (31K), Hartford-New Haven CT (31K), Des Moines-Ames IA (30K)...

### Cell 2 — DSP (Scope3) Test (top DMAs by enrollment)
Tampa-St. Pete FL (152K), Miami FL (122K), Sacramento CA (101K), Seattle-Tacoma WA (92K), Johnstown-Altoona PA (79K), Columbia SC (57K), Tucson-Sierra Vista AZ (49K), Phoenix AZ (48K), Wichita-Hutchinson KS (40K), Savannah GA (39K), Salt Lake City UT (36K), Albuquerque-Santa Fe NM (35K), Salt Lake City UT (33K), Raleigh-Durham NC (31K)...

### Cell 3 — Control Holdout (top DMAs by enrollment)
Washington DC (142K), Orlando FL (142K), Boston MA (99K), Denver CO (88K), Seattle-Tacoma WA (66K), Mobile AL (64K), Grand Rapids MI (53K), Greenville-New Bern NC (45K), Cedar Rapids IA (44K), Lubbock TX (37K), Knoxville TN (36K), Roanoke-Lynchburg VA (34K), Flint-Saginaw-Bay City MI (33K), Richmond-Petersburg VA (31K)...

---

## MMT Assignments (10 Triplets)
| Triplet | Yahoo Test | DSP (Scope3) | Control |
|---|---|---|---|
| 1 | Tampa-St. Pete (152K) | Washington DC (142K) | Orlando (142K) |
| 2 | Flint-Saginaw MI (56K) | Columbia SC (57K) | La Crosse-Eau Claire WI (59K) |
| 3 | Wichita-Hutchinson KS (40K) | Greenville-New Bern NC (45K) | Waco-Temple-Bryan TX (43K) |
| 4 | Lincoln-Hastings NE (30K) | Hartford-New Haven CT (31K) | Salt Lake City UT (33K) |
| 5 | Tri-Cities TN/VA (26K) | Tyler-Longview TX (27K) | Spokane WA (26K) |
| 6 | Tulsa OK (20K) | Biloxi-Gulfport MS (21K) | Ft. Wayne IN (20K) |
| 7 | Laredo TX (17K) | Huntsville-Decatur AL (19K) | Amarillo TX (19K) |
| 8 | Medford-Klamath Falls OR (17K) | Wichita Falls TX (17K) | Davenport IL/IA (17K) |
| 9 | Chico-Redding CA (14K) | Huntington-Charleston WV (14K) | Fargo-Valley City ND (14K) |
| 10 | Springfield-Holyoke MA (12K) | Palm Springs CA (11K) | Duluth MN (12K) |

---

## Current Cell Assignments (8–10 DMAs per cell, 27 total)
- **27 DMAs selected** from 164 eligible — top DMAs by composite score (50% enrollment + 50% paid spend)
- **Enrollment CV: 1.20%** ✓ | **Spend CV: 1.26%** ✓ (both well under 2% target)
- Balance chart (`dma_group_balance.png`) shows weekly enrollment + spend line graphs per cell

## Snowflake Connection
- **Role**: `SNOWFLAKE_PROD_ANALYST_OKTA`
- **Warehouse**: `ANALYTICS_WH`
- **Spend query**: joins `edw_db.core.member_details` + `edw_db.marketing.fact_marketing_user_spend` + `FIVETRAN.GSHEETS.ZIPCODE_TO_DMA` where `traffic_source = 'paid'`

## Open Questions / Next Steps
- [ ] Decide on test launch date and duration
- [ ] Review DMA assignments for geographic diversity / business sense
- [ ] Tune `N_PER_CELL` (currently 9) or `ENROLL_WEIGHT`/`SPEND_WEIGHT` if needed
