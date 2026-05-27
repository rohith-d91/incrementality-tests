# DSP Yahoo Geo Test — Project Context
**Ticket:** MDF-1629
**Last updated:** 2026-05-26 (post-audit refactor)

> ⚠️ **Major audit completed 2026-05-26.** The original `DMA_NAMES` dict in `balance_design2.py` had 115/211 codes mislabeled. See **`DMA_AUDIT_AND_REDESIGN.md`** for full findings. All output below reflects the corrected MMT design.

---

## Goal
Run a **3-cell DMA geo-level incrementality test** to measure whether Yahoo DSP and/or Scope3 DSP advertising drives incremental Chime enrollments vs. a pure control holdout.

---

## Test Design (Design 2 — MMT)

### Cells
| # | Label | Purpose |
|---|---|---|
| 1 | Yahoo Test | DMAs exposed to Yahoo DSP ads |
| 2 | DSP (Scope3) Test | DMAs exposed to Scope3 DSP ads |
| 3 | Control Holdout | No DSP ads (pure holdout) |

### Algorithm: Matched Market Test (MMT)
- 10 matched triplets (1 DMA per cell per triplet)
- Triplets formed by stratifying eligible pool by enrollment+spend composite, then within each stratum picking the 3 DMAs maximising `avg_pairwise_correlation − 0.5×CV_enroll − 0.5×CV_spend` on weekly enrollments
- Cells assigned within each triplet to balance overall totals via brute-force permutation
- Cell-level z-test on weekly relative differences for power (matches paper methodology)

### Power Design (from the design paper, Yahoo + Scope3 doc)
| Parameter | Value |
|-----------|-------|
| Flight duration | 3 weeks |
| Budget per partner | $300,000 |
| iCPE assumption | $400 |
| Expected incremental enrollments | 750 per partner |
| Expected lift | ~5.6% |
| Statistical power | **80%** |
| α (significance) | 0.05 two-sided |

---

## Key Files

| File | Description |
|---|---|
| `balance_design2.py` | **Main script** — canonical DMA_NAMES, fixed exclusions, MMT algorithm, parallel-trends chart |
| `May 2025- 2026 Data by DMA.csv` | Raw daily data (88K rows, 60 weeks, 210 DMAs) — uses correct Nielsen codes |
| `dma_paid_spend.csv` | Paid spend by DMA + date from Snowflake — uses correct Nielsen codes |
| `fetch_spend.py` | Snowflake pull script (no changes — codes were always correct) |
| `design2_dma_group_assignments.csv` | **Output** — 30-DMA MMT cell assignments with correct Nielsen names |
| `design2_parallel_trends.png` | **Output** — 4-panel validation chart |
| `DMA_AUDIT_AND_REDESIGN.md` | **Full audit + redesign rationale** |
| `Yahoo_DSP_Geo_Test_Design.docx` | Design document (to be regenerated) |
| `generate_doc.py` / `generate_docx.py` | Doc generators |

---

## Exclusions (applied in `balance_design2.py`)

### (A) Active geo tests (20 DMAs) — Samsung + tvScientific
Jackson MS (718), Shreveport LA (612), Cincinnati OH (515), Little Rock AR (693), Norfolk VA (544), Greensboro NC (518), El Paso TX (765), Harlingen TX (636), Harrisburg PA (566), West Palm Beach FL (548), Macon GA (503), Joplin MO/Pittsburg KS (522), Charleston WV (564), Dayton OH (542), Fresno CA (866), San Diego CA (825), Greenville SC/NC (567), Minneapolis MN (514), Chattanooga TN (575), Baton Rouge LA (716)

### (B) Large markets (30 DMAs)
NY (501), LA (803), Dallas (623), Houston (618), Memphis (640), Indianapolis (527), Kansas City (616), Detroit (505), Birmingham (630), Baltimore (512), Charlotte (517), Atlanta (524), Louisville (529), Columbus OH (535), Philadelphia (504), San Francisco (807), Phoenix (753), Nashville (659), Chicago (602), New Orleans (622), Pittsburgh (508), Oklahoma City (650), St. Louis (609), Las Vegas (839), San Antonio (641), Jacksonville (561), Milwaukee (617), Washington DC (511), Salt Lake City (770), Seattle-Tacoma (819)

### (C) Design 1 DMAs (58 codes — defensive double-coding)
- 30 codes from Design 1's original output (`DESIGN1_ORIGINAL_CODES`)
- 28 canonical Nielsen codes for the intended-market names from Design 1 (`DESIGN1_INTENDED_CODES`)
- Union = 58 unique codes; defensive double-coding protects against the same name↔code drift that caused this audit

### (D) Offshore — 4 DMAs
Anchorage (743), Honolulu (744), Fairbanks (745), Juneau (747)

### (E) Bottom-50 by enrollment — automatically excluded
Markets too small to detect meaningful lift.

**Net eligible pool: 73 DMAs** (after all exclusions)

---

## Final MMT Assignments (10 Triplets × 3 Cells = 30 DMAs)

| Triplet | Yahoo Test (ads ON) | DSP (Scope3) Test (ads ON) | Control Holdout (ads OFF) |
|:-:|:-:|:-:|:-:|
| 1 | Spokane, WA | Albany-Schenectady-Troy, NY | Toledo, OH |
| 2 | Montgomery-Selma, AL | Tri-Cities, TN/VA | Tallahassee, FL-Thomasville, GA |
| 3 | Lafayette, LA | Tyler-Longview, TX | Evansville, IN |
| 4 | Rochester, NY | Monroe, LA-El Dorado, AR | Ft. Wayne, IN |
| 5 | Beaumont-Port Arthur, TX | Albany, GA | Odessa-Midland, TX |
| 6 | Yakima-Pasco-Richland-Kennewick, WA | Amarillo, TX | Wichita Falls, TX-Lawton, OK |
| 7 | Biloxi-Gulfport, MS | Lincoln-Hastings-Kearney, NE | Peoria-Bloomington, IL |
| 8 | Burlington, VT-Plattsburgh, NY | Springfield-Holyoke, MA | Fargo-Valley City, ND |
| 9 | Terre Haute, IN | Rockford, IL | Abilene-Sweetwater, TX |
| 10 | Alexandria, LA | Jonesboro, AR | Salisbury, MD |

### Balance
| Cell | DMAs | Enrollments | Spend |
|------|-----|------------|-------|
| 1 — Yahoo Test | 10 | 198,468 | $1,627.5M |
| 2 — DSP (Scope3) | 10 | 200,102 | $1,613.1M |
| 3 — Control | 10 | 199,660 | $1,624.2M |

- **Enrollment CV: 0.346%** ✓ (target <2%)
- **Spend CV: 0.379%** ✓ (target <2%)
- **Enroll imbalance: 0.819%** ✓ (target <5%)
- **Spend imbalance: 0.885%** ✓ (target <5%)

### Parallel Trends Validation (pre-period: Feb 2025 – Apr 2026, 60 weeks)
| Pair | Weekly enrollment correlation |
|------|------------------------------|
| Yahoo Test vs Control | **r = +0.967** ✓ |
| DSP Test vs Control | **r = +0.969** ✓ |
| Yahoo Test vs DSP Test | **r = +0.968** ✓ |

### Power
- **Yahoo vs Control**: σ_eff = 2.74%, achieved power = **99.8%** ✓ (target 80%)
- **DSP vs Control**: σ_eff = 2.35%, achieved power = **100%** ✓ (target 80%)

---

## Data Schema (`May 2025- 2026 Data by DMA.csv`)
```
index, geo (DMA code), assignment (prior cell), date, total users, cta taps, enrollments, dd_30
```
- `dd_30`: 30-day direct deposit metric
- `cta taps`: call-to-action taps (ad engagement proxy)
- `assignment`: prior test assignment (Cell A YouTube / Cell B Meta / Cell C Control / Excluded)

---

## Snowflake Connection
- **Role**: `SNOWFLAKE_PROD_ANALYST_OKTA`
- **Warehouse**: `ANALYTICS_WH`
- **Spend query**: joins `edw_db.core.member_details` + `edw_db.marketing.fact_marketing_user_spend` + `FIVETRAN.GSHEETS.ZIPCODE_TO_DMA` where `traffic_source = 'paid'`

---

## Open Questions / Next Steps
- [ ] Regenerate `Yahoo_DSP_Geo_Test_Design.docx` from the new MMT outputs
- [ ] Re-share the corrected paper with marketing (the original Google Doc has the same DMA mislabels)
- [ ] Confirm test launch date
- [ ] Verify active-test exclusions (Samsung, tvScientific) are still active in May 2026
