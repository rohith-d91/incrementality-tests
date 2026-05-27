"""
Map GA4 city-level visitor data to DMA using Gma_Geocid_US.csv.

Inputs:
  - /Users/rohith.devarasetty/Documents/Cursor/tvScientific Incrementality Test/Visitor data 0526.csv
  - /tmp/tvsci/Gma_Geocid_US.csv

Output:
  - /tmp/tvsci/Visitors_by_DMA_0526.csv   (date, dma_code, dma_name, total_users, cta_taps, n_cities, n_cities_mapped)

Also prints a mapping-coverage report so we know how much of the GA4 traffic
fell into "unmapped" / unknown city IDs.
"""
import pandas as pd
from pathlib import Path

VIS_PATH = "/Users/rohith.devarasetty/Documents/Cursor/tvScientific Incrementality Test/Visitor data 0526.csv"
GEO_PATH = "/tmp/tvsci/Gma_Geocid_US.csv"
OUT_PATH = "/tmp/tvsci/Visitors_by_DMA_0526.csv"

# ---- Load visitor file -----------------------------------------------------
# 4-line "#" preamble + 1 blank line + header row (line 7) + "Grand total" row (line 8).
# The Grand total row has 6 fields where the header only has 5 — pandas would otherwise
# shift it into an unnamed index, misaligning every column. Skip it explicitly.
vis = pd.read_csv(VIS_PATH, skiprows=[0,1,2,3,4,5,7], low_memory=False)
print(f"raw visitor rows: {len(vis):,}")
print("columns:", list(vis.columns))

# Defensive dropna in case of any remaining stray rows
vis = vis.dropna(subset=["Date", "City", "City ID"]).copy()
print(f"after dropping totals: {len(vis):,}")

# Coerce
vis["Date"] = pd.to_datetime(vis["Date"].astype(int).astype(str), format="%Y%m%d")
vis["City ID"] = vis["City ID"].astype(int)
vis["Total users"] = pd.to_numeric(vis["Total users"], errors="coerce").fillna(0).astype(int)
vis["CTA Tap Count"] = pd.to_numeric(vis["CTA Tap Count"], errors="coerce").fillna(0).astype(int)

print("date range:", vis["Date"].min().date(), "->", vis["Date"].max().date())
print("distinct cities:", vis["City ID"].nunique())
print("total users (sum):", int(vis["Total users"].sum()))
print("total CTA taps (sum):", int(vis["CTA Tap Count"].sum()))

# ---- Load Geocid -> DMA mapping --------------------------------------------
geo = pd.read_csv(GEO_PATH, usecols=["GeoCid", "Gma", "GmaName"])
print(f"\ngeocid -> DMA rows: {len(geo):,}  (distinct GeoCid: {geo['GeoCid'].nunique():,})")

# ---- Merge -----------------------------------------------------------------
merged = vis.merge(geo, left_on="City ID", right_on="GeoCid", how="left")

# Coverage report
mapped = merged["Gma"].notna()
print(f"\nrows mapped:    {mapped.sum():,} / {len(merged):,}  ({mapped.mean()*100:.2f}%)")
print(f"users mapped:   {int(merged.loc[mapped, 'Total users'].sum()):,} / {int(merged['Total users'].sum()):,}  "
      f"({merged.loc[mapped,'Total users'].sum()/merged['Total users'].sum()*100:.2f}%)")
print(f"CTA mapped:     {int(merged.loc[mapped, 'CTA Tap Count'].sum()):,} / {int(merged['CTA Tap Count'].sum()):,}  "
      f"({merged.loc[mapped,'CTA Tap Count'].sum()/merged['CTA Tap Count'].sum()*100:.2f}%)")

# Top unmapped cities by users — sanity-check
unmapped = merged.loc[~mapped].groupby(["City", "City ID"], as_index=False).agg(
    users=("Total users", "sum"), cta=("CTA Tap Count", "sum")).sort_values("users", ascending=False)
print("\nTop 10 unmapped cities by user volume:")
print(unmapped.head(10).to_string(index=False))

# ---- Aggregate to DMA × date -----------------------------------------------
agg = (merged.dropna(subset=["Gma"])
              .assign(Gma=lambda d: d["Gma"].astype(int))
              .groupby(["Date", "Gma", "GmaName"], as_index=False)
              .agg(total_users=("Total users", "sum"),
                   cta_taps=("CTA Tap Count", "sum"),
                   n_cities=("City ID", "nunique")))
agg = agg.rename(columns={"Date": "date", "Gma": "dma_code", "GmaName": "dma_name"})
agg["date"] = agg["date"].dt.strftime("%Y-%m-%d")
agg = agg.sort_values(["date", "dma_code"])

print(f"\noutput rows: {len(agg):,}  (distinct dates: {agg['date'].nunique()}, distinct DMAs: {agg['dma_code'].nunique()})")
agg.to_csv(OUT_PATH, index=False)
print(f"wrote: {OUT_PATH}  ({Path(OUT_PATH).stat().st_size:,} bytes)")
print("\nSample:")
print(agg.head(5).to_string(index=False))
