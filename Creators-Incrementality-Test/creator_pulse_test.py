#!/usr/bin/env python3
"""
Creator Incrementality Pulse Test
MDF-XXXX

Pulse test design:
  Phase 1 – Pre-period    : baseline creator spend (establishes enrollment baseline)
  Phase 2 – Off period    : creator spend paused for 2–3 weeks (measures enrollment drop)
  Phase 3 – Ramp period   : creator budget increased by $2–3M (measures enrollment lift)

Primary metric: enrollments (daily, from May 2025–2026 Data by DMA.csv)

Analysis outputs:
  1. Daily / weekly enrollment trends with phase markers
  2. Interrupted time-series (ITS) pre/off/ramp comparison
  3. Day-of-week adjusted lift estimates
  4. Power analysis — what lift can $2–3M in creator budget detect?
  5. Estimated incremental CPE from the pause window
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats as scipy_stats

# ─── CONFIG ─────────────────────────────────────────────────────────────────

DATA_FILE = os.path.join(os.path.dirname(__file__), "May 2025- 2026 Data by DMA.csv")

# ── Phase date boundaries ─────────────────────────────────────────────────
# Update OFF/RAMP dates once the test is scheduled.
PRE_PERIOD_START  = "2026-01-05"   # first full week of 2026 (skip partial Jan 1-4 week)
PRE_PERIOD_END    = "2026-04-19"   # last date with available data
OFF_PERIOD_START  = "2026-05-12"   # PLACEHOLDER — first day creators are off (~3 weeks)
OFF_PERIOD_END    = "2026-06-01"   # PLACEHOLDER — last day of off period
RAMP_PERIOD_START = "2026-06-02"   # PLACEHOLDER — first day of budget ramp-up
RAMP_PERIOD_END   = "2026-06-30"   # PLACEHOLDER — end of ramp measurement window

# ── Budget & cost parameters ──────────────────────────────────────────────
BUDGET_INCREMENT_LOW_M  = 2.0   # $M – lower bound of ramp budget
BUDGET_INCREMENT_HIGH_M = 3.0   # $M – upper bound of ramp budget
ICPE_BASELINE           = 100   # $ – incremental cost per enrollment (creator channel)

# ── Power analysis assumptions (aligned with Creator Spend Power Calculator) ─
# Statistical design: two-sample t-test on daily means (off period vs ramp period).
# The off period is the counterfactual — enrollment rate with $0 creator spend.
# The ramp is compared against that baseline, so ALL ramp-period lift is attributable
# to creator spend (no embedded baseline contribution to worry about).
ALPHA                   = 0.10   # significance level (10%, per tool)
POWER_TARGET            = 0.70   # target power (70%, per tool)
MDE                     = 0.08   # minimum detectable effect (8% lift in enrollments)

# No-spend daily baseline: expected daily enrollments during the off period ($0 creators).
# This is lower than the observed pre-period mean because the pre-period includes
# ~$700K/month of creator spend already driving ~2–3% of observed enrollments.
# Update this once the off period runs — use actual off-period daily mean.
NO_SPEND_DAILY_BASELINE = 19_500   # enrollments/day (from power calculator tool)
DAILY_CV_EMPIRICAL      = 0.11     # empirical CV (σ/μ) on daily enrollment counts

# ── DMAs to include ───────────────────────────────────────────────────────
# Set to None to use ALL non-excluded DMAs in the CSV.
# Provide a list of DMA codes to restrict to a specific subset.
CREATOR_DMA_SUBSET = None   # e.g. [501, 524, 602, 618, 623]

# ── Exclusions ────────────────────────────────────────────────────────────
# Creator test is national — no DMA exclusions applied.
EXCLUDED_DMA_CODES: set = set()

# ── Output files ──────────────────────────────────────────────────────────
OUT_TREND_PLOT  = os.path.join(os.path.dirname(__file__), "creator_pulse_trend.png")
OUT_POWER_PLOT  = os.path.join(os.path.dirname(__file__), "creator_pulse_power.png")
OUT_SUMMARY_CSV = os.path.join(os.path.dirname(__file__), "creator_pulse_summary.csv")

PHASE_COLORS = {
    "Pre-period":  "#2196F3",   # blue
    "Off period":  "#F44336",   # red
    "Ramp period": "#4CAF50",   # green
}

# ─── LOAD DATA ───────────────────────────────────────────────────────────────

def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df["date"] = pd.to_datetime(df["date"])
    df["enrollments"] = pd.to_numeric(df["enrollments"], errors="coerce").fillna(0)
    return df


def filter_dmas(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only eligible creator DMAs."""
    df = df[~df["geo"].isin(EXCLUDED_DMA_CODES)].copy()
    if CREATOR_DMA_SUBSET is not None:
        df = df[df["geo"].isin(CREATOR_DMA_SUBSET)].copy()
    return df


# ─── PHASE ASSIGNMENT ────────────────────────────────────────────────────────

def assign_phase(date: pd.Timestamp) -> str | None:
    pre_start  = pd.Timestamp(PRE_PERIOD_START)
    pre_end    = pd.Timestamp(PRE_PERIOD_END)
    off_start  = pd.Timestamp(OFF_PERIOD_START)
    off_end    = pd.Timestamp(OFF_PERIOD_END)
    ramp_start = pd.Timestamp(RAMP_PERIOD_START)
    ramp_end   = pd.Timestamp(RAMP_PERIOD_END)

    if pre_start <= date <= pre_end:
        return "Pre-period"
    if off_start <= date <= off_end:
        return "Off period"
    if ramp_start <= date <= ramp_end:
        return "Ramp period"
    return None


def build_daily_national(df: pd.DataFrame) -> pd.DataFrame:
    daily = (
        df.groupby("date")
        .agg(
            enrollments=("enrollments", "sum"),
            active_dmas=("geo", "nunique"),
        )
        .reset_index()
        .sort_values("date")
    )
    daily["phase"] = daily["date"].map(assign_phase)
    daily["dow"]   = daily["date"].dt.dayofweek   # 0=Mon … 6=Sun
    daily["week"]  = daily["date"].dt.to_period("W").apply(lambda p: p.start_time)
    return daily


# ─── PHASE SUMMARY ───────────────────────────────────────────────────────────

def compute_phase_stats(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for phase in ["Pre-period", "Off period", "Ramp period"]:
        sub = daily[daily["phase"] == phase]
        if sub.empty:
            continue
        n_days  = len(sub)
        total   = sub["enrollments"].sum()
        avg_day = sub["enrollments"].mean()
        std_day = sub["enrollments"].std()
        rows.append({
            "Phase":              phase,
            "Days":               n_days,
            "Total Enrollments":  total,
            "Avg / Day":          avg_day,
            "Std / Day":          std_day,
            "CV":                 std_day / avg_day if avg_day > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def dow_adjusted_baseline(daily: pd.DataFrame) -> dict[int, float]:
    """Day-of-week average enrollments from the pre-period."""
    pre = daily[daily["phase"] == "Pre-period"]
    return pre.groupby("dow")["enrollments"].mean().to_dict()


def compute_lift(daily: pd.DataFrame, dow_baseline: dict) -> pd.DataFrame:
    """
    For each day in off/ramp periods, compute:
      - expected enrollments (day-of-week adjusted pre-period mean)
      - absolute lift = actual − expected
      - relative lift = (actual − expected) / expected
    """
    target = daily[daily["phase"].isin(["Off period", "Ramp period"])].copy()
    target["expected"]     = target["dow"].map(dow_baseline)
    target["abs_lift"]     = target["enrollments"] - target["expected"]
    target["rel_lift_pct"] = (target["abs_lift"] / target["expected"]) * 100
    return target


# ─── POWER ANALYSIS ──────────────────────────────────────────────────────────

def compute_pre_noise(daily: pd.DataFrame) -> dict:
    """
    Estimate pre-period noise from weekly enrollment series.
    Returns:
      sigma_rel   – weekly coefficient of variation (std / mean)
      mu_weekly   – mean weekly enrollments
      n_weeks     – number of pre-period weeks
      autocorr_1  – lag-1 autocorrelation of weekly enrollments
    """
    pre = daily[daily["phase"] == "Pre-period"].copy()
    weekly = pre.groupby("week")["enrollments"].sum().sort_index()
    mu     = weekly.mean()
    sigma  = weekly.std()
    return {
        "sigma_rel":    sigma / mu if mu > 0 else np.nan,
        "mu_weekly":    mu,
        "n_weeks":      len(weekly),
        "autocorr_1":   weekly.autocorr(lag=1) if len(weekly) > 2 else 0.0,
        "weekly_series": weekly,
    }


def _ac_inflate(sigma_rel: float, autocorr: float) -> float:
    """Newey-West lag-1 variance inflation: σ_eff = σ × √(1 + 2ρ₁)."""
    rho = max(autocorr, 0.0)
    return sigma_rel * np.sqrt(1 + 2 * rho)


def weeks_needed(sigma_rel: float, lift: float, k: float, autocorr: float = 0.0) -> int:
    sigma_eff = _ac_inflate(sigma_rel, autocorr)
    return int(np.ceil(k * (sigma_eff / lift) ** 2))


def mde_at_weeks(sigma_rel: float, t_weeks: int, k: float, autocorr: float = 0.0) -> float:
    """Minimum detectable lift (%) after t_weeks, with AC correction."""
    sigma_eff = _ac_inflate(sigma_rel, autocorr)
    return np.sqrt(k / t_weeks) * sigma_eff * 100


def print_phase_report(phase_stats: pd.DataFrame, lift_df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("CREATOR PULSE TEST — PHASE ENROLLMENT SUMMARY")
    print("=" * 80)
    print(f"\n  {'Phase':<15}  {'Days':>6}  {'Total Enroll':>15}  {'Avg/Day':>12}  {'Std/Day':>10}  {'CV':>7}")
    print(f"  {'-'*15}  {'-'*6}  {'-'*15}  {'-'*12}  {'-'*10}  {'-'*7}")
    for _, row in phase_stats.iterrows():
        print(f"  {row['Phase']:<15}  {int(row['Days']):>6}  {row['Total Enrollments']:>15,.0f}  "
              f"{row['Avg / Day']:>12,.1f}  {row['Std / Day']:>10,.1f}  {row['CV']:>6.3f}")

    pre  = phase_stats[phase_stats["Phase"] == "Pre-period"]
    off  = phase_stats[phase_stats["Phase"] == "Off period"]
    ramp = phase_stats[phase_stats["Phase"] == "Ramp period"]

    if not pre.empty:
        pre_avg = pre["Avg / Day"].values[0]
        if not off.empty:
            off_avg = off["Avg / Day"].values[0]
            off_pct = (off_avg - pre_avg) / pre_avg * 100
            off_days = int(off["Days"].values[0])
            total_off_loss = (off_avg - pre_avg) * off_days
            print(f"\n  Off period vs Pre-period:   {off_pct:+.2f}% per day  "
                  f"({total_off_loss:+,.0f} cumulative incremental enrollments over {off_days} days)")

        if not ramp.empty:
            ramp_avg = ramp["Avg / Day"].values[0]
            ramp_pct = (ramp_avg - pre_avg) / pre_avg * 100
            ramp_days = int(ramp["Days"].values[0])
            total_ramp_lift = (ramp_avg - pre_avg) * ramp_days
            print(f"  Ramp period vs Pre-period:  {ramp_pct:+.2f}% per day  "
                  f"({total_ramp_lift:+,.0f} cumulative incremental enrollments over {ramp_days} days)")

    # DOW-adjusted lift during off period
    if not lift_df.empty:
        off_lift = lift_df[lift_df["phase"] == "Off period"]
        ramp_lift = lift_df[lift_df["phase"] == "Ramp period"]
        print(f"\n  DOW-adjusted lift estimates:")
        if not off_lift.empty:
            mean_off = off_lift["rel_lift_pct"].mean()
            total_off = off_lift["abs_lift"].sum()
            print(f"    Off period:   avg daily lift = {mean_off:+.2f}%  "
                  f"(cumulative = {total_off:+,.0f} enrollments)")
        if not ramp_lift.empty:
            mean_ramp = ramp_lift["rel_lift_pct"].mean()
            total_ramp = ramp_lift["abs_lift"].sum()
            print(f"    Ramp period:  avg daily lift = {mean_ramp:+.2f}%  "
                  f"(cumulative = {total_ramp:+,.0f} enrollments)")


def _days_needed_twosamle(cv: float, mde: float, z_alpha: float, z_beta: float) -> int:
    """
    Days needed per arm for a two-sample t-test on daily means.
    n = 2 × (z_α + z_β)² × (CV / MDE)²
    The factor of 2 accounts for estimating both the off-period and ramp-period means
    independently (each with n days), giving SE = σ√(2/n) for the difference.
    """
    k = (z_alpha + z_beta) ** 2
    return int(np.ceil(2 * k * (cv / mde) ** 2))


def _mde_daily(cv: float, n_days: int, z_alpha: float, z_beta: float) -> float:
    """MDE (%) achievable in n_days per arm at given α and power."""
    k = (z_alpha + z_beta) ** 2
    return np.sqrt(2 * k / n_days) * cv * 100


def _power_daily(cv: float, mde: float, n_days: int, z_alpha: float) -> float:
    """Achieved power for a given MDE and n_days per arm."""
    se = cv * np.sqrt(2 / n_days)
    z  = mde / se - z_alpha
    return scipy_stats.norm.cdf(z) * 100


def print_power_report(noise: dict, icpe: float = ICPE_BASELINE) -> None:
    """
    Two-sample t-test on daily means: off-period days vs ramp-period days.

    Test comparison:
      Control arm  = off-period daily enrollment mean  ($0 creator spend)
      Treatment arm = ramp-period daily enrollment mean ($2–3M creator spend)

    Why two-sample?  The off period gives a clean $0-spend counterfactual.
    Every enrollment above that baseline during the ramp is attributable to
    creators, so the full ramp budget ($2–3M) is the incremental spend — no
    need to subtract the pre-period's embedded $700K/month contribution.
    """
    z_alpha = scipy_stats.norm.ppf(1 - ALPHA / 2)   # 1.645 at α=10%
    z_beta  = scipy_stats.norm.ppf(POWER_TARGET)      # 0.524 at 70% power

    mu    = NO_SPEND_DAILY_BASELINE
    cv    = DAILY_CV_EMPIRICAL
    sigma = cv * mu

    # Also show empirical CV from pre-period data (for reference)
    mu_obs = noise["mu_weekly"] / 7
    cv_obs = noise["sigma_rel"]

    print("\n" + "=" * 105)
    print(f"POWER ANALYSIS  —  Two-sample t-test on daily means (off period vs ramp period)")
    print(f"  α={ALPHA:.0%}  |  Target power={POWER_TARGET:.0%}  |  iCPE=${icpe:,.0f}/enrollment")
    print("=" * 105)
    print(f"\n  Baseline (no-spend daily μ):          {mu:>10,.0f}  enrollments/day")
    print(f"  Daily CV (empirical, σ/μ):            {cv:>10.1%}")
    print(f"  Daily σ:                              {sigma:>10,.0f}  enrollments/day")
    print(f"\n  [From observed 2026 pre-period data]")
    print(f"  Observed daily μ (pre, ~{noise['n_weeks']}wks):     {mu_obs:>10,.0f}  enrollments/day")
    print(f"  Observed daily CV (pre):              {cv_obs:>10.1%}  (pre-period includes creator spend)")

    print(f"\n  {'Lift':>5}  {'Signal/day':>11}  {'Days needed':>12}  "
          f"{'Incr. Enrollments':>20}  {'Budget @ $'+str(int(icpe)):>16}  {'Powered?':>9}")
    print(f"  {'-----':>5}  {'-'*11}  {'-'*12}  {'-'*20}  {'-'*16}  {'-'*9}")

    lift_range = [0.02, 0.03, 0.05, 0.07, 0.08, 0.10, 0.12, 0.15, 0.20]
    for lift in lift_range:
        n          = _days_needed_twosamle(cv, lift, z_alpha, z_beta)
        signal_day = mu * lift
        total_incr = signal_day * n
        budget_m   = total_incr * icpe / 1_000_000
        powered    = "✓ YES" if budget_m <= BUDGET_INCREMENT_HIGH_M else "✗ OVER"
        marker     = "  ◄ target MDE" if lift == MDE else ""
        print(f"  {lift*100:>4.0f}%  {signal_day:>11,.0f}  {n:>12}  "
              f"{total_incr:>20,.0f}  ${budget_m:>14.2f}M  {powered:>9}{marker}")

    print(f"\n  ── Budget-constraint reverse analysis  ($2M–$3M ramp, iCPE=${icpe:,.0f}) ──")
    print(f"  {'Budget':>8}  {'Duration':>10}  {'Implied lift':>14}  "
          f"{'Power':>7}  {'MDE at duration':>17}  {'Enough?':>8}")
    print(f"  {'-'*8}  {'-'*10}  {'-'*14}  {'-'*7}  {'-'*17}  {'-'*8}")

    for budget_m in [BUDGET_INCREMENT_LOW_M, BUDGET_INCREMENT_HIGH_M]:
        implied_incr = (budget_m * 1_000_000) / icpe
        for t_days in [14, 21, 28]:
            implied_lift  = (implied_incr / t_days) / mu
            pwr           = _power_daily(cv, implied_lift, t_days, z_alpha)
            mde_pct       = _mde_daily(cv, t_days, z_alpha, z_beta)
            enough        = "✓" if pwr >= POWER_TARGET * 100 else "✗"
            print(f"  ${budget_m:.0f}M      {t_days:>8}d  {implied_lift*100:>13.2f}%  "
                  f"{pwr:>6.1f}%  {mde_pct:>16.2f}%  {enough:>8}")
        print()

    print(f"  NOTE: Budget = incr. enrollments × iCPE  =  MDE × μ × days × ${icpe}")
    print(f"        The $2.9M figure you saw = same inputs but iCPE=$100 → "
          f"8% × {mu:,} × 18d × $100 = ${0.08*mu*18*100/1e6:.2f}M")


# ─── VISUALIZATIONS ──────────────────────────────────────────────────────────

def plot_enrollment_trend(daily: pd.DataFrame, phase_stats: pd.DataFrame,
                          lift_df: pd.DataFrame, output_path: str) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(18, 12), height_ratios=[2, 1])
    fig.patch.set_facecolor("#F8F9FA")

    phase_order = ["Pre-period", "Off period", "Ramp period"]
    phase_bounds = {
        "Pre-period":  (PRE_PERIOD_START,  PRE_PERIOD_END),
        "Off period":  (OFF_PERIOD_START,  OFF_PERIOD_END),
        "Ramp period": (RAMP_PERIOD_START, RAMP_PERIOD_END),
    }

    # ── Panel 1: Daily enrollment trend ──────────────────────────────────────
    ax1 = axes[0]
    ax1.set_facecolor("#FFFFFF")

    in_scope = daily[daily["phase"].notna()].copy()
    out_scope = daily[daily["phase"].isna()].copy()

    # Grey out-of-scope data
    if not out_scope.empty:
        ax1.plot(out_scope["date"], out_scope["enrollments"] / 1_000,
                 color="#CCCCCC", linewidth=1.0, alpha=0.6, zorder=1)

    # Phase-coloured enrollment line
    for phase in phase_order:
        sub = daily[daily["phase"] == phase]
        if sub.empty:
            continue
        color = PHASE_COLORS[phase]
        ax1.plot(sub["date"], sub["enrollments"] / 1_000,
                 color=color, linewidth=2.0, label=phase, zorder=3)
        ax1.fill_between(sub["date"], sub["enrollments"] / 1_000,
                         alpha=0.10, color=color, zorder=2)

        # Phase avg line
        avg = sub["enrollments"].mean() / 1_000
        ax1.hlines(avg, sub["date"].min(), sub["date"].max(),
                   color=color, linewidth=1.5, linestyle="--", alpha=0.7, zorder=4)

    # Phase boundary shading
    for phase, (start, end) in phase_bounds.items():
        color = PHASE_COLORS[phase]
        ax1.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.04, color=color)
        ax1.axvline(pd.Timestamp(start), color=color, linewidth=1.2,
                    linestyle=":", alpha=0.6)

    # Annotation: phase labels at top
    for phase, (start, end) in phase_bounds.items():
        mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
        ax1.text(mid, ax1.get_ylim()[1] if ax1.get_ylim()[1] != 0 else 1,
                 phase, ha="center", va="bottom", fontsize=9,
                 color=PHASE_COLORS[phase], fontweight="bold",
                 transform=ax1.get_xaxis_transform())

    ax1.set_title("Creator Pulse Test — Daily Enrollment Trend by Phase",
                  fontsize=14, fontweight="bold", pad=14)
    ax1.set_ylabel("Daily Enrollments (K)", fontsize=11)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}K"))
    ax1.legend(fontsize=10, framealpha=0.95, edgecolor="#CCCCCC", loc="upper left")
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.tick_params(axis="x", labelsize=9, rotation=15)

    # ── Panel 2: DOW-adjusted daily lift during off/ramp ─────────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#FFFFFF")
    ax2.axhline(0, color="#888888", linewidth=1.0, linestyle="--")

    if not lift_df.empty:
        for phase in ["Off period", "Ramp period"]:
            sub = lift_df[lift_df["phase"] == phase]
            if sub.empty:
                continue
            color = PHASE_COLORS[phase]
            ax2.bar(sub["date"], sub["rel_lift_pct"],
                    color=color, alpha=0.7, label=f"{phase} (DOW-adj. lift)",
                    width=0.8, edgecolor="none")

    ax2.set_title("Day-of-Week Adjusted Lift vs Pre-Period Baseline",
                  fontsize=11, fontweight="bold", pad=10)
    ax2.set_ylabel("Enrollment Lift (%)", fontsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
    ax2.legend(fontsize=9.5, framealpha=0.95, edgecolor="#CCCCCC")
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.tick_params(axis="x", labelsize=9, rotation=15)

    fig.suptitle(
        "Creator Incrementality Pulse Test  │  "
        f"Off: {OFF_PERIOD_START} → {OFF_PERIOD_END}  │  "
        f"Ramp: {RAMP_PERIOD_START} → {RAMP_PERIOD_END}  │  "
        f"Budget ramp: ${BUDGET_INCREMENT_LOW_M:.0f}M–${BUDGET_INCREMENT_HIGH_M:.0f}M",
        fontsize=11, fontweight="bold", color="#1A237E", y=1.01,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Enrollment trend chart saved to: {output_path}")


def plot_power_analysis(output_path: str, icpe: float = ICPE_BASELINE) -> None:
    z_alpha = scipy_stats.norm.ppf(1 - ALPHA / 2)
    z_beta  = scipy_stats.norm.ppf(POWER_TARGET)

    mu  = NO_SPEND_DAILY_BASELINE
    cv  = DAILY_CV_EMPIRICAL

    lift_pct_range = np.linspace(1, 20, 400)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 7))
    fig.patch.set_facecolor("#F8F9FA")

    # ── Left: Days needed vs lift ─────────────────────────────────────────────
    ax1.set_facecolor("#FFFFFF")
    d_vals = [_days_needed_twosamle(cv, l / 100, z_alpha, z_beta) for l in lift_pct_range]
    ax1.plot(lift_pct_range, d_vals, color="#2196F3", linewidth=2.5, label="Days needed")

    for days, style, lbl in [(14, "--", "14d off/ramp"), (21, "-.", "21d off/ramp")]:
        ax1.axhline(days, color="#F44336", linewidth=1.4, linestyle=style,
                    alpha=0.8, label=lbl)

    # Mark target MDE
    ax1.axvline(MDE * 100, color="#9C27B0", linewidth=1.4, linestyle=":",
                alpha=0.8, label=f"Target MDE ({MDE*100:.0f}%)")

    ax1.set_title(f"Days Needed to Detect Lift\n(α={ALPHA:.0%}, {POWER_TARGET:.0%} power  |  two-sample daily t-test)",
                  fontsize=12, fontweight="bold", pad=10)
    ax1.set_xlabel("Assumed Lift in Enrollments (%)", fontsize=10)
    ax1.set_ylabel("Days per arm (off period = ramp period)", fontsize=10)
    ax1.set_xlim(1, 20)
    ax1.set_ylim(0, 60)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax1.legend(fontsize=9.5, framealpha=0.95, edgecolor="#CCCCCC")
    ax1.spines[["top", "right"]].set_visible(False)

    for lift in [5, 8, 10, 12, 15, 20]:
        d = _days_needed_twosamle(cv, lift / 100, z_alpha, z_beta)
        if d <= 55:
            ax1.annotate(f"{d}d", xy=(lift, d), xytext=(lift + 0.4, d + 1),
                         fontsize=7.5, color="#2196F3", fontweight="bold")

    # ── Right: Budget required vs lift ($2M and $3M lines) ───────────────────
    ax2.set_facecolor("#FFFFFF")
    budgets = []
    for lift in lift_pct_range:
        d      = _days_needed_twosamle(cv, lift / 100, z_alpha, z_beta)
        budget = mu * (lift / 100) * d * icpe
        budgets.append(budget / 1_000_000)
    ax2.plot(lift_pct_range, budgets, color="#2196F3", linewidth=2.5, label="Budget needed")

    for budget_m, color, lbl in [
        (BUDGET_INCREMENT_LOW_M,  "#FF9800", f"${BUDGET_INCREMENT_LOW_M:.0f}M ramp"),
        (BUDGET_INCREMENT_HIGH_M, "#4CAF50", f"${BUDGET_INCREMENT_HIGH_M:.0f}M ramp"),
    ]:
        ax2.axhline(budget_m, color=color, linewidth=2.0, linestyle="--", label=lbl)
        ax2.text(16.5, budget_m + 0.08, lbl, fontsize=9, color=color, fontweight="bold")

    ax2.set_title(f"Budget Required vs Assumed Lift\n(iCPE=${icpe:,}/enrollment, {POWER_TARGET:.0%} power)",
                  fontsize=12, fontweight="bold", pad=10)
    ax2.set_xlabel("Assumed Lift in Enrollments (%)", fontsize=10)
    ax2.set_ylabel("Required Budget ($M)", fontsize=10)
    ax2.set_xlim(1, 20)
    ax2.set_ylim(0)
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    ax2.legend(fontsize=9.5, framealpha=0.95, edgecolor="#CCCCCC")
    ax2.spines[["top", "right"]].set_visible(False)

    fig.text(0.5, -0.02,
             f"μ={mu:,} enrolls/day (no-spend baseline)  |  CV={cv:.0%}  |  "
             f"α={ALPHA:.0%}  |  power={POWER_TARGET:.0%}  |  iCPE=${icpe}",
             ha="center", fontsize=9, color="#555555", style="italic")

    fig.suptitle(
        "Creator Pulse Test — Power Analysis\n"
        "Two-sample t-test: off-period days vs ramp-period days",
        fontsize=12, fontweight="bold", color="#1A237E", y=1.03,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Power analysis chart saved to: {output_path}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading data from: {DATA_FILE}")
    raw_df = load_data(DATA_FILE)
    df     = filter_dmas(raw_df)
    n_dmas = df["geo"].nunique()
    date_min, date_max = df["date"].min().date(), df["date"].max().date()
    print(f"  {n_dmas} eligible DMAs  |  Date range: {date_min} → {date_max}")

    # ── Build daily national series ──────────────────────────────────────────
    daily = build_daily_national(df)
    in_scope_days = daily["phase"].notna().sum()
    print(f"  {in_scope_days} days within defined test phases\n")

    # ── Phase stats ──────────────────────────────────────────────────────────
    phase_stats = compute_phase_stats(daily)

    # ── DOW-adjusted lift ────────────────────────────────────────────────────
    dow_baseline = dow_adjusted_baseline(daily)
    lift_df      = compute_lift(daily, dow_baseline)

    print_phase_report(phase_stats, lift_df)

    # ── Pre-period noise ─────────────────────────────────────────────────────
    noise = compute_pre_noise(daily)
    print(f"\n  Pre-period: {noise['n_weeks']} weeks  |  "
          f"Avg weekly enrollments: {noise['mu_weekly']:,.0f}  |  "
          f"σ (rel): {noise['sigma_rel']*100:.2f}%  |  "
          f"Lag-1 AC: {noise['autocorr_1']:.3f}")

    # ── Power report ─────────────────────────────────────────────────────────
    print_power_report(noise)

    # ── Visualizations ───────────────────────────────────────────────────────
    plot_enrollment_trend(daily, phase_stats, lift_df, OUT_TREND_PLOT)
    plot_power_analysis(OUT_POWER_PLOT)

    # ── Export phase summary ─────────────────────────────────────────────────
    summary = phase_stats.copy()
    summary["Pre-period start"]  = PRE_PERIOD_START
    summary["Pre-period end"]    = PRE_PERIOD_END
    summary["Off-period start"]  = OFF_PERIOD_START
    summary["Off-period end"]    = OFF_PERIOD_END
    summary["Ramp-period start"] = RAMP_PERIOD_START
    summary["Ramp-period end"]   = RAMP_PERIOD_END
    summary["Budget ramp ($M)"]  = f"{BUDGET_INCREMENT_LOW_M}–{BUDGET_INCREMENT_HIGH_M}"
    summary["iCPE ($)"]          = ICPE_BASELINE
    summary["Eligible DMAs"]     = n_dmas
    summary.to_csv(OUT_SUMMARY_CSV, index=False)
    print(f"Phase summary saved to: {OUT_SUMMARY_CSV}")

    # ── Quick sanity: how much data falls in each phase ──────────────────────
    print("\n" + "=" * 50)
    print("DATA COVERAGE CHECK")
    print("=" * 50)
    for phase in ["Pre-period", "Off period", "Ramp period"]:
        sub = daily[daily["phase"] == phase]
        if sub.empty:
            print(f"  {phase:<15}  *** NO DATA — check date bounds ***")
        else:
            print(f"  {phase:<15}  {len(sub):>3} days  "
                  f"{sub['date'].min().date()} → {sub['date'].max().date()}")
    print()
    print("NOTE: If Off period or Ramp period show no data, update")
    print("      PRE_PERIOD_END / OFF_PERIOD_START / RAMP_PERIOD_START in CONFIG.")


if __name__ == "__main__":
    main()
