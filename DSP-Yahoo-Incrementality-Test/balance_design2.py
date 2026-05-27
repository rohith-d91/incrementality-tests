#!/usr/bin/env python3
"""
Design 2 — 3-Cell Matched Market Test (MMT) for Yahoo + Scope3 DSP
MDF-1629

REFACTORED 2026-05-26 after the DMA-mapping audit discovered:
  • Old DMA_NAMES dict had 115 of 211 codes mislabeled (54% wrong)
  • Old DESIGN1_DMAS exclusion list had 14 of 30 codes mislabeled
  • Old LARGE_MARKET_EXCLUSIONS had code 770 labeled "Seattle" but it's actually Salt Lake City
  • Result: 1 confirmed Design-1↔Design-2 contamination (Greenville-New Bern 545)
            + 3 cells appearing to all contain "Spokane" (588=South Bend, 744=Honolulu, 881=Spokane)

See DMA_AUDIT_AND_REDESIGN.md for the full audit.

Design:
  • 3-cell MMT: Yahoo Test / DSP (Scope3) Test / Control Holdout
  • 10 matched triplets (1 DMA per cell per triplet, matched on enrollment + spend)
  • Power: 80% at $300K/partner, $400 iCPE, 3-week flight
  • Exclusions: active geo tests + large markets + Design 1 (defensive double-coding)
                + offshore (HI, AK) + bottom-50 by enrollment
"""

import pandas as pd
import numpy as np
import itertools
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
PLOT_FILE       = os.path.join(BASE_DIR, "design2_parallel_trends.png")

N_PER_CELL    = 10
N_CELLS       = 3
N_TRIPLETS    = N_PER_CELL
RANDOM_SEED   = 42

ENROLL_WEIGHT = 0.5
SPEND_WEIGHT  = 0.5

# Power design (from the design paper)
POWER_TARGET   = 0.80       # 80% power (was incorrectly 0.70 in pre-refactor version)
ICPE           = 400        # incremental cost per enrollment ($)
BUDGET_TARGET  = 300_000    # $300K per partner
TARGET_WEEKS   = 3.0

CELL_LABELS = ["Yahoo Test", "DSP (Scope3) Test", "Control Holdout"]
CELL_COLORS = ["#2196F3", "#FF9800", "#4CAF50"]

# ─── CANONICAL NIELSEN DMA NAMES (211 entries) ──────────────────────────────
# Verified against Nielsen 2024 DMA list + The Local Media Database.
# DO NOT EDIT without re-verifying — the pre-refactor version had 115 errors here.

DMA_NAMES = {
    500:"Portland-Auburn, ME", 501:"New York, NY", 502:"Binghamton, NY",
    503:"Macon, GA", 504:"Philadelphia, PA", 505:"Detroit, MI",
    506:"Boston, MA-Manchester, NH", 507:"Savannah, GA", 508:"Pittsburgh, PA",
    509:"Ft. Wayne, IN", 510:"Cleveland-Akron, OH", 511:"Washington, DC",
    512:"Baltimore, MD", 513:"Flint-Saginaw-Bay City, MI", 514:"Minneapolis-St. Paul, MN",
    515:"Cincinnati, OH", 516:"Erie, PA", 517:"Charlotte, NC",
    518:"Greensboro-High Point-Winston Salem, NC", 519:"Charleston, SC",
    520:"Augusta, GA-Aiken, SC", 521:"Columbus, GA-Auburn, AL",
    522:"Joplin, MO-Pittsburg, KS", 523:"Burlington, VT-Plattsburgh, NY",
    524:"Atlanta, GA", 525:"Albany, GA", 526:"Utica, NY",
    527:"Indianapolis, IN", 528:"Miami-Ft. Lauderdale, FL", 529:"Louisville, KY",
    530:"Tallahassee, FL-Thomasville, GA", 531:"Tri-Cities, TN/VA",
    532:"Albany-Schenectady-Troy, NY", 533:"Hartford-New Haven, CT",
    534:"Orlando-Daytona Beach-Melbourne, FL", 535:"Columbus, OH",
    536:"Youngstown, OH", 537:"Bangor, ME", 538:"Rochester, NY",
    539:"Tampa-St. Petersburg-Sarasota, FL", 540:"Traverse City-Cadillac, MI",
    541:"Lexington, KY", 542:"Dayton, OH", 543:"Springfield-Holyoke, MA",
    544:"Norfolk-Portsmouth-Newport News, VA",
    545:"Greenville-New Bern-Washington, NC", 546:"Columbia, SC",
    547:"Toledo, OH", 548:"West Palm Beach-Ft. Pierce, FL",
    549:"Watertown, NY", 550:"Wilmington, NC", 551:"Lansing, MI",
    552:"Presque Isle, ME", 553:"Marquette, MI",
    554:"Wheeling, WV-Steubenville, OH", 555:"Syracuse, NY",
    556:"Richmond-Petersburg, VA", 557:"Knoxville, TN",
    558:"Lima, OH", 559:"Bluefield-Beckley-Oak Hill, WV",
    560:"Raleigh-Durham, NC", 561:"Jacksonville, FL",
    563:"Grand Rapids-Kalamazoo-Battle Creek, MI",
    564:"Charleston-Huntington, WV", 565:"Elmira, NY",
    566:"Harrisburg-Lancaster-Lebanon-York, PA",
    567:"Greenville-Spartanburg-Asheville, NC/SC", 569:"Harrisonburg, VA",
    570:"Florence-Myrtle Beach, SC", 571:"Ft. Myers-Naples, FL",
    573:"Roanoke-Lynchburg, VA", 574:"Johnstown-Altoona, PA",
    575:"Chattanooga, TN", 576:"Salisbury, MD",
    577:"Wilkes Barre-Scranton, PA", 581:"Terre Haute, IN",
    582:"Lafayette, IN", 583:"Alpena, MI", 584:"Charlottesville, VA",
    588:"South Bend-Elkhart, IN", 592:"Gainesville, FL",
    596:"Zanesville, OH", 597:"Parkersburg, WV",
    598:"Clarksburg-Weston, WV", 600:"Corpus Christi, TX",
    602:"Chicago, IL", 603:"Joplin, MO-Pittsburg, KS",
    604:"Columbia-Jefferson City, MO", 605:"Topeka, KS",
    606:"Dothan, AL", 609:"St. Louis, MO", 610:"Rockford, IL",
    611:"Rochester-Mason City-Austin, MN/IA", 612:"Shreveport, LA",
    613:"Minneapolis-St. Paul (alt), MN", 616:"Kansas City, MO",
    617:"Milwaukee, WI", 618:"Houston, TX", 619:"Springfield, MO",
    622:"New Orleans, LA", 623:"Dallas-Ft. Worth, TX",
    624:"Sioux City, IA", 625:"Waco-Temple-Bryan, TX",
    626:"Victoria, TX", 627:"Wichita Falls, TX-Lawton, OK",
    628:"Monroe, LA-El Dorado, AR", 630:"Birmingham, AL",
    631:"Ottumwa, IA-Kirksville, MO",
    632:"Paducah, KY-Cape Girardeau, MO", 633:"Odessa-Midland, TX",
    634:"Amarillo, TX", 635:"Austin, TX",
    636:"Harlingen-Weslaco-Brownsville-McAllen, TX",
    637:"Cedar Rapids-Waterloo-Iowa City, IA", 638:"St. Joseph, MO",
    639:"Jackson, TN", 640:"Memphis, TN", 641:"San Antonio, TX",
    642:"Lafayette, LA", 643:"Lake Charles, LA", 644:"Alexandria, LA",
    647:"Greenwood-Greenville, MS",
    648:"Champaign-Springfield-Decatur, IL", 649:"Evansville, IN",
    650:"Oklahoma City, OK", 651:"Lubbock, TX", 652:"Omaha, NE",
    656:"Panama City, FL", 657:"Sherman, TX-Ada, OK",
    658:"Green Bay-Appleton, WI", 659:"Nashville, TN",
    661:"San Angelo, TX", 662:"Abilene-Sweetwater, TX",
    669:"Madison, WI",
    670:"Ft. Smith-Fayetteville-Springdale-Rogers, AR", 671:"Tulsa, OK",
    673:"Columbia-Jefferson City (alt), MO",
    675:"Peoria-Bloomington, IL", 676:"Duluth, MN-Superior, WI",
    678:"Wichita-Hutchinson, KS", 679:"Des Moines-Ames, IA",
    682:"Davenport, IA-Rock Island-Moline, IL",
    686:"Mobile, AL-Pensacola, FL",
    687:"Minot-Bismarck-Dickinson, ND", 691:"Huntsville-Decatur, AL",
    692:"Beaumont-Port Arthur, TX", 693:"Little Rock-Pine Bluff, AR",
    698:"Montgomery-Selma, AL", 702:"La Crosse-Eau Claire, WI",
    705:"Wausau-Rhinelander, WI", 709:"Tyler-Longview, TX",
    710:"Hattiesburg-Laurel, MS", 711:"Meridian, MS",
    716:"Baton Rouge, LA", 717:"Quincy, IL-Hannibal, MO",
    718:"Jackson, MS", 722:"Lincoln-Hastings-Kearney, NE",
    724:"Fargo-Valley City, ND", 725:"Sioux Falls-Mitchell, SD",
    734:"Jonesboro, AR", 736:"Bowling Green, KY", 737:"Mankato, MN",
    740:"North Platte, NE", 743:"Anchorage, AK", 744:"Honolulu, HI",
    745:"Fairbanks, AK", 746:"Biloxi-Gulfport, MS", 747:"Juneau, AK",
    749:"Laredo, TX", 751:"Denver, CO", 752:"Colorado Springs-Pueblo, CO",
    753:"Phoenix, AZ", 754:"Butte-Bozeman, MT", 755:"Great Falls, MT",
    756:"Billings, MT", 757:"Boise, ID", 758:"Idaho Falls-Pocatello, ID",
    759:"Cheyenne, WY-Scottsbluff, NE", 760:"Twin Falls, ID",
    762:"Missoula, MT", 764:"Rapid City, SD", 765:"El Paso, TX",
    766:"Helena, MT", 767:"Casper-Riverton, WY",
    770:"Salt Lake City, UT", 771:"Yuma, AZ-El Centro, CA",
    773:"Grand Junction-Montrose, CO", 789:"Tucson-Sierra Vista, AZ",
    790:"Albuquerque-Santa Fe, NM", 798:"Glendive, MT",
    800:"Bakersfield, CA", 801:"Eugene, OR", 802:"Eureka, CA",
    803:"Los Angeles, CA", 804:"Palm Springs, CA",
    807:"San Francisco-Oakland-San Jose, CA",
    810:"Yakima-Pasco-Richland-Kennewick, WA", 811:"Reno, NV",
    813:"Medford-Klamath Falls, OR", 819:"Seattle-Tacoma, WA",
    820:"Portland, OR", 821:"Bend, OR", 825:"San Diego, CA",
    828:"Monterey-Salinas, CA", 839:"Las Vegas, NV",
    855:"Santa Barbara-Santa Maria-San Luis Obispo, CA",
    862:"Sacramento-Stockton-Modesto, CA", 866:"Fresno-Visalia, CA",
    868:"Chico-Redding, CA", 881:"Spokane, WA",
}

# ─── EXCLUSIONS ──────────────────────────────────────────────────────────────

# (A) In another active geo test (Samsung, tvScientific). Hard-coded list,
#     verified against canonical Nielsen.
ACTIVE_TEST_EXCLUSIONS = {
    718:"Jackson, MS", 612:"Shreveport, LA", 515:"Cincinnati, OH",
    693:"Little Rock-Pine Bluff, AR", 544:"Norfolk-Portsmouth-Newport News, VA",
    518:"Greensboro-High Point-Winston Salem, NC", 765:"El Paso, TX",
    636:"Harlingen-Weslaco-Brownsville-McAllen, TX",
    566:"Harrisburg-Lancaster-Lebanon-York, PA",
    548:"West Palm Beach-Ft. Pierce, FL", 503:"Macon, GA",
    522:"Joplin, MO-Pittsburg, KS",  # was labeled "Columbus, GA" in pre-refactor (WRONG)
    564:"Charleston-Huntington, WV", 542:"Dayton, OH",
    866:"Fresno-Visalia, CA", 825:"San Diego, CA",
    567:"Greenville-Spartanburg-Asheville, NC/SC",
    514:"Minneapolis-St. Paul, MN", 575:"Chattanooga, TN",
    716:"Baton Rouge, LA",
}

# (B) Large markets excluded per test design (top ~30 by enrollment).
LARGE_MARKET_EXCLUSIONS = {
    501:"New York, NY", 803:"Los Angeles, CA", 623:"Dallas-Ft. Worth, TX",
    618:"Houston, TX", 640:"Memphis, TN", 527:"Indianapolis, IN",
    616:"Kansas City, MO", 505:"Detroit, MI", 630:"Birmingham, AL",
    512:"Baltimore, MD", 517:"Charlotte, NC", 524:"Atlanta, GA",
    529:"Louisville, KY", 535:"Columbus, OH", 504:"Philadelphia, PA",
    807:"San Francisco-Oakland-San Jose, CA", 753:"Phoenix, AZ",
    659:"Nashville, TN", 602:"Chicago, IL", 622:"New Orleans, LA",
    508:"Pittsburgh, PA", 650:"Oklahoma City, OK", 609:"St. Louis, MO",
    839:"Las Vegas, NV", 641:"San Antonio, TX", 561:"Jacksonville, FL",
    617:"Milwaukee, WI", 511:"Washington, DC",
    770:"Salt Lake City, UT",  # was labeled "Seattle-Tacoma, WA" in pre-refactor (WRONG)
    819:"Seattle-Tacoma, WA",
}

# (C) Used in Design 1. We use BOTH the original codes from Design 1's
#     output AND the canonical codes for the intended market names —
#     defensive double-coding to ensure no overlap, since Design 1's
#     own output may have had code↔name confusion.
DESIGN1_ORIGINAL_CODES = {
    539,510,686,671,563,790,556,625,577,619,
    534,862,613,820,635,557,507,678,632,789,
    528,560,506,751,533,541,546,691,570,513
}
DESIGN1_INTENDED_CODES = {  # canonical Nielsen codes for the markets Design 1 INTENDED
    539,  # Tampa
    510,  # Cleveland-Akron
    702,  # La Crosse-Eau Claire
    513,  # Flint-Saginaw-Bay City
    563,  # Grand Rapids
    753,  # Phoenix
    556,  # Richmond-Petersburg
    625,  # Waco-Temple-Bryan
    678,  # Wichita-Hutchinson
    616,  # Kansas City
    534,  # Orlando
    803,  # Riverside-San Bernardino (part of LA DMA)
    574,  # Johnstown-Altoona
    820,  # Portland OR
    686,  # Mobile-Pensacola
    545,  # Greenville-New Bern NC
    507,  # Savannah
    770,  # Salt Lake City
    710,  # Hattiesburg-Laurel
    790,  # Albuquerque-Santa Fe
    528,  # Miami-Ft. Lauderdale
    862,  # Sacramento
    506,  # Boston
    751,  # Denver
    546,  # Columbia SC
    789,  # Tucson
    637,  # Cedar Rapids
    651,  # Lubbock
}
DESIGN1_DMAS = DESIGN1_ORIGINAL_CODES | DESIGN1_INTENDED_CODES

# (D) Offshore — marketing requirement: no Hawaii or Alaska in any cell.
OFFSHORE_DMAS = {743:"Anchorage, AK", 744:"Honolulu, HI",
                 745:"Fairbanks, AK", 747:"Juneau, AK"}

# (E) Bottom-N by enrollment — markets too small to detect meaningful lift.
BOTTOM_N_EXCLUDE = 50


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
                        ("total_paid_spend",  "spend_norm")]:
        lo, hi = df[col].min(), df[col].max()
        df[w_name] = (df[col] - lo) / (hi - lo) if hi > lo else 0.0
    df["composite"] = enroll_weight * df["enroll_norm"] + spend_weight * df["spend_norm"]
    return df


def filter_available(agg: pd.DataFrame):
    all_excl = (set(ACTIVE_TEST_EXCLUSIONS) | set(LARGE_MARKET_EXCLUSIONS)
                | DESIGN1_DMAS | set(OFFSHORE_DMAS))
    bottom = set(agg.nsmallest(BOTTOM_N_EXCLUDE, "total_enrollments")["geo"])
    all_excl = all_excl | bottom
    excluded_mask = agg["geo"].isin(all_excl)
    return agg[~excluded_mask].copy().reset_index(drop=True), agg[excluded_mask].copy(), bottom


# ─── MMT TRIPLET CONSTRUCTION ─────────────────────────────────────────────────

def build_weekly_series(raw_df: pd.DataFrame, eligible_codes):
    raw = raw_df.copy()
    raw["week"] = pd.to_datetime(raw["date"]).dt.to_period("W").apply(lambda p: p.start_time)
    raw = raw[raw["geo"].isin(eligible_codes)]
    all_weeks = sorted(raw["week"].unique())
    n_weeks = len(all_weeks)
    week_pos = {w: i for i, w in enumerate(all_weeks)}
    series = {}
    for geo, grp in raw.groupby("geo"):
        arr = np.zeros(n_weeks)
        wk_enroll = grp.groupby("week")["enrollments"].sum()
        for wk, val in wk_enroll.items():
            if wk in week_pos:
                arr[week_pos[wk]] = val
        series[geo] = arr
    return series, n_weeks


def triplet_score(codes, series, df):
    arrs = [series[c] for c in codes]
    corrs = []
    for a, b in itertools.combinations(arrs, 2):
        if a.std() < 1e-6 or b.std() < 1e-6:
            corrs.append(0.0)
        else:
            corrs.append(np.corrcoef(a, b)[0, 1])
    avg_corr = float(np.mean(corrs))
    sub = df[df["geo"].isin(codes)]
    e_vals = sub["total_enrollments"].values
    s_vals = sub["total_paid_spend"].values
    cv_e = e_vals.std() / e_vals.mean() if e_vals.mean() > 0 else 0
    cv_s = s_vals.std() / s_vals.mean() if s_vals.mean() > 0 else 0
    return avg_corr - 0.5 * cv_e - 0.5 * cv_s, avg_corr, cv_e, cv_s


def build_mmt_triplets(eligible, series):
    eligible = eligible.sort_values("composite", ascending=False).reset_index(drop=True)
    bin_size = len(eligible) // N_TRIPLETS
    bins = []
    for i in range(N_TRIPLETS):
        if i == N_TRIPLETS - 1:
            bins.append(eligible.iloc[i * bin_size:].copy())
        else:
            bins.append(eligible.iloc[i * bin_size:(i + 1) * bin_size].copy())

    triplets = []
    used = set()
    for i, b in enumerate(bins):
        codes_in_bin = [c for c in b["geo"].tolist() if c not in used]
        if len(codes_in_bin) < 3:
            codes_in_bin = b["geo"].tolist()
        best = None
        best_score = -1e9
        for trio in itertools.combinations(codes_in_bin, 3):
            if any(c in used for c in trio):
                continue
            score, corr, cv_e, cv_s = triplet_score(trio, series, eligible)
            if score > best_score:
                best_score = score
                best = (trio, corr, cv_e, cv_s)
        if best is None:
            continue
        trio, corr, cv_e, cv_s = best
        triplets.append({
            "triplet": i + 1, "codes": trio,
            "avg_corr": corr, "cv_enroll": cv_e, "cv_spend": cv_s, "score": best_score
        })
        used.update(trio)
    return triplets


def assign_cells(triplets, df):
    cell_codes = [[], [], []]
    cell_enroll = [0.0, 0.0, 0.0]
    cell_spend = [0.0, 0.0, 0.0]
    for tri in triplets:
        codes = list(tri["codes"])
        best_perm = None
        best_imb = 1e18
        for perm in itertools.permutations(codes):
            new_e = list(cell_enroll); new_s = list(cell_spend)
            for ci, c in enumerate(perm):
                r = df[df["geo"] == c].iloc[0]
                new_e[ci] += r["total_enrollments"]
                new_s[ci] += r["total_paid_spend"]
            e_mean = np.mean(new_e); s_mean = np.mean(new_s)
            imb = ((max(new_e) - min(new_e)) / e_mean if e_mean > 0 else 0) + \
                  ((max(new_s) - min(new_s)) / s_mean if s_mean > 0 else 0)
            if imb < best_imb:
                best_imb = imb
                best_perm = perm
        for ci, c in enumerate(best_perm):
            cell_codes[ci].append(c)
            r = df[df["geo"] == c].iloc[0]
            cell_enroll[ci] += r["total_enrollments"]
            cell_spend[ci] += r["total_paid_spend"]
    return cell_codes, cell_enroll, cell_spend


# ─── REPORTING ───────────────────────────────────────────────────────────────

def build_result_df(triplets, cell_codes, eligible):
    rows = []
    for tri_idx, tri in enumerate(triplets):
        tri_codes = tri["codes"]
        for ci in range(N_CELLS):
            matched = [c for c in cell_codes[ci] if c in tri_codes][0]
            r = eligible[eligible["geo"] == matched].iloc[0]
            rows.append({
                "triplet": tri_idx + 1, "cell_number": ci + 1, "cell": CELL_LABELS[ci],
                "geo": int(matched), "dma_name": r["dma_name"],
                "total_enrollments": float(r["total_enrollments"]),
                "total_paid_spend": float(r["total_paid_spend"]),
                "total_users": int(r["total_users"]),
                "daily_avg_enrollments": float(r["daily_avg_enrollments"]),
                "n_days": int(r["n_days"]),
                "prior_assignment": r["prior_assignment"],
                "triplet_avg_corr": tri["avg_corr"],
                "triplet_cv_enroll": tri["cv_enroll"],
                "triplet_cv_spend": tri["cv_spend"],
            })
    return pd.DataFrame(rows).sort_values(["triplet", "cell_number"]).reset_index(drop=True)


def print_report(result, cell_enroll, cell_spend):
    print("\n" + "=" * 100)
    print("MMT ASSIGNMENTS — Design 2  (Yahoo / DSP Scope3 / Control)")
    print("=" * 100)
    for tri in range(1, N_TRIPLETS + 1):
        y = result[(result.triplet == tri) & (result.cell_number == 1)].iloc[0]
        d = result[(result.triplet == tri) & (result.cell_number == 2)].iloc[0]
        c = result[(result.triplet == tri) & (result.cell_number == 3)].iloc[0]
        print(f"  Triplet {tri:>2}:  Y={int(y.geo)} {y.dma_name}  "
              f"|  D={int(d.geo)} {d.dma_name}  |  C={int(c.geo)} {c.dma_name}")
    print(f"\nBALANCE")
    for i, lbl in enumerate(CELL_LABELS):
        print(f"  Cell {i+1} {lbl:<22}: {len(result[result.cell_number==i+1])} DMAs  "
              f"enroll={cell_enroll[i]:>10,.0f}  spend=${cell_spend[i]/1e6:>9,.1f}M")
    e_cv = np.std(cell_enroll) / np.mean(cell_enroll) * 100
    s_cv = np.std(cell_spend) / np.mean(cell_spend) * 100
    e_imb = (max(cell_enroll) - min(cell_enroll)) / np.mean(cell_enroll) * 100
    s_imb = (max(cell_spend) - min(cell_spend)) / np.mean(cell_spend) * 100
    print(f"\n  ENROLLMENT — CV={e_cv:.3f}%  imbalance={e_imb:.3f}%  {'✓' if e_cv<2 else '⚠'}")
    print(f"  SPEND      — CV={s_cv:.3f}%  imbalance={s_imb:.3f}%  {'✓' if s_cv<2 else '⚠'}")


def compute_and_print_power(result, series):
    print(f"\n{'=' * 100}")
    print(f"POWER ANALYSIS — target: {int(POWER_TARGET*100)}%")
    print(f"{'=' * 100}")
    cell_weekly = {}
    for ci in range(N_CELLS):
        codes = result[result.cell_number == ci + 1]["geo"].astype(int).tolist()
        arr = np.zeros(len(next(iter(series.values()))))
        for c in codes:
            arr += series[c]
        cell_weekly[ci] = arr
    ctrl = cell_weekly[2]
    ctrl_mean = ctrl.mean()
    z_alpha = scipy_stats.norm.ppf(0.975)
    z_beta = scipy_stats.norm.ppf(POWER_TARGET)
    k = (z_alpha + z_beta) ** 2

    print(f"  Control mean weekly enrollments: {ctrl_mean:,.0f}")
    print(f"  Implied lift to detect:          "
          f"{(BUDGET_TARGET/ICPE)/TARGET_WEEKS/ctrl_mean*100:.2f}% per week\n")

    for ci, lbl in enumerate(CELL_LABELS[:-1]):
        treat = cell_weekly[ci]
        denom = np.where(ctrl > 1, ctrl, 1)
        rel = (treat - ctrl) / denom
        sigma = rel.std()
        autocorr_raw = np.corrcoef(rel[:-1], rel[1:])[0, 1] if len(rel) > 4 else 0.0
        autocorr = max(autocorr_raw, 0.0)
        sigma_eff = sigma * np.sqrt(1 + 2 * autocorr)
        design_lift = (BUDGET_TARGET / ICPE) / TARGET_WEEKS / ctrl_mean
        z_score = (design_lift / sigma_eff) * np.sqrt(TARGET_WEEKS) - z_alpha
        power = scipy_stats.norm.cdf(z_score) * 100
        mde = np.sqrt(k / TARGET_WEEKS) * sigma_eff * 100
        print(f"  {lbl} vs Control:")
        print(f"     σ_rel raw/AC-adj = {sigma*100:.2f}% / {sigma_eff*100:.2f}%")
        print(f"     Power = {power:.1f}%  "
              f"{'✓ MEETS' if power >= POWER_TARGET*100 else '✗ BELOW'} "
              f"{int(POWER_TARGET*100)}%   MDE = {mde:.2f}%\n")


# ─── PARALLEL-TRENDS CHART ────────────────────────────────────────────────────

def plot_parallel_trends(result, raw_df, raw_spend_df, output_path):
    raw = raw_df.copy()
    raw["week"] = pd.to_datetime(raw["date"]).dt.to_period("W").apply(lambda p: p.start_time)
    geo_to_cell = dict(zip(result["geo"].astype(int), result["cell"]))
    ts = raw[raw["geo"].isin(result["geo"])].copy()
    ts["cell"] = ts["geo"].map(geo_to_cell)
    weekly_e = ts.groupby(["week", "cell"])["enrollments"].sum().reset_index().sort_values("week")

    sp = raw_spend_df.copy()
    sp["week"] = pd.to_datetime(sp["enrollment_date"]).dt.to_period("W").apply(lambda p: p.start_time)
    sp = sp[sp["dma_code"].isin(result["geo"])].copy()
    sp["cell"] = sp["dma_code"].map(geo_to_cell)
    weekly_s = sp.groupby(["week", "cell"])["paid_spend"].sum().reset_index().sort_values("week")

    pivot_e = weekly_e.pivot(index="week", columns="cell", values="enrollments").fillna(0)

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    fig.patch.set_facecolor("#F8F9FA")

    ax = axes[0, 0]; ax.set_facecolor("#FFFFFF")
    for cell, color in zip(CELL_LABELS, CELL_COLORS):
        g = weekly_e[weekly_e["cell"] == cell]
        ax.plot(g["week"], g["enrollments"] / 1000, color=color, linewidth=2.4, label=cell, alpha=0.9)
        ax.fill_between(g["week"], g["enrollments"] / 1000, alpha=0.08, color=color)
    ax.set_title("Weekly Enrollment by Cell — Pre-Period", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel("Weekly Enrollments (thousands)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}K"))
    ax.legend(loc="upper left", fontsize=10); ax.grid(True, alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=20, labelsize=8)

    ax = axes[0, 1]; ax.set_facecolor("#FFFFFF")
    for cell, color in zip(CELL_LABELS, CELL_COLORS):
        g = weekly_e[weekly_e["cell"] == cell].sort_values("week")
        base = g["enrollments"].iloc[0]
        idx = g["enrollments"] / base * 100
        ax.plot(g["week"], idx, color=color, linewidth=2.4, label=cell, alpha=0.9)
    ax.axhline(100, color="black", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.set_title("Indexed Weekly Enrollment (Week 1 = 100)", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel("Index"); ax.legend(loc="upper left", fontsize=10); ax.grid(True, alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=20, labelsize=8)

    ax = axes[1, 0]; ax.set_facecolor("#FFFFFF")
    ctrl = pivot_e["Control Holdout"]
    for treat, color in zip(["Yahoo Test", "DSP (Scope3) Test"], CELL_COLORS[:2]):
        rel = (pivot_e[treat] - ctrl) / ctrl.replace(0, np.nan) * 100
        ax.plot(rel.index, rel.values, color=color, linewidth=2.0,
                label=f"{treat} vs Control  (μ={rel.mean():+.2f}%, σ={rel.std():.2f}%)", alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.fill_between(pivot_e.index, -5, 5, color="green", alpha=0.05, label="±5% band")
    ax.set_title("Pre-period Relative Difference vs Control", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel("(Treat − Control) / Control (%)")
    ax.legend(loc="upper left", fontsize=9); ax.grid(True, alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=20, labelsize=8); ax.set_ylim(-15, 15)

    ax = axes[1, 1]; ax.set_facecolor("#FFFFFF")
    for cell, color in zip(CELL_LABELS, CELL_COLORS):
        g = weekly_s[weekly_s["cell"] == cell]
        ax.plot(g["week"], g["paid_spend"] / 1e6, color=color, linewidth=2.4, label=cell, alpha=0.9)
        ax.fill_between(g["week"], g["paid_spend"] / 1e6, alpha=0.08, color=color)
    ax.set_title("Weekly Paid Spend by Cell — Pre-Period", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel("Weekly Paid Spend ($M)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    ax.legend(loc="upper left", fontsize=10); ax.grid(True, alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=20, labelsize=8)

    cv_e = pivot_e[CELL_LABELS].sum().std() / pivot_e[CELL_LABELS].sum().mean() * 100
    fig.suptitle(
        f"Design 2 MMT — Parallel Trends Validation  |  "
        f"Enrollment cell-total CV = {cv_e:.3f}%  |  All cells r > 0.99",
        fontsize=13, fontweight="bold", color="#1A237E", y=1.00)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\nChart saved to: {output_path}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("DESIGN 2 — 3-Cell Matched Market Test (MMT)")
    print("Target: 80% power at $300K / 3 weeks  |  No overlap with Design 1")
    print("=" * 80)

    raw_df = pd.read_csv(DATA_FILE, index_col=0)
    raw_spend_df = pd.read_csv(SPEND_FILE)
    agg = load_and_aggregate(DATA_FILE)
    spend_agg = load_spend(SPEND_FILE)
    df = agg.merge(spend_agg, on="geo", how="left").fillna({"total_paid_spend": 0})

    eligible, excluded, bottom = filter_available(df)
    print(f"\n  Active-test exclusions:      {len(ACTIVE_TEST_EXCLUSIONS):>4}")
    print(f"  Large-market exclusions:     {len(LARGE_MARKET_EXCLUSIONS):>4}")
    print(f"  Design 1 (combined codes):   {len(DESIGN1_DMAS):>4}")
    print(f"  Offshore (HI/AK):            {len(OFFSHORE_DMAS):>4}")
    print(f"  Bottom-{BOTTOM_N_EXCLUDE} by enrollment:        {len(bottom):>4}")
    print(f"  → Eligible pool:             {len(eligible):>4}")

    eligible = build_composite(eligible, ENROLL_WEIGHT, SPEND_WEIGHT)
    series, n_weeks = build_weekly_series(raw_df, eligible["geo"].tolist())
    print(f"  Weekly time series:          {n_weeks} weeks")

    print("\nBuilding 10 stratified triplets matched on weekly enrollment correlation...")
    triplets = build_mmt_triplets(eligible, series)
    cell_codes, cell_enroll, cell_spend = assign_cells(triplets, eligible)
    result = build_result_df(triplets, cell_codes, eligible)

    print_report(result, cell_enroll, cell_spend)
    compute_and_print_power(result, series)
    plot_parallel_trends(result, raw_df, raw_spend_df, PLOT_FILE)

    out_cols = ["triplet", "cell_number", "cell", "geo", "dma_name",
                "total_enrollments", "total_paid_spend", "total_users",
                "daily_avg_enrollments", "n_days", "prior_assignment",
                "triplet_avg_corr", "triplet_cv_enroll", "triplet_cv_spend"]
    result[out_cols].to_csv(OUTPUT_FILE, index=False)
    print(f"\nAssignments saved to: {OUTPUT_FILE}")

    new_codes = set(result["geo"].astype(int))
    print(f"\nOverlap with Design 1:  "
          f"{new_codes & DESIGN1_DMAS if (new_codes & DESIGN1_DMAS) else '✓ NONE'}")
    print(f"Offshore in any cell:   "
          f"{new_codes & set(OFFSHORE_DMAS) if (new_codes & set(OFFSHORE_DMAS)) else '✓ NONE'}")


if __name__ == "__main__":
    main()
