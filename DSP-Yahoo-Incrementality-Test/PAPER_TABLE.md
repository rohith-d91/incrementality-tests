# Corrected Paper Table — Design 2 MMT

Drop this into the Yahoo + Scope3 design paper (Google Doc) replacing the
old "Matched Markets" table that had Spokane appearing in 3 rows.

---

## Matched Markets

Each row is a matched triplet. Ads run only in Yahoo Test and DSP Test markets;
Control markets receive no display spend from either partner.

| Triplet | **Yahoo Test (ads ON)** | **DSP (Scope3) Test (ads ON)** | **Control Holdout (ads OFF)** |
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

---

## Pre-Test Validation (replace existing paragraph)

Test and control markets show strong alignment in weekly enrollments over
the pre-period (Feb 2025 – Apr 2026, 60 weeks). Weekly enrollment
correlations across all three cells exceed **r = 0.96**, and the
pre-period relative differences (Treat − Control) / Control stay within
**±7%** with low autocorrelation. Each triplet was selected to maximise
within-triplet pairwise correlation on weekly enrollments while keeping
size (enrollment + spend) variation low — giving confidence that any
divergence during the campaign can be attributed to the ads.

## Test Recommendation (no change to numbers)

- **Recommended flight duration:** 3 weeks
- **Budget:** $300K per partner
- **Assumed iCPE:** $400
- **Expected incremental enrollments:** ~750 per partner
- **Lift this budget is expected to drive:** ~5.6%
- **Statistical power:** ≥80% for both Yahoo and DSP (cell-level z-test on weekly relative diffs)
- **Flight structure:** Week 1 allows the campaigns to exit the platform learning phase; Weeks 2–3 are the primary measurement window

---

## What Changed vs the Previous Paper Version

The previous version of this paper had market names mislabeled because of
a bug in the underlying `DMA_NAMES` lookup dict in `balance_design2.py`
(115 of 211 codes wrong). The most visible effect: **3 different markets
all displayed as "Spokane, WA"** (real Spokane is in this corrected table,
along with the previously-mislabeled markets at their true names — the
previously-shown "Spokane" in the DSP cell was actually South Bend-Elkhart,
IN, and the previously-shown "Spokane" in the Control cell was Honolulu,
HI — now excluded entirely as we want a mainland-only design).

The underlying *codes* were always correct, so the algorithm picked real,
distinct DMAs. Only the *labels* were wrong. See `DMA_AUDIT_AND_REDESIGN.md`
for the full audit.
