# DMA Mapping Audit & Design 2 Redesign

**Date:** 2026-05-26
**Ticket:** MDF-1629
**Author:** Audit triggered by question "why is Spokane in all 3 cells?"

---

## TL;DR

The original `balance_design2.py` had a **systematically broken `DMA_NAMES` dictionary** (115 of 211 codes mislabeled, 54% wrong). This caused:

1. **3 different DMAs (588 South Bend, 744 Honolulu, 881 Spokane) all displayed as "Spokane, WA"** in the output CSV and design paper.
2. **Honolulu (offshore) accidentally chosen as a Control market** for what was supposed to be a mainland test.
3. **At least 1 confirmed contamination with Design 1** — real Greenville-New Bern, NC (code 545) appeared in both Design 1 (DSP cell) and Design 2 (Yahoo cell), because the Design 1 exclusion list had code 557 (actually Knoxville) labeled as "Greenville-New Bern".
4. **Silent exclusion of Salt Lake City** — `LARGE_MARKET_EXCLUSIONS` had code 770 labeled "Seattle-Tacoma" but 770 is actually Salt Lake City.

The **data files** (`May 2025- 2026 Data by DMA.csv` and `dma_paid_spend.csv`) use **correct Nielsen DMA codes**. The bug was purely in the Python `DMA_NAMES` lookup dict and its derived exclusion lists.

---

## Audit Findings

### `DMA_NAMES` dict: 115 of 211 codes wrong

Sample of the most consequential errors:

| Code | Pre-refactor label | Actual Nielsen |
|------|-------------------|----------------|
| 519 | Syracuse, NY | **Charleston, SC** |
| 520 | Raleigh-Durham, NC | **Augusta, GA-Aiken, SC** |
| 521 | Knoxville, TN | **Columbus, GA-Auburn, AL** |
| 530 | Hartford-New Haven, CT | **Tallahassee, FL** |
| 545 | Oklahoma City, OK | **Greenville-New Bern, NC** |
| 547 | Richmond-Petersburg, VA | **Toledo, OH** |
| 555 | Wilkes Barre-Scranton, PA | **Syracuse, NY** |
| 557 | Greenville-New Bern, NC | **Knoxville, TN** |
| 571 | Salt Lake City, UT | **Ft. Myers-Naples, FL** |
| 588 | Spokane, WA | **South Bend-Elkhart, IN** |
| 670 | Des Moines-Ames, IA | **Ft. Smith-Fayetteville, AR** |
| 678 | Salt Lake City, UT | **Wichita-Hutchinson, KS** |
| 698 | Lincoln-Hastings, NE | **Montgomery-Selma, AL** |
| 744 | Spokane, WA | **Honolulu, HI** |
| 757 | Yuma, AZ-El Centro, CA | **Boise, ID** |
| 770 | Seattle-Tacoma, WA | **Salt Lake City, UT** |
| 800 | Boise, ID | **Bakersfield, CA** |

…and ~100 more. The dict appears to have been built by appending entries over time without verification against a canonical source.

### Exclusion list mismatches

**`ACTIVE_TEST_EXCLUSIONS`** — 1 of 20 wrong:
- Code `522` labeled "Columbus, GA" — actually **Joplin, MO-Pittsburg, KS**. Real Columbus GA = 521. (Effect: Joplin excluded by accident; real Columbus GA was not, but was caught by the active list intent.)

**`LARGE_MARKET_EXCLUSIONS`** — 1 of 30 wrong:
- Code `770` labeled "Seattle-Tacoma" — actually **Salt Lake City, UT**. Real Seattle = 819 (also in list). (Effect: SLC silently excluded as a "large market".)

**`DESIGN1_DMAS`** — 14 of 30 wrong codes. Most consequential:
| Code | Pre-refactor label | Actually is |
|------|-------------------|-------------|
| 686 | La Crosse-Eau Claire, WI | Mobile, AL-Pensacola, FL |
| 671 | Flint-Saginaw, MI | Tulsa, OK |
| 577 | Wichita-Hutchinson, KS | Wilkes Barre-Scranton, PA |
| 557 | Greenville-New Bern, NC | Knoxville, TN |
| 678 | Salt Lake City, UT | Wichita-Hutchinson, KS |
| 560 | Sacramento, CA | Raleigh-Durham, NC |
| 533 | Columbia, SC | Hartford-New Haven, CT |
| 546 | Cedar Rapids, IA | Columbia, SC |
| 691 | Lubbock, TX | Huntsville-Decatur, AL |
| 570 | Denver, CO | Florence-Myrtle Beach, SC |
| 862 | Riverside-San Bernardino, CA | Sacramento, CA |
| 635 | Mobile, AL-Pensacola, FL | Austin, TX |
| 789 | Albuquerque-Santa Fe, NM | Tucson, AZ |
| 790 | Phoenix, AZ | Albuquerque-Santa Fe, NM |

### Confirmed contamination

**Real Greenville-New Bern-Washington, NC (code 545)** appeared in:
- Design 1 → DSP Test cell (per `PROJECT_CONTEXT.md` design intent)
- Design 2 (pre-refactor) → Yahoo Test cell (`design2_dma_group_assignments.csv` row 4, labeled "Oklahoma City, OK")

Without the fix, Greenville-New Bern would have received **both Meta/YouTube (from Design 1) AND Yahoo DSP (from Design 2)** during overlapping windows, confounding both tests for that market.

---

## How the bug originated (hypothesis)

The `DMA_NAMES` dict was likely built by hand by someone looking up codes from a Nielsen-coded data source (the Snowflake/Google-Sheets zipcode-to-DMA mapping) and pairing them with market names from a different reference — possibly a marketing-team spreadsheet that used a non-Nielsen DMA numbering or had typos.

Two specific patterns of error suggest the wrong-but-self-consistent labelling came from a single bad reference:
1. Codes 588 / 744 / 881 all labeled "Spokane, WA" — suggests a manual lookup that defaulted multiple unknown codes to the same name.
2. Codes 678 / 571 / 801 all labeled "Salt Lake City, UT" — same pattern.

Once the dict was set, every downstream artifact (output CSVs, balance charts, the design paper in Google Docs) inherited the wrong labels — but the underlying **codes** remained correct, so the *algorithm* picked real, distinct DMAs. The disconnect only became visible when stakeholders read names and noticed "Spokane" repeating.

---

## Redesign (Design 2 v2)

### Configuration changes

| Parameter | Old | New | Source |
|-----------|-----|-----|--------|
| `POWER_TARGET` | 0.70 | **0.80** | design paper |
| Algorithm | Full Geo Test (cell balancing) | **MMT (10 matched triplets)** | design paper |
| `DMA_NAMES` | 115/211 wrong | **Canonical Nielsen (verified)** | Nielsen 2024 + TLMD |
| Bottom-N exclusion | implicit | **Explicit: bottom 50 by enrollment** | design paper |
| Offshore exclusion | none | **{743, 744, 745, 747}** added | marketing requirement |
| Design 1 exclusion | 30 (mislabeled) codes | **30 original + 28 canonical-name codes** (defensive double-coding) | audit |

### New triplet assignments

| # | Yahoo Test (ads ON) | DSP (Scope3) Test (ads ON) | Control Holdout (ads OFF) |
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

### Validation

| Check | Result |
|-------|--------|
| Independent Nielsen code↔name verification (30/30 markets) | ✓ ALL MATCH |
| Enrollment-vs-TV-HH sanity (no mapping errors) | ✓ PASS |
| Zero overlap with Design 1 (original codes) | ✓ NONE |
| Zero overlap with Design 1 (intended-market canonical codes) | ✓ NONE |
| No Hawaii/Alaska in any cell | ✓ NONE |
| Enrollment cell CV | **0.346%** (target <2%) |
| Spend cell CV | **0.379%** (target <2%) |
| Enrollment max-min imbalance | **0.819%** (target <5%) |
| Spend max-min imbalance | **0.885%** (target <5%) |
| Weekly enrollment correlation Yahoo↔Control | **r = +0.967** |
| Weekly enrollment correlation DSP↔Control | **r = +0.969** |
| Weekly spend correlation Yahoo↔Control | **r = +0.972** |
| Weekly spend correlation DSP↔Control | **r = +0.969** |
| Pre-period |max| relative diff vs Control | < 7.3% |
| Per-triplet within-pair correlations (30 pairs) | All ≥ 0.60, median 0.72 |

### Power analysis

Cell-level z-test on weekly relative differences (matches paper methodology):
- **Yahoo vs Control**: σ_eff = 2.74%, achieved power = **99.8%** ✓
- **DSP vs Control**: σ_eff = 2.35%, achieved power = **100%** ✓

Both exceed the 80% paper target with significant margin.

---

## Lessons for Future Tests

1. **Never hand-build a code↔name lookup dict.** Always derive it from an authoritative source (e.g., a Snowflake table sourced from the broadcaster's Nielsen feed) and verify on load.

2. **For any market-exclusion list, store the *intended market* alongside the code** and validate at runtime that the code's canonical name matches the intended market — fail loudly if not.

3. **For multi-stage tests (Design 1 → Design 2 → Design 3…), use *defensive double-coding* on exclusions** — include both the original codes from prior outputs AND canonical codes for intended market names. The combined cost is a few extra excluded DMAs; the safety against label drift is significant.

4. **Always validate generated reports against the team's mental model before sharing.** The "Spokane in 3 cells" question would have caught this 2 design iterations ago.

5. **Sanity-check by demographic ratio.** `enrollments / TV_HH` for known mid-size markets should fall in a consistent range (60–110 per HH for Chime's target audience in mid-US markets). Outliers >2× or <0.5× the median should be investigated as potential mapping bugs.

6. **For 3-cell incrementality tests, the MMT (matched triplet) design is more defensible than the Full Geo Test cell-balancing approach.** Triplet matching produces tighter pre-period correlations (>0.95 cell-aggregate) and reduces the chance that random differences in cell composition look like treatment effects.

---

## Files Replaced in This Redesign

| File | What Changed |
|------|-------------|
| `balance_design2.py` | Full refactor: canonical `DMA_NAMES`, fixed exclusions, MMT algorithm, 80% power |
| `design2_dma_group_assignments.csv` | New 30-DMA MMT assignments with correct Nielsen names |
| `design2_parallel_trends.png` | New 4-panel parallel-trends validation chart |
| `design2_dma_group_balance.png` | Deleted (stale, from old Full Geo Test run with wrong labels) |
| `design2_power_analysis.png` | Deleted (stale, computed at 70% power vs 80% target) |
| `PROJECT_CONTEXT.md` | Updated to reference new MMT design and audit findings |
| `DMA_AUDIT_AND_REDESIGN.md` | NEW — this document |

## Files Unchanged

| File | Why |
|------|-----|
| `May 2025- 2026 Data by DMA.csv` | Source data uses correct Nielsen codes |
| `dma_paid_spend.csv` | Source data uses correct Nielsen codes |
| `fetch_spend.py` | Snowflake pull script is fine; the codes it returns are correct |
| `Yahoo_DSP_Geo_Test_Design.docx` | To be regenerated from the new outputs |
| `generate_doc.py`, `generate_docx.py` | Doc generators; will produce correct output now that inputs are fixed |
