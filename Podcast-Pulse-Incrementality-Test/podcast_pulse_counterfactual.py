#!/usr/bin/env python3
"""
Podcast Pulse Counterfactual Analysis
======================================
Tests whether podcast spend pulsing periods produced statistically significant
changes in overall daily enrollments vs. a time-series counterfactual baseline.

Spend periods (Avg Test Spend = actual spend during each window):
  BAU       : 3/16/2026 – 3/31/2026  | $228,944 total  (2.5 wks · ~$91.6K/wk)
  50% BAU   : 4/01/2026 – 4/21/2026  | $330,000 total  (3 wks   · $110K/wk)
  150% BAU  : 4/22/2026 – 4/30/2026  | $220,000 total  (1 wk    · $220K/wk)

Methodology:
  1. Load pre-aggregated daily enrollments from "Enrollments by date.csv".
  2. Train a Prophet model on May 1 2025 – Mar 23 2026.
       - Additive weekly seasonality (Fourier order 3)
       - Additive yearly seasonality (Fourier order 5, captures spring uptick)
       - Flexible piecewise-linear trend (changepoint_prior_scale=0.05)
       - 95% uncertainty intervals via posterior sampling
  3. Validate on Mar 24 – Mar 31 2026 (final BAU week, no spend change).
  4. Forecast through Apr 30 as counterfactual for the pulse periods.
  5. For each pulse period, compare actual sum vs. counterfactual sum and
     test significance against the 95% forecast CI.
"""

import os
import logging
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from prophet import Prophet

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "Enrollments by date.csv")
OUT_PNG   = os.path.join(BASE_DIR, "podcast_pulse_counterfactual.png")
OUT_CSV   = os.path.join(BASE_DIR, "podcast_pulse_results.csv")

# ── Period definitions ─────────────────────────────────────────────────────
TRAIN_START = "2025-05-01"
TRAIN_END   = "2026-03-23"   # end of BAU training window

VALIDATION = {
    "label": "BAU Validation",
    "start": "2026-03-24",
    "end":   "2026-03-31",
    "color": "#4C72B0",
}

TEST_PERIODS = [
    {
        "label":        "50% BAU (Spend Down)",
        "spend_label":  "$330,000 total · $110K/wk",
        "start":        "2026-04-01",
        "end":          "2026-04-21",
        "total_spend":  330_000,
        "color":        "#DD8452",
    },
    {
        "label":        "150% BAU (Spend Up)",
        "spend_label":  "$220,000 total · $220K/wk",
        "start":        "2026-04-22",
        "end":          "2026-04-30",
        "total_spend":  220_000,
        "color":        "#55A868",
    },
]

# ── 1. Load data & build daily series ─────────────────────────────────────
print("=" * 70)
print("PODCAST PULSE COUNTERFACTUAL ANALYSIS")
print("=" * 70)
print(f"\n[1] Loading data from: {DATA_FILE}")

df = pd.read_csv(DATA_FILE, parse_dates=["SPEND_DATE"])
print(f"    Rows: {len(df):,}")

# Pre-aggregated file — set date index directly
daily = (
    df.set_index("SPEND_DATE")["ENROLLMENTS"]
    .rename("enrollments")
    .sort_index()
    .asfreq("D")
)
# Forward-fill any isolated missing calendar days (e.g. reporting lags)
daily = daily.ffill()

DATA_END = daily.index.max()
print(f"    Date range: {daily.index.min().date()} → {DATA_END.date()}  ({len(daily)} days)")

# ── 2. Training series ─────────────────────────────────────────────────────
print(f"\n[2] Training window: {TRAIN_START} → {TRAIN_END}")
train = daily[TRAIN_START:TRAIN_END].copy()
print(f"    Training days: {len(train)}   |   "
      f"Mean daily enrollments: {train.mean():,.0f}   |   "
      f"Std: {train.std():,.0f}")

# ── 3. Fit Prophet ────────────────────────────────────────────────────────
print("\n[3] Fitting Prophet (trend + weekly + yearly seasonality) …")

# Prophet requires a DataFrame with columns ds (date) and y (value)
train_prophet = train.reset_index().rename(columns={"SPEND_DATE": "ds", "enrollments": "y"})

m = Prophet(
    changepoint_prior_scale=0.05,   # flexibility of trend changepoints
    seasonality_mode="additive",
    yearly_seasonality=True,         # captures spring/seasonal uptick
    weekly_seasonality=True,         # captures Mon-Sun pattern
    daily_seasonality=False,
    interval_width=0.95,             # 95% uncertainty intervals
)
m.fit(train_prophet)

# In-sample residuals on training data
train_insample = m.predict(train_prophet[["ds"]])
resid_vals  = train.values - train_insample["yhat"].values
rmse_train  = np.sqrt((resid_vals ** 2).mean())
mape_train  = (np.abs(resid_vals) / train.values).mean() * 100
print(f"    Training RMSE: {rmse_train:,.0f}   MAPE: {mape_train:.1f}%")

# ── 4. Forecast: validation week + full pulse window ──────────────────────
print("\n[4] Generating counterfactual forecast 3/24/2026 → 4/30/2026 …")
FORECAST_END = "2026-04-30"
n_steps      = (pd.Timestamp(FORECAST_END) - pd.Timestamp(TRAIN_END)).days

future    = m.make_future_dataframe(periods=n_steps, freq="D", include_history=False)
fc_raw    = m.predict(future)
fc_raw    = fc_raw.set_index("ds")

fc_mean   = fc_raw["yhat"].rename("cf_mean")
fc_lo     = fc_raw["yhat_lower"].rename("cf_lo")
fc_hi     = fc_raw["yhat_upper"].rename("cf_hi")

# ── 5. Validation: BAU hold-out week (3/24 – 3/31) ────────────────────────
print("\n[5] Validation on BAU hold-out week (3/24 – 3/31) …")
v_start  = pd.Timestamp(VALIDATION["start"])
v_end    = pd.Timestamp(VALIDATION["end"])
v_actual = daily[v_start:v_end]
v_cf     = fc_mean[v_start:v_end]
v_lo     = fc_lo[v_start:v_end]
v_hi     = fc_hi[v_start:v_end]

v_rmse = np.sqrt(((v_actual.values - v_cf.values) ** 2).mean())
v_mape = (np.abs(v_actual.values - v_cf.values) / v_actual.values).mean() * 100
v_bias = (v_actual.values - v_cf.values).mean()
v_days_inside_ci = ((v_actual.values >= v_lo.values) & (v_actual.values <= v_hi.values)).sum()

print(f"    Days:              {len(v_actual)}")
print(f"    Actual total:      {v_actual.sum():,.0f}")
print(f"    Forecast total:    {v_cf.sum():,.0f}  ({v_actual.sum() - v_cf.sum():+,.0f})")
print(f"    RMSE:              {v_rmse:,.0f}")
print(f"    MAPE:              {v_mape:.1f}%")
print(f"    Mean daily bias:   {v_bias:+,.0f}")
print(f"    Days inside 95%CI: {v_days_inside_ci}/{len(v_actual)}")

# ── 6. Per-period results (pulse windows only) ────────────────────────────
print("\n[6] Computing lift & statistical significance per pulse period …\n")
rows = []
for p in TEST_PERIODS:
    pstart   = pd.Timestamp(p["start"])
    pend     = pd.Timestamp(p["end"])
    avail_end = min(pend, DATA_END)
    has_data  = pstart <= DATA_END

    if has_data:
        act_series = daily[pstart:avail_end]
        act_total  = act_series.sum()
        act_days   = len(act_series)
        missing_days = (pend - avail_end).days
    else:
        act_series   = pd.Series(dtype=float)
        act_total    = np.nan
        act_days     = 0
        missing_days = (pend - pstart).days + 1

    # Counterfactual over the actual-data window (for lift calc) AND full period (for display)
    cf_s      = fc_mean[pstart:avail_end]    # aligns with actuals
    cf_lo_s   = fc_lo[pstart:avail_end]
    cf_hi_s   = fc_hi[pstart:avail_end]
    cf_full   = fc_mean[pstart:pend]         # full forecast window for display
    cf_lo_full = fc_lo[pstart:pend]
    cf_hi_full = fc_hi[pstart:pend]

    cf_total      = cf_s.sum()               # used for lift (aligned to actuals)
    cf_lo_sum     = cf_lo_s.sum()            # CI bounds aligned to actuals
    cf_hi_sum     = cf_hi_s.sum()
    cf_total_full = cf_full.sum()            # full-period totals for display
    cf_lo_full_sum = cf_lo_full.sum()
    cf_hi_full_sum = cf_hi_full.sum()
    cf_days_full  = len(cf_full)

    if has_data and len(cf_s) > 0:
        lift_abs = act_total - cf_total
        lift_pct = lift_abs / cf_total * 100

        # SE of sum (sum of per-day variances, independence assumption)
        half_widths = (cf_hi_s - cf_lo_s) / 2.0
        se_sum = np.sqrt((half_widths ** 2).sum()) / 1.96
        z_stat = lift_abs / se_sum if se_sum > 0 else np.nan
        p_val  = 2.0 * (1.0 - stats.norm.cdf(abs(z_stat))) if not np.isnan(z_stat) else np.nan
        sig    = "YES" if p_val < 0.05 else "no"

        # Is the actual outside the summed CI?
        outside_ci = act_total > cf_hi_sum or act_total < cf_lo_sum
    else:
        lift_abs = lift_pct = z_stat = p_val = np.nan
        sig      = "—"
        outside_ci = None

    note = ""
    if missing_days > 0 and has_data:
        note = f"{missing_days}d missing from end"
    elif not has_data:
        note = "no actuals in dataset"

    rows.append({
        "period":        p["label"],
        "spend":         p["spend_label"],
        "actual_days":   act_days,
        "actual_total":  act_total,
        "cf_total":      cf_total,
        "cf_total_full":  cf_total_full,
        "cf_lo_full_sum": cf_lo_full_sum,
        "cf_hi_full_sum": cf_hi_full_sum,
        "cf_days_full":   cf_days_full,
        "cf_lo_sum":     cf_lo_sum,
        "cf_hi_sum":     cf_hi_sum,
        "lift_abs":      lift_abs,
        "lift_pct":      lift_pct,
        "z_stat":        z_stat,
        "p_value":       p_val,
        "stat_sig":      sig,
        "outside_95ci":  outside_ci,
        "note":          note,
        "color":         p["color"],
        "total_spend":   p["total_spend"],
    })

# ── 7. Print results ───────────────────────────────────────────────────────
print("-" * 70)
print(f"{'Period':<28} {'Actual':>10} {'CF':>10} {'Lift Abs':>10} "
      f"{'Lift %':>8} {'p-val':>8} {'Sig':>5}")
print("-" * 70)
for r in rows:
    act_s  = f"{r['actual_total']:>10,.0f}" if not np.isnan(r["actual_total"]) else f"{'—':>10}"
    # Use full-period CF when no actuals (e.g. 150% BAU has no data yet)
    cf_disp = r["cf_total_full"] if r["cf_total"] == 0 and np.isnan(r["actual_total"]) else r["cf_total"]
    cf_s   = f"{cf_disp:>10,.0f}"            if not np.isnan(cf_disp)         else f"{'—':>10}"
    lab    = f"{r['lift_abs']:>+10,.0f}"     if not np.isnan(r["lift_abs"])   else f"{'—':>10}"
    lpct   = f"{r['lift_pct']:>+8.1f}%"     if not np.isnan(r["lift_pct"])   else f"{'—':>9}"
    pv     = f"{r['p_value']:>8.4f}"         if not np.isnan(r["p_value"])    else f"{'—':>8}"
    sig    = f"{r['stat_sig']:>5}"
    print(f"{r['period']:<28} {act_s} {cf_s} {lab} {lpct} {pv} {sig}")
    if r["note"]:
        print(f"  {'':28}  note: {r['note']}")
print("-" * 70)

# CPE on incremental enrollments
print(f"\n{'':3}{'Period':<28} {'Incr. Enrollments':>20} {'CPE (Incremental)':>20}")
print(f"  {'-'*68}")
for r in rows:
    if not np.isnan(r["lift_abs"]) and r["lift_abs"] > 0:
        cpe = r["total_spend"] / r["lift_abs"]
        print(f"  {r['period']:<28} {r['lift_abs']:>20,.0f} {f'${cpe:,.2f}':>20}")
    elif not np.isnan(r["lift_abs"]):
        print(f"  {r['period']:<28} {'(no positive lift)':>20} {'—':>20}")
    else:
        print(f"  {r['period']:<28} {'(no data)':>20} {'—':>20}")
print()

# ── 8. Save CSV ────────────────────────────────────────────────────────────
export_cols = [
    "period", "spend", "actual_days", "actual_total", "cf_total",
    "cf_lo_sum", "cf_hi_sum", "lift_abs", "lift_pct",
    "z_stat", "p_value", "stat_sig", "outside_95ci", "note",
]
res_df = pd.DataFrame(rows)[export_cols]
res_df.to_csv(OUT_CSV, index=False)
print(f"Results saved → {OUT_CSV}")

# ── 9. Plot ────────────────────────────────────────────────────────────────
print(f"Building chart …")

PLOT_START = "2025-10-01"   # show ~6 months of pre-period context
fig, axes = plt.subplots(
    2, 1,
    figsize=(18, 12),
    gridspec_kw={"height_ratios": [3, 1]},
    sharex=True,
)
fig.patch.set_facecolor("#F9F9F9")

# ── Panel 1: actual vs counterfactual ─────────────────────────────────────
ax = axes[0]
ax.set_facecolor("#F9F9F9")

ymax = daily[PLOT_START:].max() * 1.02

# Pre-period actuals (training region shown for context)
pre_plot = daily[PLOT_START:TRAIN_END]
ax.plot(pre_plot.index, pre_plot.values,
        color="#888888", lw=1.2, alpha=0.7, label="Actual (training)")

# Validation + test period actuals
act_plot = daily[pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1):DATA_END]
ax.plot(act_plot.index, act_plot.values,
        color="#1A1A2E", lw=2.0, label="Actual (validation + test)", zorder=4)

# Shade validation window
ax.axvspan(pd.Timestamp(VALIDATION["start"]), pd.Timestamp(VALIDATION["end"]),
           alpha=0.10, color=VALIDATION["color"], zorder=1)
ax.axvline(pd.Timestamp(VALIDATION["start"]), color=VALIDATION["color"],
           lw=1.3, linestyle=":", alpha=0.9, zorder=2)
ax.text(pd.Timestamp(VALIDATION["start"]) + pd.Timedelta(days=0.4), ymax * 0.04,
        "BAU\nValidation", fontsize=7.5, color=VALIDATION["color"],
        va="bottom", rotation=90, fontweight="bold")

# Counterfactual + CI
cf_plot_range = fc_mean[PLOT_START:]
ci_lo_range   = fc_lo[PLOT_START:]
ci_hi_range   = fc_hi[PLOT_START:]
ax.plot(cf_plot_range.index, cf_plot_range.values,
        color="#4C72B0", lw=1.8, linestyle="--",
        label="Counterfactual (Prophet)", zorder=3)
ax.fill_between(cf_plot_range.index, ci_lo_range, ci_hi_range,
                alpha=0.18, color="#4C72B0", label="95% CI")

# Training end vertical line
ax.axvline(pd.Timestamp(TRAIN_END), color="#888888", lw=1.2,
           linestyle="--", alpha=0.7, zorder=2)
ax.text(pd.Timestamp(TRAIN_END) - pd.Timedelta(days=2),
        ymax * 0.04,
        f"Train end\n3/23", fontsize=7.5, color="#888888", ha="right", va="bottom")

# Period shading + labels
for p, r in zip(TEST_PERIODS, rows):
    pstart = pd.Timestamp(p["start"])
    pend   = pd.Timestamp(p["end"])
    ax.axvspan(pstart, pend, alpha=0.08, color=p["color"], zorder=1)
    ax.axvline(pstart, color=p["color"], lw=1.3, linestyle=":", alpha=0.9, zorder=2)
    # Label at top of shaded band
    ax.text(pstart + pd.Timedelta(days=0.4), ymax * 0.98,
            p["label"], fontsize=8, color=p["color"],
            va="top", rotation=90, fontweight="bold")
    # Stat sig annotation
    if r["stat_sig"] not in ("—", None):
        mid  = pstart + (min(pend, DATA_END) - pstart) / 2
        sign = "▲" if (not np.isnan(r["lift_pct"]) and r["lift_pct"] > 0) else "▼"
        lbl  = (f"{sign}{abs(r['lift_pct']):.1f}%\n{r['stat_sig']}"
                if not np.isnan(r["lift_pct"]) else "")
        ax.text(mid, ymax * 0.82, lbl,
                fontsize=8.5, color=p["color"],
                ha="center", va="top", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7, ec=p["color"]))

# Validation metrics box
val_txt = (f"Validation (3/24–3/31)\n"
           f"RMSE: {v_rmse:,.0f}  MAPE: {v_mape:.1f}%\n"
           f"Bias: {v_bias:+,.0f}/day  CI coverage: {v_days_inside_ci}/{len(v_actual)}d")
ax.text(pd.Timestamp("2026-03-10"), ymax * 0.96, val_txt,
        fontsize=7.5, color="#4C72B0", va="top", ha="left",
        bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.85, ec="#4C72B0"))

ax.set_ylim(bottom=0, top=ymax * 1.06)
ax.set_ylabel("Daily Enrollments", fontsize=11)
ax.set_title(
    "Podcast Pulse Test — Actual vs Prophet Counterfactual (Overall Enrollments)\n"
    f"Training: {TRAIN_START} → {TRAIN_END}   |   "
    f"Model: Prophet (trend + weekly + yearly)   |   "
    f"Training MAPE: {mape_train:.1f}%",
    fontsize=12, pad=10,
)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(loc="upper left", fontsize=9, framealpha=0.85)
ax.grid(axis="y", alpha=0.25, linestyle="--")

# ── Panel 2: daily lift (actual − counterfactual) ──────────────────────────
ax2 = axes[1]
ax2.set_facecolor("#F9F9F9")

for p, r in zip(TEST_PERIODS, rows):
    pstart    = pd.Timestamp(p["start"])
    avail_end = min(pd.Timestamp(p["end"]), DATA_END)
    if pstart > DATA_END:
        continue
    act_seg = daily[pstart:avail_end]
    cf_seg  = fc_mean[pstart:avail_end]
    lift_d  = act_seg.values - cf_seg.values
    ax2.bar(act_seg.index, lift_d,
            color=[p["color"] if v >= 0 else "#CC4444" for v in lift_d],
            alpha=0.7, width=0.9, zorder=3)

ax2.axhline(0, color="#333333", lw=0.8)
ax2.set_ylabel("Daily Lift\n(Actual − CF)", fontsize=9)
ax2.set_xlabel("Date", fontsize=11)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+,.0f}"))
ax2.grid(axis="y", alpha=0.25, linestyle="--")

# Shade same windows in bottom panel
for p in TEST_PERIODS:
    ax2.axvspan(pd.Timestamp(p["start"]), pd.Timestamp(p["end"]),
                alpha=0.06, color=p["color"], zorder=1)

plt.tight_layout(h_pad=0.5)
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"Chart saved  → {OUT_PNG}")

# ── 10. Interpretation summary ────────────────────────────────────────────
print("\n" + "=" * 70)
print("VALIDATION SUMMARY (BAU hold-out: 3/24 – 3/31)")
print("=" * 70)
print(f"  RMSE:              {v_rmse:,.0f} enrollments/day")
print(f"  MAPE:              {v_mape:.1f}%")
print(f"  Mean daily bias:   {v_bias:+,.0f}  ({'over' if v_bias > 0 else 'under'}forecasting)")
print(f"  Days inside 95%CI: {v_days_inside_ci}/{len(v_actual)}")
print(f"  Actual total:      {v_actual.sum():,.0f}")
print(f"  Forecast total:    {v_cf.sum():,.0f}  (diff: {v_actual.sum()-v_cf.sum():+,.0f})")

print("\n" + "=" * 70)
print("INTERPRETATION — PULSE PERIODS")
print("=" * 70)
for r in rows:
    print(f"\n  {r['period']}  ({r['spend']})")
    if r["stat_sig"] == "—":
        print(f"    No actuals available — counterfactual forecast only.")
        print(f"    Projected counterfactual: {r['cf_total_full']:,.0f} enrollments "
              f"over {r['cf_days_full']} days  "
              f"[95% CI: {r['cf_lo_full_sum']:,.0f} – {r['cf_hi_full_sum']:,.0f}]")
    else:
        dir_lbl = "LIFT" if r["lift_pct"] > 0 else "DROP"
        print(f"    Actual:         {r['actual_total']:>12,.0f} enrollments ({r['actual_days']} days)")
        print(f"    Counterfactual: {r['cf_total']:>12,.0f} enrollments  [95% CI: {r['cf_lo_sum']:,.0f} – {r['cf_hi_sum']:,.0f}]")
        print(f"    {dir_lbl}:          {r['lift_abs']:>+12,.0f}  ({r['lift_pct']:+.1f}%)")
        print(f"    Z-statistic: {r['z_stat']:.2f}   p-value: {r['p_value']:.4f}   Stat sig (p<0.05): {r['stat_sig']}")
        print(f"    Actual outside 95% CI band: {r['outside_95ci']}")
        if r["note"]:
            print(f"    ⚠ Note: {r['note']}")

print("\n" + "=" * 70)
print("METHODOLOGICAL NOTES")
print("=" * 70)
print("""
  - Counterfactual is a Prophet model trained on May 2025 – Mar 23 2026.
    Prophet decomposes the series into a piecewise-linear trend, weekly
    seasonality, and yearly seasonality, then extrapolates each component
    forward. Uncertainty intervals reflect posterior uncertainty over trend
    changepoints. The model captures the spring enrollment uptick via
    yearly seasonality — unlike SARIMA, whose CI widens unboundedly.

  - Stat sig is tested by comparing the period-level actual enrollment sum to
    the summed 95% CI of the daily forecasts (independence-of-days assumption).
    This is conservative — correlated forecast errors make the true CI wider.

  - If both the spend-down and spend-up periods show enrollment above the
    counterfactual, potential explanations include:
      (a) Natural spring seasonality not fully captured in the training window
      (b) Other media channels ramped up in April simultaneously
      (c) Podcast spend is not a primary marginal driver of total enrollments
""")

# ── 11. Prophet components chart ─────────────────────────────────────────
print("Building Prophet components chart …")
OUT_COMPONENTS = os.path.join(BASE_DIR, "podcast_pulse_prophet_components.png")

# Predict over the full observed range for component decomposition
full_range = pd.DataFrame({"ds": pd.date_range(TRAIN_START, FORECAST_END, freq="D")})
components = m.predict(full_range)

fig2, axes2 = plt.subplots(3, 1, figsize=(16, 10))
fig2.patch.set_facecolor("#F9F9F9")
fig2.suptitle("Prophet Model Components — Enrollment Forecast Decomposition",
              fontsize=13, y=1.01)

# Trend
axes2[0].plot(components["ds"], components["trend"], color="#1A1A2E", lw=1.8)
axes2[0].set_title("Trend (piecewise linear)", fontsize=10)
axes2[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
axes2[0].grid(alpha=0.25, linestyle="--")
axes2[0].axvline(pd.Timestamp(TRAIN_END), color="#888888", lw=1, linestyle="--", alpha=0.6)

# Weekly seasonality
axes2[1].plot(components["ds"], components["weekly"], color="#4C72B0", lw=1.5)
axes2[1].set_title("Weekly Seasonality (day-of-week effect, enrollments)", fontsize=10)
axes2[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+,.0f}"))
axes2[1].axhline(0, color="#333", lw=0.8)
axes2[1].grid(alpha=0.25, linestyle="--")

# Yearly seasonality
axes2[2].plot(components["ds"], components["yearly"], color="#55A868", lw=1.5)
axes2[2].set_title("Yearly Seasonality (time-of-year effect, enrollments)", fontsize=10)
axes2[2].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+,.0f}"))
axes2[2].axhline(0, color="#333", lw=0.8)
axes2[2].grid(alpha=0.25, linestyle="--")

for ax_c in axes2:
    ax_c.set_facecolor("#F9F9F9")
    for p in TEST_PERIODS:
        ax_c.axvspan(pd.Timestamp(p["start"]), pd.Timestamp(p["end"]),
                     alpha=0.07, color=p["color"])

plt.tight_layout()
plt.savefig(OUT_COMPONENTS, dpi=150, bbox_inches="tight")
print(f"Components chart saved → {OUT_COMPONENTS}")

print(f"\nDone. Outputs:\n  Chart      → {OUT_PNG}\n  Components → {OUT_COMPONENTS}\n  Table      → {OUT_CSV}\n")
