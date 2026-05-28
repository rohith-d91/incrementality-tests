# DMA Reference & ZIP→DMA Validation

## Files

| File | Purpose |
|------|---------|
| `dma_code_reference.csv` | **Canonical Nielsen DMA reference** — 210 entries with code, name, states covered, market-size tier |
| `validate_zipcode_to_dma.py` | Pulls `FIVETRAN.GSHEETS.ZIPCODE_TO_DMA` from Snowflake and audits it against `dma_code_reference.csv` |

## `dma_code_reference.csv` — How It Was Built

| Column | Description |
|--------|-------------|
| `dma_code` | Nielsen 3-digit code (500–881) |
| `dma_name` | Canonical Nielsen market name |
| `states` | Comma-separated US states the DMA spans |
| `tier` | Size tier: `mega` (top 12), `large` (next 17), `medium` (next 34), `small` (rest) |

**Verification sources used:**
1. Nielsen 2024 DMA list (broadcasting reference)
2. The Local Media Database (TLMD)
3. Empirical validation against `May 2025- 2026 Data by DMA.csv` — the top-30 codes by enrollment volume match expected US population/market hierarchy exactly (501=NY, 803=LA, 623=Dallas, ...), and enrollment/TV-HH ratios are consistent within ±2x for all 30 selected DMAs in Design 2's MMT.

**This file should be treated as the source of truth** for DMA code↔name lookups going forward. The bug we hit on 2026-05-26 happened because the hand-built `DMA_NAMES` dict in `balance_design2.py` had drifted from canonical. Always load names from `dma_code_reference.csv`, never inline them.

## What This File Does NOT Contain

This is **NOT a ZIP→DMA mapping** (~42,000 ZIP codes). For that, use one of:

### Option A: Snowflake `FIVETRAN.GSHEETS.ZIPCODE_TO_DMA` (recommended)
Already in your data stack and was verified during the audit to use correct Nielsen codes. Run `validate_zipcode_to_dma.py` periodically to confirm it stays clean.

### Option B: External sources
- **Nielsen direct feed** — gold standard, paid
- **The Local Media Database (TLMD)** — paid, well-maintained
- **SimpleMaps** US ZIP database (free tier has DMA codes — verify against `dma_code_reference.csv`)
- **HUD USPS ZIP↔County crosswalk** + Nielsen DMA↔County mapping (free but requires combining)

### Option C: Build your own
Easier path: write a Snowflake query that joins your data warehouse's address↔ZIP table to a county-level DMA map. But this requires a county↔DMA table to begin with, which isn't included here.

## Using This File in `balance_design2.py`

```python
import pandas as pd
import os

REF = pd.read_csv(os.path.join(BASE_DIR, "dma_code_reference.csv"))
DMA_NAMES = dict(zip(REF["dma_code"], REF["dma_name"]))
```

This replaces the 211-entry inline dict, eliminating the risk that the inline dict drifts from the reference file.

## Running the Validation Script

```bash
python3 validate_zipcode_to_dma.py
```

A browser window will open for Snowflake SSO. The script then checks:

1. **Unknown DMA codes** — codes in the GSheet that aren't in Nielsen
2. **Coverage gaps** — Nielsen DMAs with zero ZIPs mapped
3. **Code↔name mismatches** — wrong labels for known codes
4. **Multi-DMA ZIPs** — ZIPs incorrectly mapped to >1 DMA (should be 1:1)
5. **ZIP-count outliers** — DMAs with suspiciously few or many ZIPs

If any issues are found, they're written to `zipcode_to_dma_audit.csv` for review.

## Quick Reference — DMA Counts

| Tier | Count | Examples |
|------|-------|----------|
| `mega` | 12 | NY, LA, Chicago, Philadelphia, Dallas, Houston, Atlanta, Miami, Boston, Detroit, DC, Phoenix |
| `large` | 17 | Cleveland, Seattle, Tampa, Pittsburgh, Indianapolis, Charlotte, Sacramento, San Diego (after re-tier), etc. |
| `medium` | 34 | Hartford, Tucson, Salt Lake City, Tulsa, Memphis, etc. |
| `small` | 147 | Everything else |

States with the most overlapping DMAs:
| State | # DMAs touching it |
|-------|-------------------|
| TX | 20 |
| CA | 14 |
| MO | 13 |
| MI | 12 |
| OH | 12 |

## Maintenance

If Nielsen releases an updated DMA list (typically annually), update:
1. `dma_code_reference.csv` — replace with the new canonical list
2. Re-run `validate_zipcode_to_dma.py` to catch any GSheet drift
3. Re-run `balance_design2.py` to ensure no Design 2 markets shifted

There is no other place in the repo where DMA names should be hardcoded.
