#!/usr/bin/env python3
"""Generate the Yahoo + DSP Geo Incrementality Test design document as HTML."""

import base64, os, pandas as pd

BASE = os.path.dirname(__file__)

# ── Load data ──────────────────────────────────────────────────────────────────
mmt = pd.read_csv(os.path.join(BASE, "mmt_group_assignments.csv"))
mmt["weekly_enrollments"] = (mmt["total_enrollments"] / (mmt["n_days"] / 7)).round(0).astype(int)

# ── Embed chart ────────────────────────────────────────────────────────────────
with open(os.path.join(BASE, "mmt_balance_power.png"), "rb") as f:
    chart_b64 = base64.b64encode(f.read()).decode()

# ── Cell summary numbers ───────────────────────────────────────────────────────
CELLS   = ["Yahoo Test", "DSP (Scope3) Test", "Control Holdout"]
COLORS  = {"Yahoo Test": "#1565C0", "DSP (Scope3) Test": "#E65100", "Control Holdout": "#2E7D32"}
BADGES  = {"Yahoo Test": "#E3F2FD", "DSP (Scope3) Test": "#FFF3E0", "Control Holdout": "#E8F5E9"}

totals  = mmt.groupby("cell")["total_enrollments"].sum()
weekly  = mmt.groupby("cell")["weekly_enrollments"].sum()
n_dmas  = mmt.groupby("cell").size()

# ── Build DMA table rows ───────────────────────────────────────────────────────
def dma_rows(cell_label):
    rows = ""
    for _, r in mmt[mmt["cell"] == cell_label].sort_values("triplet").iterrows():
        rows += f"""
        <tr>
          <td style="text-align:center">{int(r.triplet)}</td>
          <td>{r.dma_name}</td>
          <td style="text-align:center">{int(r.geo)}</td>
          <td style="text-align:right">{r.weekly_enrollments:,}</td>
        </tr>"""
    return rows

# ── Power table ────────────────────────────────────────────────────────────────
power_rows = [
    ("1 week",  "11.8%", "99%", "84%", "~$15K/DMA/wk", "Too short for learning phase"),
    ("2 weeks", "5.9%",  "87%", "84%", "~$15K/DMA/wk", "Well powered, tight pacing"),
    ("3 weeks", "4.0%",  "71%", "66%", "~$10K/DMA/wk", "Recommended — strong power, feasible pacing"),
    ("4 weeks", "3.0%",  "57%", "53%", "~$7.5K/DMA/wk","Directional only"),
    ("6 weeks", "2.0%",  "40%", "36%", "~$5K/DMA/wk",  "Insufficient power"),
]

power_table_rows = ""
for dur, lift, yp, dp, pacing, note in power_rows:
    is_rec = dur == "3 weeks"
    bg = "background:#F0FFF4; font-weight:600;" if is_rec else ""
    rec_badge = " <span style='background:#2E7D32;color:white;border-radius:4px;padding:1px 6px;font-size:11px;'>Recommended</span>" if is_rec else ""
    power_table_rows += f"""
    <tr style="{bg}">
      <td>{dur}{rec_badge}</td>
      <td style="text-align:center">{lift}</td>
      <td style="text-align:center">{yp}</td>
      <td style="text-align:center">{dp}</td>
      <td style="text-align:center">{pacing}</td>
      <td>{note}</td>
    </tr>"""

# ── HTML ───────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Yahoo & DSP Display — Geo Incrementality Test Design</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         font-size: 14px; color: #1A1A2E; background: #F7F8FC; padding: 32px; line-height: 1.6; }}
  .page {{ max-width: 960px; margin: 0 auto; background: white; border-radius: 12px;
           box-shadow: 0 2px 16px rgba(0,0,0,0.08); padding: 48px; }}

  /* Header */
  .header {{ border-bottom: 3px solid #1565C0; padding-bottom: 20px; margin-bottom: 32px; }}
  .header h1 {{ font-size: 26px; color: #1565C0; font-weight: 700; }}
  .header .subtitle {{ color: #555; margin-top: 6px; font-size: 14px; }}
  .meta {{ display: flex; gap: 24px; margin-top: 14px; }}
  .meta-item {{ font-size: 12px; color: #666; }}
  .meta-item strong {{ color: #333; }}

  /* Section headings */
  h2 {{ font-size: 17px; font-weight: 700; color: #1A1A2E; margin: 36px 0 14px;
        padding-bottom: 6px; border-bottom: 1px solid #E0E4F0; }}
  h3 {{ font-size: 14px; font-weight: 700; color: #333; margin: 20px 0 10px; }}

  /* Recommendation box */
  .rec-box {{ background: #EBF5EB; border-left: 4px solid #2E7D32; border-radius: 6px;
              padding: 18px 22px; margin-bottom: 28px; }}
  .rec-box .rec-title {{ font-weight: 700; font-size: 15px; color: #1B5E20; margin-bottom: 8px; }}
  .rec-box p {{ color: #2E4A2E; font-size: 13.5px; margin-top: 6px; }}
  .rec-box ul {{ padding-left: 20px; margin-top: 8px; color: #2E4A2E; font-size: 13.5px; }}
  .rec-box ul li {{ margin-bottom: 4px; }}

  /* Info callout */
  .callout {{ background: #F0F4FF; border-left: 4px solid #1565C0; border-radius: 6px;
              padding: 14px 18px; margin: 16px 0; font-size: 13px; color: #1A237E; }}

  /* Summary cards */
  .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }}
  .card {{ border-radius: 8px; padding: 18px; border: 1px solid #E0E4F0; }}
  .card .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px;
                  font-weight: 600; margin-bottom: 4px; }}
  .card .value {{ font-size: 22px; font-weight: 700; }}
  .card .sub {{ font-size: 11px; color: #666; margin-top: 4px; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 12px 0; }}
  th {{ background: #F0F4FF; color: #1A237E; font-weight: 600; padding: 9px 12px;
        text-align: left; border-bottom: 2px solid #C5CAE9; font-size: 12px;
        text-transform: uppercase; letter-spacing: 0.4px; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #F0F0F8; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #FAFBFF; }}

  /* Cell section tabs */
  .cell-section {{ margin-bottom: 28px; }}
  .cell-header {{ border-radius: 6px 6px 0 0; padding: 10px 16px; font-weight: 700;
                  font-size: 13px; display: flex; justify-content: space-between; }}
  .cell-table-wrap {{ border: 1px solid #E0E4F0; border-top: none; border-radius: 0 0 6px 6px; overflow: hidden; }}

  /* Chart */
  .chart-wrap {{ text-align: center; margin: 20px 0; }}
  .chart-wrap img {{ max-width: 100%; border-radius: 8px; border: 1px solid #E0E4F0; }}

  /* Footer */
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #E0E4F0;
             font-size: 11px; color: #999; display: flex; justify-content: space-between; }}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <h1>Yahoo & DSP Display — Geo Incrementality Test Design</h1>
    <div class="subtitle">Matched Market Test (MMT) | 3-Cell Design | MDF-1629</div>
    <div class="meta">
      <div class="meta-item"><strong>Date:</strong> May 2026</div>
      <div class="meta-item"><strong>Partners:</strong> Yahoo Display · DSP (Scope3)</div>
      <div class="meta-item"><strong>Budget:</strong> $300K per partner</div>
      <div class="meta-item"><strong>iCPE:</strong> $400</div>
      <div class="meta-item"><strong>Design:</strong> 10 triplets × 3 cells</div>
    </div>
  </div>

  <!-- Recommendation -->
  <div class="rec-box">
    <div class="rec-title">Recommendation: 3-Week Concentrated Flight</div>
    <p>
      Based on power analysis of our 10 matched DMA triplets, we recommend concentrating the $300K budget
      into a <strong>3-week flight</strong> rather than spreading it over 4–6 weeks.
      This delivers ~70% power for Yahoo and ~66% for DSP — the strongest achievable
      result within the budget envelope while keeping pacing realistic at ~$10K per DMA per week.
    </p>
    <ul>
      <li><strong>$300K → 750 incremental enrollments</strong> (at $400 iCPE) — fixed regardless of flight length</li>
      <li>Shorter = stronger weekly signal = easier to detect above market noise</li>
      <li>3 weeks gives campaigns one week to exit learning phase + two clean measurement weeks</li>
      <li>Spreading to 4–6 weeks drops power to 40–57% — results would be directional at best</li>
    </ul>
  </div>

  <!-- Why geo tests need more budget callout -->
  <div class="callout">
    <strong>Note on geo vs. user-level test sizing:</strong> Geo tests are inherently noisier than
    user-level holdouts because the unit of randomization is a DMA (10 markets), not an individual user.
    Week-to-week market fluctuations (~7–8% per DMA pair) require a higher signal to detect lift,
    which is why the budget requirement is higher than a standard user-level calculator would suggest.
  </div>

  <!-- Test Design Overview -->
  <h2>Test Design Overview</h2>
  <div class="cards">
    <div class="card" style="background:#E3F2FD; border-color:#BBDEFB;">
      <div class="label" style="color:#1565C0;">Cell 1</div>
      <div class="value" style="color:#1565C0;">Yahoo Test</div>
      <div class="sub">10 DMAs · {weekly["Yahoo Test"]:,} enrollments/week</div>
    </div>
    <div class="card" style="background:#FFF3E0; border-color:#FFE0B2;">
      <div class="label" style="color:#E65100;">Cell 2</div>
      <div class="value" style="color:#E65100;">DSP (Scope3) Test</div>
      <div class="sub">10 DMAs · {weekly["DSP (Scope3) Test"]:,} enrollments/week</div>
    </div>
    <div class="card" style="background:#E8F5E9; border-color:#C8E6C9;">
      <div class="label" style="color:#2E7D32;">Cell 3</div>
      <div class="value" style="color:#2E7D32;">Control Holdout</div>
      <div class="sub">10 DMAs · {weekly["Control Holdout"]:,} enrollments/week</div>
    </div>
  </div>

  <table>
    <tr>
      <th>Parameter</th>
      <th>Value</th>
    </tr>
    <tr><td>Test methodology</td><td>Matched Market Test (MMT) — stratified triplet sampling</td></tr>
    <tr><td>Matching approach</td><td>Max avg. pairwise weekly enrollment correlation within strata</td></tr>
    <tr><td>DMAs per cell</td><td>10 (30 total across 3 cells)</td></tr>
    <tr><td>Excluded markets</td><td>46 DMAs (active geo tests + large markets) not eligible</td></tr>
    <tr><td>Cell balance CV</td><td>0.08% — near-perfect enrollment balance across cells</td></tr>
    <tr><td>Statistical test</td><td>Paired t-test, n=10, df=9, α=0.05, two-sided</td></tr>
    <tr><td>Within-pair noise (σ)</td><td>~7.7% (Yahoo) · ~8.0% (DSP)</td></tr>
    <tr><td>Measurement approach</td><td>Within-triplet DiD: (treat − ctrl) / ctrl per week</td></tr>
  </table>

  <!-- Chart -->
  <h2>DMA Match Quality & Power Curve</h2>
  <div class="chart-wrap">
    <img src="data:image/png;base64,{chart_b64}" alt="MMT Balance and Power Chart">
  </div>
  <p style="font-size:12px; color:#666; text-align:center; margin-top:8px;">
    Left: weekly enrollment trend by cell. Centre: enrollment profile — overlapping lines confirm tight DMA matching.
    Right: MDE vs. test duration — × marks show implied lift achievable at $300K per week count.
  </p>

  <!-- DMA Assignments -->
  <h2>DMA Assignments — 10 Matched Triplets</h2>
  <p style="font-size:13px; color:#555; margin-bottom:16px;">
    Each row group is a triplet: one DMA per cell, matched on weekly enrollment correlation.
    Ads run only in the Yahoo Test and DSP Test DMAs; Control DMAs receive no display spend.
  </p>

  <!-- Yahoo -->
  <div class="cell-section">
    <div class="cell-header" style="background:#1565C0; color:white;">
      <span>Cell 1 — Yahoo Test</span>
      <span>10 DMAs · {totals["Yahoo Test"]:,.0f} total enrollments · {weekly["Yahoo Test"]:,}/week</span>
    </div>
    <div class="cell-table-wrap">
      <table>
        <tr><th>Triplet</th><th>DMA Name</th><th>DMA Code</th><th style="text-align:right">Enrollments/wk</th></tr>
        {dma_rows("Yahoo Test")}
      </table>
    </div>
  </div>

  <!-- DSP -->
  <div class="cell-section">
    <div class="cell-header" style="background:#E65100; color:white;">
      <span>Cell 2 — DSP (Scope3) Test</span>
      <span>10 DMAs · {totals["DSP (Scope3) Test"]:,.0f} total enrollments · {weekly["DSP (Scope3) Test"]:,}/week</span>
    </div>
    <div class="cell-table-wrap">
      <table>
        <tr><th>Triplet</th><th>DMA Name</th><th>DMA Code</th><th style="text-align:right">Enrollments/wk</th></tr>
        {dma_rows("DSP (Scope3) Test")}
      </table>
    </div>
  </div>

  <!-- Control -->
  <div class="cell-section">
    <div class="cell-header" style="background:#2E7D32; color:white;">
      <span>Cell 3 — Control Holdout</span>
      <span>10 DMAs · {totals["Control Holdout"]:,.0f} total enrollments · {weekly["Control Holdout"]:,}/week</span>
    </div>
    <div class="cell-table-wrap">
      <table>
        <tr><th>Triplet</th><th>DMA Name</th><th>DMA Code</th><th style="text-align:right">Enrollments/wk</th></tr>
        {dma_rows("Control Holdout")}
      </table>
    </div>
  </div>

  <!-- Power & Budget -->
  <h2>Power Analysis — 3-Week Recommended Flight</h2>

  <div class="cards" style="grid-template-columns: repeat(4, 1fr);">
    <div class="card" style="background:#F0FFF4; border-color:#A5D6A7;">
      <div class="label" style="color:#1B5E20;">Budget</div>
      <div class="value" style="color:#1B5E20;">$300K</div>
      <div class="sub">per partner</div>
    </div>
    <div class="card" style="background:#F0FFF4; border-color:#A5D6A7;">
      <div class="label" style="color:#1B5E20;">iCPE</div>
      <div class="value" style="color:#1B5E20;">$400</div>
      <div class="sub">assumed</div>
    </div>
    <div class="card" style="background:#F0FFF4; border-color:#A5D6A7;">
      <div class="label" style="color:#1B5E20;">Incr. Enrollments</div>
      <div class="value" style="color:#1B5E20;">750</div>
      <div class="sub">total expected</div>
    </div>
    <div class="card" style="background:#F0FFF4; border-color:#A5D6A7;">
      <div class="label" style="color:#1B5E20;">Pacing</div>
      <div class="value" style="color:#1B5E20;">$10K</div>
      <div class="sub">per DMA per week</div>
    </div>
  </div>

  <table style="margin-top:16px;">
    <tr>
      <th>Duration</th>
      <th style="text-align:center">Implied Lift</th>
      <th style="text-align:center">Yahoo Power</th>
      <th style="text-align:center">DSP Power</th>
      <th style="text-align:center">Pacing/DMA/wk</th>
      <th>Notes</th>
    </tr>
    {power_table_rows}
  </table>

  <div class="callout" style="margin-top:20px;">
    <strong>How to read this:</strong> "Implied lift" is the relative enrollment increase we expect in test DMAs
    given the $300K budget, calculated as (weekly incremental enrollments) ÷ (control weekly enrollments).
    "Power" is the probability of detecting that lift as statistically significant. At 3 weeks, ~70% power
    means there's a 70% chance we correctly identify Yahoo's impact — strong enough to make a go/no-go call.
  </div>

  <!-- Key Assumptions -->
  <h2>Key Assumptions & Constraints</h2>
  <table>
    <tr><th>Assumption</th><th>Value</th><th>Notes</th></tr>
    <tr><td>iCPE</td><td>$400</td><td>If true iCPE is higher, fewer incr. enrollments → lower implied lift → lower power</td></tr>
    <tr><td>Significance level (α)</td><td>0.05 (two-sided)</td><td>95% confidence threshold</td></tr>
    <tr><td>Statistical power target</td><td>80%</td><td>3-week flight achieves ~70% — slightly below target, acceptable for geo test</td></tr>
    <tr><td>Excluded DMAs</td><td>46 markets</td><td>Active geo tests (20) + large markets (26) excluded from DMA pool</td></tr>
    <tr><td>Bottom-50 exclusion</td><td>50 smallest DMAs</td><td>Excluded to avoid markets too small to drive measurable lift at $30K spend</td></tr>
    <tr><td>Pre-period data</td><td>~61 weeks</td><td>May 2025 – Apr 2026 used for matching and noise estimation</td></tr>
    <tr><td>Attribution</td><td>Display incrementality</td><td>Enrollment uplift measured via geo DiD, not last-touch</td></tr>
  </table>

  <!-- Footer -->
  <div class="footer">
    <span>Yahoo & DSP Display Geo Test — MDF-1629</span>
    <span>Prepared May 2026 · Rohith Devarasetty</span>
  </div>

</div>
</body>
</html>"""

out = os.path.join(BASE, "geo_test_design.html")
with open(out, "w") as f:
    f.write(html)
print(f"Document saved: {out}")
