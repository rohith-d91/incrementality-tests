#!/usr/bin/env python3
"""
Pull paid marketing spend by DMA and enrollment date from Snowflake.
Run with:  ! python3 fetch_spend.py
A browser window will open for SSO authentication.
"""

import snowflake.connector
import pandas as pd
import os

OUT_FILE = os.path.join(os.path.dirname(__file__), "dma_paid_spend.csv")

print("Connecting to Snowflake (browser SSO will open)...")
con = snowflake.connector.connect(
    connection_name="chime",
    role="SNOWFLAKE_PROD_ANALYST_OKTA",
    warehouse="ANALYTICS_WH",
    database="edw_db",
    schema="marketing",
)

QUERY = """
SELECT
    v.enrollment_date,
    dma_code,
    SUM(spend) AS paid_spend
FROM edw_db.core.member_details v
JOIN edw_db.marketing.fact_marketing_user_spend m ON v.user_id = m.user_id
JOIN FIVETRAN.GSHEETS.ZIPCODE_TO_DMA z ON z.zip_code = v.zip_code
WHERE TO_DATE(v.enrollment_date) BETWEEN '2025-02-20' AND '2026-05-19'
  AND m.traffic_source = 'paid'
GROUP BY ALL
ORDER BY 1, 2 ASC
"""

print("Running query...")
cur = con.cursor()
cur.execute(QUERY)
rows = cur.fetchall()
col_names = [d[0].lower() for d in cur.description]

df = pd.DataFrame(rows, columns=col_names)
print(f"  Fetched {len(df):,} rows across {df['dma_code'].nunique()} DMAs")
print(f"  Date range: {df['enrollment_date'].min()} → {df['enrollment_date'].max()}")
print(f"  Total paid spend: ${df['paid_spend'].sum():,.2f}")
print(df.head(10).to_string(index=False))

df.to_csv(OUT_FILE, index=False)
print(f"\nSaved to: {OUT_FILE}")

cur.close()
con.close()
