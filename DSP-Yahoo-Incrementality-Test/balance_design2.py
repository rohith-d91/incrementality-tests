#!/usr/bin/env python3
"""
Design 2 — 3-Cell Geo Test DMA Balancing
MDF-1629 (companion to the Yahoo / Scope3 Design 1 test)

Same cell structure:
  Cell 1 – Yahoo Test
  Cell 2 – DSP (Scope3) Test
  Cell 3 – Control Holdout

Key differences vs. Design 1:
  • Excludes the 30 DMAs already used in Design 1
  • Targets smaller / mid-tier DMAs (naturally next tier down after top-30 taken)
  • Power target: 70% at $300K / 3 weeks  (iCPE = $400)
  • Outputs prefixed with design2_
"""

import pandas as pd
import numpy as np
import random
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

# ─── CONFIG ─────────────────────────────────────────────────────────────────

BASE_DIR        = os.path.dirname(__file__)
DATA_FILE       = os.path.join(BASE_DIR, "May 2025- 2026 Data by DMA.csv")
SPEND_FILE      = os.path.join(BASE_DIR, "dma_paid_spend.csv")
OUTPUT_FILE     = os.path.join(BASE_DIR, "design2_dma_group_assignments.csv")
PLOT_FILE       = os.path.join(BASE_DIR, "design2_dma_group_balance.png")
POWER_PLOT_FILE = os.path.join(BASE_DIR, "design2_power_analysis.png")

N_PER_CELL   = 10
N_CELLS      = 3
RANDOM_SEED  = 42
ICPE         = 400          # incremental cost per enrollment ($)

ENROLL_WEIGHT = 0.5
SPEND_WEIGHT  = 0.5
TREND_WEIGHT  = 0.3

# Power design target for Design 2
POWER_TARGET   = 0.70       # 70% power
BUDGET_TARGET  = 300_000    # $300K per partner
TARGET_WEEKS   = 3.0

CELL_LABELS = ["Yahoo Test", "DSP (Scope3) Test", "Control Holdout"]
CELL_COLORS = ["#2196F3", "#FF9800", "#4CAF50"]

# ─── DMA NAME MAP (Nielsen standard codes) ───────────────────────────────────

DMA_NAMES = {
    500: "Portland-Auburn, ME",
    501: "New York, NY",
    502: "Binghamton, NY",
    503: "Macon, GA",
    504: "Philadelphia, PA",
    505: "Detroit, MI",
    506: "Boston-Manchester, MA",
    507: "Savannah, GA",
    508: "Pittsburgh, PA",
    509: "Ft. Wayne, IN",
    510: "Cleveland-Akron (Youngstown), OH",
    511: "Washington, DC",
    512: "Baltimore, MD",
    513: "Flint-Saginaw-Bay City, MI",
    514: "Minneapolis-St. Paul, MN",
    515: "Cincinnati, OH",
    516: "Springfield, MO",
    517: "Charlotte, NC",
    518: "Greensboro-High Point-Winston Salem, NC",
    519: "Syracuse, NY",
    520: "Raleigh-Durham, NC",
    521: "Knoxville, TN",
    522: "Columbus, GA",
    523: "Huntington-Charleston, WV",
    524: "Atlanta, GA",
    525: "Albany, GA",
    526: "Santa Barbara-Santa Maria, CA",
    527: "Indianapolis, IN",
    528: "Miami-Ft. Lauderdale, FL",
    529: "Louisville, KY",
    530: "Hartford-New Haven, CT",
    531: "Tri-Cities, TN/VA",
    532: "Albany-Schenectady-Troy, NY",
    533: "Columbia, SC",
    534: "Orlando-Daytona Beach-Melbourne, FL",
    535: "Columbus, OH",
    536: "Youngstown, OH",
    537: "Portland, OR",
    538: "Rochester, NY",
    539: "Tampa-St. Petersburg-Sarasota, FL",
    540: "Idaho Falls-Pocatello, ID",
    541: "Tucson-Sierra Vista, AZ",
    542: "Dayton, OH",
    543: "Bakersfield, CA",
    544: "Norfolk-Portsmouth-Newport News, VA",
    545: "Oklahoma City, OK",
    546: "Cedar Rapids-Waterloo-Iowa City, IA",
    547: "Richmond-Petersburg, VA",
    548: "West Palm Beach-Ft. Pierce, FL",
    549: "Anchorage, AK",
    550: "Wilmington, NC",
    551: "Lincoln-Hastings-Kearney, NE",
    552: "Presque Isle, ME",
    553: "Watertown, NY",
    554: "Wheeling, WV-Steubenville, OH",
    555: "Wilkes Barre-Scranton, PA",
    556: "Richmond-Petersburg, VA",
    557: "Greenville-New Bern-Washington, NC",
    558: "Santa Rosa, CA",
    559: "Tallahassee, FL",
    560: "Sacramento-Stockton-Modesto, CA",
    561: "Jacksonville, FL",
    562: "Grand Rapids-Kalamazoo-Battle Creek, MI",
    563: "Grand Rapids-Kalamazoo-Battle Creek, MI",
    564: "Charleston-Huntington, WV",
    565: "Elmira, NY",
    566: "Harrisburg-Lancaster-Lebanon-York, PA",
    567: "Greenville-Spartanburg-Asheville, NC/SC",
    569: "Bluefield-Beckley-Oak Hill, WV",
    570: "Denver, CO",
    571: "Salt Lake City, UT",
    573: "Roanoke-Lynchburg, VA",
    574: "Johnstown-Altoona, PA",
    575: "Chattanooga, TN",
    576: "Duluth, MN-Superior, WI",
    577: "Wichita-Hutchinson, KS",
    581: "Little Rock-Pine Bluff, AR",
    582: "Missoula, MT",
    583: "Alpena, MI",
    584: "Traverse City-Cadillac, MI",
    588: "Spokane, WA",
    592: "Augusta, GA-Aiken, SC",
    596: "Zanesville, OH",
    597: "Rapid City, SD",
    598: "Rochester, MN-Mason City, IA",
    600: "Corpus Christi, TX",
    602: "Chicago, IL",
    603: "Rockford, IL",
    604: "Champaign-Springfield-Decatur, IL",
    605: "Peoria-Bloomington, IL",
    606: "Springfield-Holyoke, MA",
    609: "St. Louis, MO",
    610: "Terre Haute, IN",
    611: "Evansville, IN",
    612: "Shreveport, LA",
    613: "Johnstown-Altoona, PA",
    616: "Kansas City, MO",
    617: "Milwaukee, WI",
    618: "Houston, TX",
    619: "Kansas City, MO",
    622: "New Orleans, LA",
    623: "Dallas-Ft. Worth, TX",
    624: "Odessa-Midland, TX",
    625: "Waco-Temple-Bryan, TX",
    626: "Victoria, TX",
    627: "Wichita Falls, TX-Lawton, OK",
    628: "Monroe, LA-El Dorado, AR",
    630: "Birmingham, AL",
    631: "Meridian, MS",
    632: "Hattiesburg-Laurel, MS",
    633: "Biloxi-Gulfport-Pascagoula, MS",
    634: "Huntsville-Decatur, AL",
    635: "Mobile, AL-Pensacola, FL",
    636: "Harlingen-Weslaco-Brownsville-McAllen, TX",
    637: "Austin, TX",
    638: "Laredo, TX",
    639: "Meridian, MS",
    640: "Memphis, TN",
    641: "San Antonio, TX",
    642: "Abilene-Sweetwater, TX",
    643: "Lubbock, TX",
    644: "Amarillo, TX",
    647: "Odessa-Midland, TX",
    648: "Albuquerque-Santa Fe, NM",
    649: "Tucson, AZ",
    650: "Oklahoma City, OK",
    651: "Tulsa, OK",
    652: "Laurel, MS",
    656: "Panama City, FL",
    657: "Fort Smith-Fayetteville, AR",
    658: "Fort Smith-Fayetteville-Springdale-Rogers, AR",
    659: "Nashville, TN",
    661: "Anniston, AL",
    662: "Greenwood-Greenville, MS",
    669: "Madison, WI",
    670: "Des Moines-Ames, IA",
    671: "Flint-Saginaw, MI",
    673: "Omaha, NE",
    675: "Davenport-Rock Island-Moline, IL/IA",
    676: "Minot-Bismarck-Dickinson, ND",
    678: "Salt Lake City, UT",
    679: "Columbus-Tupelo-West Point, MS",
    682: "Eau Claire, WI",
    686: "La Crosse-Eau Claire, WI",
    687: "Minneapolis-St. Paul, MN",
    691: "Lubbock, TX",
    692: "Amarillo, TX",
    693: "Little Rock-Pine Bluff, AR",
    698: "Lincoln-Hastings-Kearney, NE",
    702: "Clarksburg-Weston, WV",
    705: "Glendive, MT",
    709: "Tyler-Longview, TX",
    710: "Lafayette, LA",
    711: "Beaumont-Port Arthur, TX",
    716: "Baton Rouge, LA",
    717: "Fort Smith-Fayetteville, AR",
    718: "Jackson, MS",
    722: "Sioux Falls-Mitchell, SD",
    724: "Fargo-Valley City, ND",
    725: "Sioux City, IA",
    734: "Grand Junction-Montrose, CO",
    736: "Helena, MT",
    737: "Billings, MT",
    740: "North Platte, NE",
    743: "Honolulu, HI",
    744: "Spokane, WA",
    745: "Anchorage, AK",
    746: "Laredo, TX",
    747: "Juneau, AK",
    749: "Monterey-Salinas, CA",
    751: "Denver, CO",
    752: "Colorado Springs-Pueblo, CO",
    753: "Phoenix, AZ",
    754: "Butte-Bozeman, MT",
    755: "Great Falls, MT",
    756: "Santa Barbara-Santa Maria, CA",
    757: "Yuma, AZ-El Centro, CA",
    758: "Las Vegas, NV",
    759: "Reno, NV",
    760: "Chico-Redding, CA",
    762: "Medford-Klamath Falls, OR",
    764: "Bakersfield, CA",
    765: "El Paso, TX",
    766: "Eureka, CA",
    767: "Bend, OR",
    770: "Seattle-Tacoma, WA",
    771: "Albany, OR",
    773: "Yakima-Pasco-Richland-Kennewick, WA",
    789: "Albuquerque-Santa Fe, NM",
    790: "Phoenix, AZ",
    798: "Glendive, MT",
    800: "Boise, ID",
    801: "Salt Lake City, UT",
    802: "Palm Springs, CA",
    803: "Los Angeles, CA",
    804: "Palm Springs, CA",
    807: "San Francisco-Oakland-San Jose, CA",
    810: "Medford-Klamath Falls, OR",
    811: "Portland, OR",
    813: "Eugene, OR",
    819: "Seattle-Tacoma, WA",
    820: "Portland, OR",
    821: "Bend, OR",
    825: "San Diego, CA",
    828: "Monterey-Salinas, CA",
    839: "Las Vegas, NV",
    855: "Honolulu, HI",
    862: "Riverside-San Bernardino, CA",
    866: "Fresno-Visalia, CA",
    868: "Chico-Redding, CA",
    881: "Spokane, WA",
}

# ─── EXCLUSIONS ──────────────────────────────────────────────────────────────

# (A) In another active geo test
ACTIVE_TEST_EXCLUSIONS = {
    718: "Jackson, MS",
    612: "Shreveport, LA",
    515: "Cincinnati, OH",
    693: "Little Rock-Pine Bluff, AR",
    544: "Norfolk-Portsmouth-Newport News, VA",
    518: "Greensboro-High Point-Winston Salem, NC",
    765: "El Paso, TX",
    636: "Harlingen-Weslaco-Brownsville-McAllen, TX",
    566: "Harrisburg-Lancaster-Lebanon-York, PA",
    548: "West Palm Beach-Ft. Pierce, FL",
    503: "Macon, GA",
    522: "Columbus, GA",
    564: "Charleston-Huntington, WV",
    542: "Dayton, OH",
    866: "Fresno-Visalia, CA",
    825: "San Diego, CA",
    567: "Greenville-Spartanburg-Asheville, NC/SC",
    514: "Minneapolis-St. Paul, MN",
    575: "Chattanooga, TN",
    716: "Baton Rouge, LA",
}

# (B) Large markets excluded per test design
LARGE_MARKET_EXCLUSIONS = {
    501: "New York, NY",
    803: "Los Angeles, CA",
    623: "Dallas-Ft. Worth, TX",
    618: "Houston, TX",
    640: "Memphis, TN",
    527: "Indianapolis, IN",
    616: "Kansas City, MO",
    505: "Detroit, MI",
    630: "Birmingham, AL",
    512: "Baltimore, MD",
    517: "Charlotte, NC",
    524: "Atlanta, GA",
    529: "Louisville, KY",
    535: "Columbus, OH",
    504: "Philadelphia, PA",
    807: "San Francisco-Oakland-San Jose, CA",
    753: "Phoenix, AZ",
    659: "Nashville, TN",
    602: "Chicago, IL",
    622: "New Orleans, LA",
    508: "Pittsburgh, PA",
    650: "Oklahoma City, OK",
    609: "St. Louis, MO",
    839: "Las Vegas, NV",
    641: "San Antonio, TX",
    561: "Jacksonville, FL",
    617: "Milwaukee, WI",
    511: "Washington, DC",
    770: "Seattle-Tacoma, WA",
    819: "Seattle-Tacoma, WA",
}

# (C) Used in Design 1 — must not overlap
DESIGN1_DMAS = {
    # Cell 1 — Yahoo Test
    539: "Tampa-St. Petersburg-Sarasota, FL",
    510: "Cleveland-Akron (Youngstown), OH",
    686: "La Crosse-Eau Claire, WI",
    671: "Flint-Saginaw, MI",
    563: "Grand Rapids-Kalamazoo-Battle Creek, MI",
    790: "Phoenix, AZ",
    556: "Richmond-Petersburg, VA",
    625: "Waco-Temple-Bryan, TX",
    577: "Wichita-Hutchinson, KS",
    619: "Kansas City, MO",
    # Cell 2 — DSP (Scope3) Test
    534: "Orlando-Daytona Beach-Melbourne, FL",
    862: "Riverside-San Bernardino, CA",
    613: "Johnstown-Altoona, PA",
    820: "Portland, OR",
    635: "Mobile, AL-Pensacola, FL",
    557: "Greenville-New Bern-Washington, NC",
    507: "Savannah, GA",
    678: "Salt Lake City, UT",
    632: "Hattiesburg-Laurel, MS",
    789: "Albuquerque-Santa Fe, NM",
    # Cell 3 — Control Holdout
    528: "Miami-Ft. Lauderdale, FL",
    560: "Sacramento-Stockton-Modesto, CA",
    506: "Boston-Manchester, MA",
    751: "Denver, CO",
    533: "Columbia, SC",
    541: "Tucson-Sierra Vista, AZ",
    546: "Cedar Rapids-Waterloo-Iowa City, IA",
    691: "Lubbock, TX",
    570: "Denver, CO",
    513: "Flint-Saginaw-Bay City, MI",
}

EXCLUDED_DMA_CODES = {**ACTIVE_TEST_EXCLUSIONS, **LARGE_MARKET_EXCLUSIONS, **DESIGN1_DMAS}


# ─── DATA LOADING ────────────────────────────────────────────────────────────

def load_and_aggregate(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df["date"] = pd.to_datetime(df["date"])
    agg = (
        df.groupby("geo")
        .agg(
            total_enrollments=("enrollments", "sum"),
            total_users=("total users", "sum"),
            n_days=("date", "nunique"),
            prior_assignment=("assignment", "first"),
        )
        .reset_index()
    )
    agg["dma_name"] = agg["geo"].map(DMA_NAMES).fillna("Unknown")
    agg["daily_avg_enrollments"] = agg["total_enrollments"] / agg["n_days"]
    return agg


def load_spend(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    agg = df.groupby("dma_code")["paid_spend"].sum().reset_index()
    agg.rename(columns={"dma_code": "geo", "paid_spend": "total_paid_spend"}, inplace=True)
    return agg


def build_composite(df: pd.DataFrame,
                    enroll_weight: float = ENROLL_WEIGHT,
                    spend_weight: float  = SPEND_WEIGHT) -> pd.DataFrame:
    df = df.copy()
    for col, w_name in [("total_enrollments", "enroll_norm"),
                        ("total_paid_spend",   "spend_norm")]:
        lo, hi = df[col].min(), df[col].max()
        df[w_name] = (df[col] - lo) / (hi - lo) if hi > lo else 0.0
    df["composite"] = enroll_weight * df["enroll_norm"] + spend_weight * df["spend_norm"]
    return df


def filter_available(agg: pd.DataFrame):
    excluded_mask = agg["geo"].isin(EXCLUDED_DMA_CODES)
    return agg[~excluded_mask].copy().reset_index(drop=True), agg[excluded_mask].copy()


# ─── BALANCING ALGORITHM ─────────────────────────────────────────────────────

def _lag1_ac(arr: np.ndarray) -> float:
    if len(arr) < 4:
        return 0.0
    mu    = arr.mean()
    denom = ((arr - mu) ** 2).sum()
    if denom < 1e-12:
        return 0.0
    numer = ((arr[:-1] - mu) * (arr[1:] - mu)).sum()
    return float(np.clip(numer / denom, -1.0, 1.0))


def build_dma_weekly_series(raw_df: pd.DataFrame, available: pd.DataFrame) -> dict:
    raw = raw_df.copy()
    raw["week"] = pd.to_datetime(raw["date"]).dt.to_period("W").apply(lambda p: p.start_time)
    all_weeks = sorted(raw["week"].unique())
    week_pos  = {w: i for i, w in enumerate(all_weeks)}
    n_weeks   = len(all_weeks)
    series = {}
    for df_idx, row in available.iterrows():
        geo    = row["geo"]
        subset = raw[raw["geo"] == geo]
        arr    = np.zeros(n_weeks)
        if not subset.empty:
            wk_enroll = subset.groupby("week")["enrollments"].sum()
            for wk, val in wk_enroll.items():
                if wk in week_pos:
                    arr[week_pos[wk]] = val
        series[df_idx] = arr
    return series


def _max_sigma_eff(groups: list, weekly_by_idx: dict,
                   ctrl_idx: int, n_cells: int) -> float:
    n_weeks = len(next(iter(weekly_by_idx.values())))
    gw = [
        np.sum([weekly_by_idx[i] for i in g], axis=0) if g else np.zeros(n_weeks)
        for g in groups
    ]
    ctrl_w = gw[ctrl_idx]
    denom  = np.where(ctrl_w > 1.0, ctrl_w, 1.0)
    sigmas = []
    for i in range(n_cells):
        if i == ctrl_idx:
            continue
        rel = (gw[i] - ctrl_w) / denom
        rho = max(_lag1_ac(rel), 0.0)
        sigmas.append(float(rel.std()) * np.sqrt(1 + 2 * rho))
    return max(sigmas) if sigmas else 0.0


def greedy_balance(dmas: pd.DataFrame, n_cells: int, metric: str,
                   max_per_cell: int | None = None) -> list[list[int]]:
    sorted_df = dmas.sort_values(metric, ascending=False)
    groups: list[list[int]] = [[] for _ in range(n_cells)]
    group_sums = [0.0] * n_cells
    for idx, row in sorted_df.iterrows():
        eligible = (
            [i for i in range(n_cells) if len(groups[i]) < max_per_cell]
            if max_per_cell else range(n_cells)
        )
        target = eligible[int(np.argmin([group_sums[i] for i in eligible]))]
        groups[target].append(idx)
        group_sums[target] += row[metric]
    return groups


def local_search(dmas: pd.DataFrame, groups: list[list[int]], metric: str,
                 max_iter: int = 50_000, seed: int = 42,
                 equal_sizes: bool = False,
                 weekly_by_idx: dict | None = None,
                 ctrl_group_idx: int | None = None,
                 trend_weight: float = 0.0) -> list[list[int]]:
    use_trend = (weekly_by_idx is not None
                 and ctrl_group_idx is not None
                 and trend_weight > 0.0)

    rng        = random.Random(seed)
    n_cells    = len(groups)
    group_sums = [dmas.loc[g, metric].sum() for g in groups]

    if use_trend:
        n_weeks = len(next(iter(weekly_by_idx.values())))
        group_weekly: list = [
            np.sum([weekly_by_idx[idx] for idx in g], axis=0) if g else np.zeros(n_weeks)
            for g in groups
        ]
    else:
        group_weekly = []

    def _objective(sums: list, weekly: list) -> float:
        mean_s = float(np.mean(sums))
        if mean_s < 1e-12:
            return 0.0
        metric_imb = (max(sums) - min(sums)) / mean_s
        if not use_trend:
            return metric_imb
        ctrl_w  = weekly[ctrl_group_idx]
        denom   = np.where(ctrl_w > 1.0, ctrl_w, 1.0)
        ac_vals = []
        for i in range(n_cells):
            if i == ctrl_group_idx:
                continue
            rel = (weekly[i] - ctrl_w) / denom
            ac_vals.append(max(_lag1_ac(rel), 0.0))
        trend_pen = float(np.mean(ac_vals)) if ac_vals else 0.0
        return (1.0 - trend_weight) * metric_imb + trend_weight * trend_pen

    best_groups = [g[:] for g in groups]
    best_obj    = _objective(group_sums, group_weekly)
    ops         = ["swap"] if equal_sizes else ["move", "swap"]

    for _ in range(max_iter):
        op = rng.choice(ops)

        if op == "move":
            src = rng.randrange(n_cells)
            if not groups[src]:
                continue
            dst = rng.randrange(n_cells)
            if src == dst:
                continue
            idx_pos = rng.randrange(len(groups[src]))
            dma_idx = groups[src][idx_pos]
            val     = dmas.loc[dma_idx, metric]
            new_sums = group_sums[:]
            new_sums[src] -= val
            new_sums[dst] += val
            if use_trend:
                new_weekly      = list(group_weekly)
                new_weekly[src] = group_weekly[src] - weekly_by_idx[dma_idx]
                new_weekly[dst] = group_weekly[dst] + weekly_by_idx[dma_idx]
            else:
                new_weekly = []
            new_obj = _objective(new_sums, new_weekly)
            if new_obj < best_obj:
                groups[src].pop(idx_pos)
                groups[dst].append(dma_idx)
                group_sums   = new_sums
                group_weekly = new_weekly
                best_obj     = new_obj
                best_groups  = [g[:] for g in groups]

        else:
            a, b = rng.sample(range(n_cells), 2)
            if not groups[a] or not groups[b]:
                continue
            ia    = rng.randrange(len(groups[a]))
            ib    = rng.randrange(len(groups[b]))
            dma_a = groups[a][ia]
            dma_b = groups[b][ib]
            val_a = dmas.loc[dma_a, metric]
            val_b = dmas.loc[dma_b, metric]
            new_sums = group_sums[:]
            new_sums[a] += val_b - val_a
            new_sums[b] += val_a - val_b
            if use_trend:
                new_weekly    = list(group_weekly)
                new_weekly[a] = group_weekly[a] - weekly_by_idx[dma_a] + weekly_by_idx[dma_b]
                new_weekly[b] = group_weekly[b] - weekly_by_idx[dma_b] + weekly_by_idx[dma_a]
            else:
                new_weekly = []
            new_obj = _objective(new_sums, new_weekly)
            if new_obj < best_obj:
                groups[a][ia], groups[b][ib] = dma_b, dma_a
                group_sums   = new_sums
                group_weekly = new_weekly
                best_obj     = new_obj
                best_groups  = [g[:] for g in groups]

    return best_groups


# ─── REPORTING ───────────────────────────────────────────────────────────────

def build_result_df(available: pd.DataFrame, groups: list[list[int]],
                    cell_labels: list[str]) -> pd.DataFrame:
    available = available.copy()
    available["cell"] = ""
    available["cell_number"] = -1
    for i, group_indices in enumerate(groups):
        available.loc[group_indices, "cell"] = cell_labels[i]
        available.loc[group_indices, "cell_number"] = i + 1
    return available.sort_values(["cell_number", "total_enrollments"], ascending=[True, False])


def print_balance_report(result: pd.DataFrame, cell_labels: list[str]) -> None:
    print("\n" + "=" * 85)
    print("CELL ASSIGNMENTS — DESIGN 2  (Yahoo / DSP Scope3 / Control)")
    print("=" * 85)

    has_spend = "total_paid_spend" in result.columns
    enroll_totals, spend_totals = [], []

    for i, label in enumerate(cell_labels, 1):
        cell_df = result[result["cell_number"] == i]
        enroll  = cell_df["total_enrollments"].sum()
        spend   = cell_df["total_paid_spend"].sum() if has_spend else 0
        enroll_totals.append(enroll)
        spend_totals.append(spend)
        print(f"\n{'─'*85}")
        spend_str = f"  ${spend/1e6:.1f}M spend" if has_spend else ""
        print(f"  CELL {i}: {label}  ({len(cell_df)} DMAs,  {enroll:,.0f} enrollments{spend_str})")
        print(f"{'─'*85}")
        for _, row in cell_df.iterrows():
            spend_col = f"  ${row['total_paid_spend']/1e6:>7.2f}M" if has_spend else ""
            print(f"  DMA {row['geo']:>4}  {row['dma_name']:<45}  {row['total_enrollments']:>10,.0f}{spend_col}")

    grand_enroll = sum(enroll_totals)
    grand_spend  = sum(spend_totals)

    print(f"\n{'='*85}")
    print("BALANCE SUMMARY — ENROLLMENTS")
    print(f"{'='*85}")
    print(f"  {'Cell':<28}  {'Enrollments':>14}  {'% of Total':>10}  {'DMAs':>5}")
    print(f"  {'-'*28}  {'-'*14}  {'-'*10}  {'-'*5}")
    for label, total in zip(cell_labels, enroll_totals):
        n = len(result[result["cell"] == label])
        print(f"  {label:<28}  {total:>14,.0f}  {total/grand_enroll*100:>9.2f}%  {n:>5}")
    print(f"  {'TOTAL':<28}  {grand_enroll:>14,.0f}  {'100.00%':>10}  {len(result):>5}")

    cv_e  = np.std(enroll_totals) / np.mean(enroll_totals) * 100
    imb_e = (max(enroll_totals) - min(enroll_totals)) / np.mean(enroll_totals) * 100
    print(f"\n  CV (enrollments):               {cv_e:.3f}%")
    print(f"  Max-Min Imbalance (enrollments):{imb_e:.3f}%")

    if has_spend:
        print(f"\n{'='*85}")
        print("BALANCE SUMMARY — PAID SPEND")
        print(f"{'='*85}")
        print(f"  {'Cell':<28}  {'Paid Spend ($)':>16}  {'% of Total':>10}  {'DMAs':>5}")
        print(f"  {'-'*28}  {'-'*16}  {'-'*10}  {'-'*5}")
        for label, spend in zip(cell_labels, spend_totals):
            n = len(result[result["cell"] == label])
            print(f"  {label:<28}  ${spend:>15,.0f}  {spend/grand_spend*100:>9.2f}%  {n:>5}")
        print(f"  {'TOTAL':<28}  ${grand_spend:>15,.0f}  {'100.00%':>10}  {len(result):>5}")
        cv_s  = np.std(spend_totals) / np.mean(spend_totals) * 100
        imb_s = (max(spend_totals) - min(spend_totals)) / np.mean(spend_totals) * 100
        print(f"\n  CV (paid spend):                {cv_s:.3f}%")
        print(f"  Max-Min Imbalance (paid spend): {imb_s:.3f}%")

    print(f"\n  Target: CV < 2%, Imbalance < 5% on both metrics")
    both_ok = cv_e < 2.0 and (not has_spend or cv_s < 2.0)
    if both_ok:
        print(f"  ✓ Balance is within acceptable range for incrementality testing")
    else:
        print(f"  ⚠ Consider re-running with a different seed or adjusting weights")


def print_exclusion_summary(excluded: pd.DataFrame) -> None:
    print("\n" + "=" * 70)
    print(f"EXCLUDED DMAs  ({len(excluded)} total — not eligible for Design 2)")
    print("=" * 70)
    active_codes = set(ACTIVE_TEST_EXCLUSIONS)
    large_codes  = set(LARGE_MARKET_EXCLUSIONS)
    d1_codes     = set(DESIGN1_DMAS)

    print("\n(A) In another active geo test:")
    for _, row in (excluded[excluded["geo"].isin(active_codes)]
                   .sort_values("total_enrollments", ascending=False).iterrows()):
        print(f"  DMA {row['geo']:>4}  {row['dma_name']:<45}  {row['total_enrollments']:>10,.0f} enrollments")

    print("\n(B) Large markets excluded per test design:")
    for _, row in (excluded[excluded["geo"].isin(large_codes)]
                   .sort_values("total_enrollments", ascending=False).iterrows()):
        print(f"  DMA {row['geo']:>4}  {row['dma_name']:<45}  {row['total_enrollments']:>10,.0f} enrollments")

    print("\n(C) Used in Design 1 — no overlap allowed:")
    for _, row in (excluded[excluded["geo"].isin(d1_codes)]
                   .sort_values("total_enrollments", ascending=False).iterrows()):
        print(f"  DMA {row['geo']:>4}  {row['dma_name']:<45}  {row['total_enrollments']:>10,.0f} enrollments")


# ─── VISUALIZATIONS ──────────────────────────────────────────────────────────

def plot_group_balance(result: pd.DataFrame, raw_df: pd.DataFrame,
                       raw_spend_df: pd.DataFrame,
                       cell_labels: list[str], output_path: str) -> None:
    colors = CELL_COLORS

    group_enroll = {label: result[result["cell"] == label]["total_enrollments"].sum()
                    for label in cell_labels}
    group_spend  = {label: result[result["cell"] == label]["total_paid_spend"].sum()
                    for label in cell_labels}
    group_counts = {label: len(result[result["cell"] == label]) for label in cell_labels}
    grand_enroll = sum(group_enroll.values())
    grand_spend  = sum(group_spend.values())

    cv_e = np.std(list(group_enroll.values())) / np.mean(list(group_enroll.values())) * 100
    cv_s = np.std(list(group_spend.values()))  / np.mean(list(group_spend.values()))  * 100

    geo_to_cell = result.set_index("geo")["cell"].to_dict()

    ts = raw_df[raw_df["geo"].isin(geo_to_cell)].copy()
    ts["cell"] = ts["geo"].map(geo_to_cell)
    ts["week"] = pd.to_datetime(ts["date"]).dt.to_period("W").apply(lambda p: p.start_time)
    weekly_enroll = (
        ts.groupby(["week", "cell"])["enrollments"]
        .sum().reset_index().sort_values("week")
    )

    sp = raw_spend_df[raw_spend_df["dma_code"].isin(geo_to_cell)].copy()
    sp["cell"] = sp["dma_code"].map(geo_to_cell)
    sp["week"] = pd.to_datetime(sp["enrollment_date"]).dt.to_period("W").apply(lambda p: p.start_time)
    weekly_spend = (
        sp.groupby(["week", "cell"])["paid_spend"]
        .sum().reset_index().sort_values("week")
    )

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 7))
    fig.patch.set_facecolor("#F8F9FA")

    ax1.set_facecolor("#FFFFFF")
    for label, color in zip(cell_labels, colors):
        n     = group_counts[label]
        total = group_enroll[label]
        grp   = weekly_enroll[weekly_enroll["cell"] == label]
        ax1.plot(grp["week"], grp["enrollments"] / 1_000,
                 label=f"{label}  ({n} DMAs · {total/1e6:.2f}M)",
                 color=color, linewidth=2.4, alpha=0.9)
        ax1.fill_between(grp["week"], grp["enrollments"] / 1_000, alpha=0.08, color=color)
    ax1.set_title("Weekly Enrollment Trend by Cell — Design 2\n(parallel trends check)",
                  fontsize=12, fontweight="bold", pad=12)
    ax1.set_ylabel("Weekly Enrollments (K)", fontsize=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}K"))
    ax1.legend(fontsize=9.5, framealpha=0.95, loc="upper left", edgecolor="#CCCCCC")
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.tick_params(axis="x", labelsize=9, rotation=20)
    ax1.text(0.98, 0.03, f"CV = {cv_e:.3f}%  |  Grand total = {grand_enroll:,.0f}",
             transform=ax1.transAxes, ha="right", fontsize=8.5, color="#555555")

    ax2.set_facecolor("#FFFFFF")
    for label, color in zip(cell_labels, colors):
        n     = group_counts[label]
        total = group_spend[label]
        grp   = weekly_spend[weekly_spend["cell"] == label]
        ax2.plot(grp["week"], grp["paid_spend"] / 1e6,
                 label=f"{label}  ({n} DMAs · ${total/1e9:.2f}B)",
                 color=color, linewidth=2.4, alpha=0.9)
        ax2.fill_between(grp["week"], grp["paid_spend"] / 1e6, alpha=0.08, color=color)
    ax2.set_title("Weekly Paid Spend Trend by Cell — Design 2\n(spend balance check)",
                  fontsize=12, fontweight="bold", pad=12)
    ax2.set_ylabel("Weekly Paid Spend ($M)", fontsize=10)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    ax2.legend(fontsize=9.5, framealpha=0.95, loc="upper left", edgecolor="#CCCCCC")
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.tick_params(axis="x", labelsize=9, rotation=20)
    ax2.text(0.98, 0.03, f"CV = {cv_s:.3f}%  |  Grand total = ${grand_spend/1e9:.2f}B",
             transform=ax2.transAxes, ha="right", fontsize=8.5, color="#555555")

    n_dmas = sum(group_counts.values())
    fig.suptitle(
        f"Design 2 — 3-Cell Geo Test  │  {n_dmas} DMAs ({n_dmas // N_CELLS} per cell)  │"
        f"  Enrollment CV = {cv_e:.3f}%  │  Spend CV = {cv_s:.3f}%",
        fontsize=11, fontweight="bold", color="#1A237E", y=1.01,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\nBalance chart saved to: {output_path}")


# ─── POWER ANALYSIS ──────────────────────────────────────────────────────────

def _ac_inflate(sigma_rel: float, autocorr: float) -> float:
    rho = max(autocorr, 0.0)
    return sigma_rel * np.sqrt(1 + 2 * rho)


def weeks_needed(sigma_rel: float, lift: float, k: float, autocorr: float = 0.0) -> int:
    sigma_eff = _ac_inflate(sigma_rel, autocorr)
    return int(np.ceil(k * (sigma_eff / lift) ** 2))


def mde_at_weeks(sigma_rel: float, t_weeks: float, k: float, autocorr: float = 0.0) -> float:
    sigma_eff = _ac_inflate(sigma_rel, autocorr)
    return np.sqrt(k / t_weeks) * sigma_eff * 100


def compute_power_stats(result: pd.DataFrame, raw_df: pd.DataFrame,
                        cell_labels: list[str],
                        alpha: float = 0.05,
                        power: float = POWER_TARGET) -> dict:
    z_alpha = scipy_stats.norm.ppf(1 - alpha / 2)
    z_beta  = scipy_stats.norm.ppf(power)
    k       = (z_alpha + z_beta) ** 2

    geo_to_cell = result.set_index("geo")["cell"].to_dict()
    ts = raw_df[raw_df["geo"].isin(geo_to_cell)].copy()
    ts["cell"] = ts["geo"].map(geo_to_cell)
    ts["week"] = pd.to_datetime(ts["date"]).dt.to_period("W").apply(lambda p: p.start_time)

    weekly = (
        ts.groupby(["week", "cell"])["enrollments"]
        .sum().reset_index().sort_values("week")
    )

    control_label = cell_labels[-1]
    control_w = weekly[weekly["cell"] == control_label].set_index("week")["enrollments"]

    stats_out = {}
    for treat_label in cell_labels[:-1]:
        treat_w = weekly[weekly["cell"] == treat_label].set_index("week")["enrollments"]
        common  = control_w.index.intersection(treat_w.index)
        c = control_w[common]
        t = treat_w[common]
        rel_diff = (t - c) / c

        stats_out[treat_label] = {
            "sigma_rel":       rel_diff.std(),
            "mu_control":      c.mean(),
            "mu_treat":        t.mean(),
            "n_weeks":         len(common),
            "autocorr_lag1":   rel_diff.autocorr(lag=1),
            "z_alpha":         z_alpha,
            "z_beta":          z_beta,
            "k":               k,
            "rel_diff_series": rel_diff,
        }
    return stats_out


def print_power_report(stats_out: dict, icpe: float = ICPE,
                       budget_cap: float = BUDGET_TARGET) -> None:
    lift_range        = [0.03, 0.05, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15]
    target_lifts      = [0.025, 0.03, 0.04]
    target_weeks      = TARGET_WEEKS
    budget_cap_target = BUDGET_TARGET

    print("\n" + "=" * 110)
    print(f"POWER ANALYSIS — DESIGN 2  "
          f"(α=0.05 two-sided, {int(POWER_TARGET*100)}% power target  |  "
          f"iCPE=${icpe:,.0f}  |  Budget cap=${budget_cap:,.0f})")
    print("=" * 110)

    for treat_label, s in stats_out.items():
        sigma_eff = _ac_inflate(s["sigma_rel"], s["autocorr_lag1"])
        print(f"\n  ── {treat_label}  vs  Control Holdout ──")
        print(f"     Pre-period weeks:                   {s['n_weeks']}")
        print(f"     Avg weekly enrollments (control):   {s['mu_control']:>10,.0f}")
        print(f"     Pre-period noise σ (raw / AC-eff):  {s['sigma_rel']*100:.2f}% / {sigma_eff*100:.2f}%")
        print(f"     Lag-1 autocorrelation:              {s['autocorr_lag1']:>9.3f}")
        print()

        col_w = 28 + len(str(int(icpe)))
        print(f"     {'Lift':>5}  {'Effect/wk':>10}  {'Weeks':>6}  "
              f"{'Incr. Enrollments':>20}  {'Budget @ $'+str(int(icpe))+'/enroll':>{col_w}}  {'Powered?':>9}")
        print(f"     {'-----':>5}  {'----------':>10}  {'------':>6}  "
              f"{'--------------------':>20}  {'-'*col_w:>{col_w}}  {'---------':>9}")

        prev_over = True
        for lift in lift_range:
            w          = weeks_needed(s["sigma_rel"], lift, s["k"], s["autocorr_lag1"])
            effect_wk  = s["mu_control"] * lift
            total_incr = effect_wk * w
            budget     = total_incr * icpe
            powered    = "✓ YES" if budget <= budget_cap else "✗ OVER"
            marker     = "  ◄ budget crossover" if prev_over != (budget > budget_cap) else ""
            prev_over  = budget > budget_cap
            print(f"     {lift*100:>4.0f}%  {effect_wk:>10,.0f}  {w:>6}  "
                  f"{total_incr:>20,.0f}  ${budget:>{col_w},.0f}  {powered:>9}{marker}")

    # Budget constraint reverse analysis
    print(f"\n{'─'*110}")
    print(f"  BUDGET CONSTRAINT ANALYSIS  —  given ${budget_cap:,.0f} total spend per partner")
    print(f"{'─'*110}")
    implied_incr = budget_cap / icpe
    print(f"  At iCPE=${icpe:,.0f}:  ${budget_cap:,.0f} budget → {implied_incr:,.0f} incremental enrollments expected\n")

    z_alpha_val = list(stats_out.values())[0]["z_alpha"]

    for treat_label, s in stats_out.items():
        sigma_eff = _ac_inflate(s["sigma_rel"], s["autocorr_lag1"])
        print(f"  {treat_label}  (σ_eff={sigma_eff*100:.2f}%, μ_control/week={s['mu_control']:,.0f})")
        print(f"  {'Duration':>10}  {'Implied lift':>13}  {'Achievable power':>17}  {'MDE ({:.0f}% pwr)'.format(int(POWER_TARGET*100)):>22}")
        print(f"  {'----------':>10}  {'-------------':>13}  {'-----------------':>17}  {'----------------------':>22}")
        for t_wks in [1, 2, 2.5, 3, 4, 6]:
            implied_lift = (implied_incr / t_wks) / s["mu_control"]
            z_score      = (implied_lift / sigma_eff) * np.sqrt(t_wks) - z_alpha_val
            pwr          = scipy_stats.norm.cdf(z_score) * 100
            mde          = mde_at_weeks(s["sigma_rel"], t_wks, s["k"], s["autocorr_lag1"])
            flag         = "  ← TARGET: $300K / 3 weeks" if t_wks == 3 else ""
            print(f"  {t_wks:>9}w  {implied_lift*100:>12.2f}%  {pwr:>16.1f}%  {mde:>21.2f}%{flag}")
        print()

    print("  Incr. enrollments = (weekly control enrollments × lift %) × weeks.")
    k_val = list(stats_out.values())[0]["k"]
    print(f"  MDE uses k={k_val:.3f} (z_α + z_β)² for {int(POWER_TARGET*100)}% power / α=0.05 two-sided.")

    # Target scenario callout
    print(f"\n{'═'*110}")
    print(f"  TARGET SCENARIO CHECK — {target_weeks:.0f}-week test, $300K budget "
          f"(iCPE=${icpe:,.0f} → {int(budget_cap_target/icpe)} incr. enrollments)")
    print(f"{'═'*110}")

    regimes = [
        (f"α=5%, {int(POWER_TARGET*100)}% power", 0.05, POWER_TARGET),
        ("α=5%, 80% power",                        0.05, 0.80),
        ("α=10%, 70% power",                       0.10, 0.70),
    ]
    print(f"\n  {'Cell':<28}  {'Lift':>5}  "
          + "  ".join(f"{'Pwr@'+str(int(target_weeks))+'w ('+r[0]+')':>24}" for r in regimes))
    print(f"  {'-'*28}  {'-'*5}  " + "  ".join(f"{'-'*24}" for _ in regimes))

    recommendation = None
    for treat_label, s in stats_out.items():
        sigma_eff = _ac_inflate(s["sigma_rel"], s["autocorr_lag1"])
        for lift in target_lifts:
            row = f"  {treat_label:<28}  {lift*100:>5.1f}%"
            for _, alpha_r, power_r in regimes:
                z_a_r = scipy_stats.norm.ppf(1 - alpha_r / 2)
                pwr   = scipy_stats.norm.cdf((lift / sigma_eff) * np.sqrt(target_weeks) - z_a_r) * 100
                flag  = " ✓" if pwr >= power_r * 100 else "  "
                row  += f"  {pwr:>21.1f}%{flag}"
            print(row)

    print(f"\n  MDE at {target_weeks:.0f} weeks (α=5%, {int(POWER_TARGET*100)}% power):")
    for treat_label, s in stats_out.items():
        mde = mde_at_weeks(s["sigma_rel"], target_weeks, s["k"], s["autocorr_lag1"])
        sigma_eff = _ac_inflate(s["sigma_rel"], s["autocorr_lag1"])
        design_lift = budget_cap_target / icpe / target_weeks / s["mu_control"]
        passes_primary = scipy_stats.norm.cdf(
            (design_lift / sigma_eff) * np.sqrt(target_weeks) - s["z_alpha"]) >= POWER_TARGET
        passes_80 = scipy_stats.norm.cdf(
            (design_lift / sigma_eff) * np.sqrt(target_weeks) - s["z_alpha"]) >= 0.80
        status = "✓ Meets 70% power target" if passes_primary else (
                 "→ 80% power requires more budget/time" if passes_80 else
                 "✗ Below 70% target — consider seed/weight tuning")
        if not passes_primary and recommendation is None:
            recommendation = "below_target"
        print(f"    {treat_label:<28}  MDE={mde:.2f}%  implied_lift={design_lift*100:.2f}%   {status}")

    print()
    if recommendation is None:
        print(f"  ✓ Both channels meet ≥{int(POWER_TARGET*100)}% power at $300K / 3-week design.")
    else:
        print(f"  ⚠ One or both channels below {int(POWER_TARGET*100)}% target — review DMA composition.")


def plot_power_analysis(stats_out: dict, output_path: str) -> None:
    treat_labels   = list(stats_out.keys())
    colors_treat   = CELL_COLORS[:len(treat_labels)]
    lift_pct_range = np.linspace(1, 20, 400)
    budget_cap     = BUDGET_TARGET       # $300K for Design 2

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 7))
    fig.patch.set_facecolor("#F8F9FA")

    # Left: weeks needed vs. lift
    ax1.set_facecolor("#FFFFFF")
    for treat_label, color in zip(treat_labels, colors_treat):
        s = stats_out[treat_label]
        w = [weeks_needed(s["sigma_rel"], lift / 100, s["k"], s["autocorr_lag1"])
             for lift in lift_pct_range]
        ax1.plot(lift_pct_range, w, color=color, linewidth=2.5, label=treat_label)

    ax1.axhline(TARGET_WEEKS, color="#E53935", linewidth=1.2, linestyle=":",
                alpha=0.7, label=f"{TARGET_WEEKS:.0f}-week target duration")

    ax1.set_title(
        f"Weeks Needed to Detect Lift — Design 2\n"
        f"vs. Control Holdout  (α=0.05, {int(POWER_TARGET*100)}% power)",
        fontsize=12, fontweight="bold", pad=10)
    ax1.set_xlabel("Assumed Lift in Enrollments (%)", fontsize=10)
    ax1.set_ylabel("Test Duration (weeks)", fontsize=10)
    ax1.set_xlim(1, 20)
    ax1.set_ylim(0, 12)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax1.legend(fontsize=9.5, framealpha=0.95, edgecolor="#CCCCCC")
    ax1.spines[["top", "right"]].set_visible(False)

    for treat_label, color in zip(treat_labels, colors_treat):
        s = stats_out[treat_label]
        for lift in [3, 5, 7, 10, 15, 20]:
            w = weeks_needed(s["sigma_rel"], lift / 100, s["k"], s["autocorr_lag1"])
            if w <= 11:
                ax1.annotate(f"{w}w", xy=(lift, w), xytext=(lift + 0.3, w + 0.3),
                             fontsize=7.5, color=color, fontweight="bold")

    # Right: budget needed vs. lift with $300K cap line
    ax2.set_facecolor("#FFFFFF")
    for treat_label, color in zip(treat_labels, colors_treat):
        s = stats_out[treat_label]
        budgets = []
        for lift in lift_pct_range:
            w      = weeks_needed(s["sigma_rel"], lift / 100, s["k"], s["autocorr_lag1"])
            budget = s["mu_control"] * (lift / 100) * w * ICPE
            budgets.append(budget / 1_000)
        ax2.plot(lift_pct_range, budgets, color=color, linewidth=2.5, label=treat_label)

    ax2.axhline(budget_cap / 1_000, color="#D32F2F", linewidth=2.2,
                linestyle="--", label=f"${budget_cap/1000:.0f}K budget cap")
    ax2.fill_between(lift_pct_range, 0, budget_cap / 1_000, alpha=0.06, color="#D32F2F")
    ax2.text(10.5, budget_cap / 1_000 + 20, f"$300K cap",
             fontsize=9, color="#D32F2F", fontweight="bold")

    ax2.set_title(f"Budget Required vs. Assumed Lift — Design 2\n"
                  f"(iCPE=${ICPE:,}/enrollment, {int(POWER_TARGET*100)}% power)",
                  fontsize=12, fontweight="bold", pad=10)
    ax2.set_xlabel("Assumed Lift in Enrollments (%)", fontsize=10)
    ax2.set_ylabel("Required Budget ($K)", fontsize=10)
    ax2.set_xlim(1, 20)
    ax2.set_ylim(0)
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.0f}K"))
    ax2.legend(fontsize=9.5, framealpha=0.95, edgecolor="#CCCCCC")
    ax2.spines[["top", "right"]].set_visible(False)

    noise_lines = "   |   ".join(
        f"{lbl}: σ_eff={_ac_inflate(s['sigma_rel'], s['autocorr_lag1'])*100:.2f}%"
        for lbl, s in stats_out.items()
    )
    fig.text(0.5, -0.02, f"Pre-period effective noise (AC-corrected):  {noise_lines}",
             ha="center", fontsize=9, color="#555555", style="italic")

    fig.suptitle(
        f"Design 2 Power Analysis — Yahoo Test & DSP (Scope3) Test vs. Control Holdout\n"
        f"Smaller / mid-tier DMAs  |  Target: {int(POWER_TARGET*100)}% power @ $300K / 3 weeks",
        fontsize=12, fontweight="bold", color="#1A237E", y=1.03,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Power analysis chart saved to: {output_path}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("DESIGN 2 — Smaller / Mid-Tier DMA Balancing")
    print("Target: 70% power at $300K / 3 weeks  |  No overlap with Design 1")
    print("=" * 70)

    print(f"\nLoading data from: {DATA_FILE}")
    raw_df = pd.read_csv(DATA_FILE, index_col=0)
    agg    = load_and_aggregate(DATA_FILE)
    print(f"  {len(agg)} total DMAs found")

    available, excluded = filter_available(agg)
    print(f"  {len(excluded)} DMAs excluded → {len(available)} DMAs available for Design 2")

    print(f"\nLoading paid spend from: {SPEND_FILE}")
    raw_spend_df = pd.read_csv(SPEND_FILE)
    spend_agg    = load_spend(SPEND_FILE)
    available    = available.merge(spend_agg, on="geo", how="left")
    available["total_paid_spend"] = available["total_paid_spend"].fillna(0)
    n_matched = (available["total_paid_spend"] > 0).sum()
    print(f"  {n_matched}/{len(available)} DMAs matched to spend data")
    print(f"  Total enrollments in pool: {available['total_enrollments'].sum():,.0f}")
    print(f"  Total paid spend in pool:  ${available['total_paid_spend'].sum():,.0f}")

    available = build_composite(available, ENROLL_WEIGHT, SPEND_WEIGHT)

    n_total   = N_CELLS * N_PER_CELL
    available = available.nlargest(n_total, "composite").reset_index(drop=True)
    print(f"  Selected top {n_total} DMAs ({N_PER_CELL} per cell target) by composite score")

    metric = "composite"
    print(f"\nBalancing on composite metric ({ENROLL_WEIGHT*100:.0f}% enrollments + "
          f"{SPEND_WEIGHT*100:.0f}% paid spend)...")

    print_exclusion_summary(excluded)

    print(f"\nRunning greedy LPT balancing (capped at {N_PER_CELL} DMAs per cell)...")
    groups = greedy_balance(available, N_CELLS, metric, max_per_cell=N_PER_CELL)

    print("Building DMA weekly enrollment series for parallel-trends penalty...")
    weekly_by_idx = build_dma_weekly_series(raw_df, available)

    print(f"Running multi-seed local search (seeds 0–9, 100k iters each, "
          f"trend_weight={TREND_WEIGHT})...")
    greedy_groups = [g[:] for g in groups]
    best_sigma    = float("inf")
    best_groups   = None

    # σ_eff target: need σ_eff ≤ 174 / μ_control for 70% power at $300K/3w
    # (174 = 250 × √3 / 2.484, where 250 = 750 incr.enrollments / 3 weeks)
    for seed in range(10):
        candidate = local_search(
            available, [g[:] for g in greedy_groups], metric,
            max_iter=100_000, seed=seed, equal_sizes=True,
            weekly_by_idx=weekly_by_idx,
            ctrl_group_idx=N_CELLS - 1, trend_weight=TREND_WEIGHT,
        )
        sigma  = _max_sigma_eff(candidate, weekly_by_idx, N_CELLS - 1, N_CELLS)
        marker = ""
        if sigma < best_sigma:
            best_sigma  = sigma
            best_groups = candidate
            marker      = "  ← best"
        print(f"  seed {seed:2d}: max σ_eff = {sigma*100:.2f}%{marker}")

    print(f"Best max σ_eff = {best_sigma*100:.2f}%")
    print(f"  (need σ_eff × μ_control ≤ 174 for 70% power @ $300K/3w — "
          f"confirmed in power report below)")
    groups = best_groups

    result = build_result_df(available, groups, CELL_LABELS)
    print_balance_report(result, CELL_LABELS)

    plot_group_balance(result, raw_df, raw_spend_df, CELL_LABELS, PLOT_FILE)

    print("\nRunning power analysis...")
    power_stats = compute_power_stats(result, raw_df, CELL_LABELS)
    print_power_report(power_stats)
    plot_power_analysis(power_stats, POWER_PLOT_FILE)

    out_cols = ["cell_number", "cell", "geo", "dma_name", "total_enrollments",
                "total_paid_spend", "total_users", "daily_avg_enrollments",
                "n_days", "prior_assignment"]
    result[out_cols].to_csv(OUTPUT_FILE, index=False)
    print(f"\nDesign 2 assignments saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
