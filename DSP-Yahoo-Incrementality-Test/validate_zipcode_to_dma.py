#!/usr/bin/env python3
"""
Validate the FIVETRAN.GSHEETS.ZIPCODE_TO_DMA Snowflake table against the
canonical Nielsen DMA list (dma_code_reference.csv).

Catches the kinds of bugs that caused the 2026-05-26 audit:
  • DMA codes in the GSheet that don't exist in Nielsen 2024
  • DMA codes labeled with the wrong canonical name
  • ZIP codes mapped to multiple DMAs (should be 1:1)
  • Suspiciously small or suspiciously large per-DMA ZIP counts
  • DMAs in the reference with zero ZIPs mapped (coverage gaps)

Run with:  python3 validate_zipcode_to_dma.py
A browser window will open for Snowflake SSO auth.
"""

import os
import sys
import pandas as pd
import snowflake.connector

BASE_DIR  = os.path.dirname(__file__)
REF_FILE  = os.path.join(BASE_DIR, "dma_code_reference.csv")
OUT_FILE  = os.path.join(BASE_DIR, "zipcode_to_dma_audit.csv")

def main():
    if not os.path.exists(REF_FILE):
        sys.exit(f"Missing reference file: {REF_FILE}")
    ref = pd.read_csv(REF_FILE)
    canonical_codes = set(ref["dma_code"].astype(int).tolist())
    canonical_names = dict(zip(ref["dma_code"].astype(int), ref["dma_name"]))

    print(f"Loaded canonical reference: {len(canonical_codes)} DMA codes")
    print(f"Connecting to Snowflake (browser SSO will open)...")
    con = snowflake.connector.connect(
        connection_name="chime",
        role="SNOWFLAKE_PROD_ANALYST_OKTA",
        warehouse="ANALYTICS_WH",
        database="FIVETRAN",
        schema="GSHEETS",
    )

    print(f"Pulling ZIPCODE_TO_DMA...")
    cur = con.cursor()
    cur.execute("""
        SELECT zip_code, dma_code, dma_name
        FROM FIVETRAN.GSHEETS.ZIPCODE_TO_DMA
    """)
    rows = cur.fetchall()
    cols = [d[0].lower() for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    cur.close(); con.close()

    df["dma_code"] = df["dma_code"].astype(int)
    print(f"  {len(df):,} ZIP↔DMA mappings, "
          f"{df['zip_code'].nunique():,} unique ZIPs, "
          f"{df['dma_code'].nunique()} unique DMAs\n")

    issues = []

    # CHECK 1: DMA codes not in canonical Nielsen
    in_gsheet = set(df["dma_code"].unique())
    unknown_codes = in_gsheet - canonical_codes
    print(f"CHECK 1 — DMA codes in GSheet but NOT in Nielsen reference:")
    if unknown_codes:
        for c in sorted(unknown_codes):
            count = (df["dma_code"] == c).sum()
            sample_name = df[df["dma_code"] == c]["dma_name"].iloc[0]
            print(f"  ⚠ code {c} ({sample_name}) — {count} ZIPs — UNKNOWN")
            issues.append({"check":"unknown_code","code":c,"detail":f"{sample_name} ({count} ZIPs)"})
    else:
        print(f"  ✓ All codes in the GSheet exist in the Nielsen reference")

    # CHECK 2: Canonical codes with zero ZIP coverage
    missing_codes = canonical_codes - in_gsheet
    print(f"\nCHECK 2 — Nielsen codes with NO ZIPs in the GSheet (coverage gaps):")
    if missing_codes:
        for c in sorted(missing_codes):
            print(f"  ⚠ code {c} ({canonical_names[c]}) — 0 ZIPs mapped")
            issues.append({"check":"no_coverage","code":c,"detail":canonical_names[c]})
    else:
        print(f"  ✓ All {len(canonical_codes)} Nielsen DMAs have at least 1 ZIP")

    # CHECK 3: Code↔name mismatches (canonical name vs GSheet name)
    print(f"\nCHECK 3 — Code↔name mismatches (GSheet label vs canonical Nielsen):")
    name_check = df.groupby("dma_code")["dma_name"].first()
    n_mismatch = 0
    for code, gsheet_name in name_check.items():
        if code not in canonical_codes:
            continue
        canon = canonical_names[code]
        def norm(s): return ''.join(c.lower() for c in str(s) if c.isalnum())
        if norm(gsheet_name)[:6] != norm(canon)[:6] and norm(gsheet_name).split('(')[0] != norm(canon).split('(')[0]:
            n_mismatch += 1
            if n_mismatch <= 30:  # Show first 30
                print(f"  ⚠ code {code}: GSheet='{gsheet_name}' vs Nielsen='{canon}'")
            issues.append({"check":"name_mismatch","code":code,
                           "detail":f"gsheet='{gsheet_name}' canon='{canon}'"})
    if n_mismatch == 0:
        print(f"  ✓ All names in the GSheet match the Nielsen canonical")
    elif n_mismatch > 30:
        print(f"  ... ({n_mismatch - 30} more mismatches — see {OUT_FILE})")

    # CHECK 4: ZIPs mapped to multiple DMAs
    print(f"\nCHECK 4 — ZIPs mapped to more than 1 DMA (should be 1:1):")
    multi = df.groupby("zip_code")["dma_code"].nunique()
    multi = multi[multi > 1]
    if len(multi) > 0:
        print(f"  ⚠ {len(multi)} ZIPs map to >1 DMA")
        for zip_code in multi.head(10).index:
            codes = df[df["zip_code"] == zip_code]["dma_code"].unique().tolist()
            print(f"     ZIP {zip_code} → DMAs {codes}")
            issues.append({"check":"multi_dma_zip","code":-1,
                           "detail":f"ZIP {zip_code} → {codes}"})
    else:
        print(f"  ✓ Every ZIP maps to exactly 1 DMA")

    # CHECK 5: ZIP count per DMA — outliers
    print(f"\nCHECK 5 — ZIP-count outliers per DMA:")
    zip_counts = df.groupby("dma_code").size().sort_values()
    print(f"  Median ZIPs per DMA: {zip_counts.median():.0f}")
    print(f"  Range: {zip_counts.min()}–{zip_counts.max()}")
    print(f"  Smallest 5:")
    for code in zip_counts.head(5).index:
        print(f"     {code} ({canonical_names.get(code,'?'):<40}): {zip_counts[code]} ZIPs")
    print(f"  Largest 5:")
    for code in zip_counts.tail(5).index:
        print(f"     {code} ({canonical_names.get(code,'?'):<40}): {zip_counts[code]} ZIPs")

    # Write audit log
    if issues:
        out = pd.DataFrame(issues)
        out.to_csv(OUT_FILE, index=False)
        print(f"\n⚠ {len(issues)} issues found — written to {OUT_FILE}")
    else:
        print(f"\n✓ NO ISSUES — GSheet ZIPCODE_TO_DMA is clean against Nielsen reference")


if __name__ == "__main__":
    main()
