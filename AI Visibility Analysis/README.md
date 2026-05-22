# AI Visibility → Direct Traffic & Enrollments — Regression Analysis

## What This Is
Multivariate OLS regression measuring the impact of Chime's AI visibility score (from Profound) on daily direct visits and direct enrollments. Built to quantify whether higher AI presence in LLMs (ChatGPT, etc.) drives incremental direct channel conversions.

## Data
- **Source:** Google Sheet — daily grain pulled from Profound (AI visibility), Looker (visits/enrollments), and internal paid dashboards (brand/NB spend)
- **Period:** June 1, 2025 – January 12, 2026 (226 raw rows → 206 after outlier removal and lag creation)
- **Outlier removal:** IQR method (1.5× IQR) applied to direct visits, direct enrollments, and brand spend. 17 rows removed — mostly month-start direct deposit spikes (Sep 1, Oct 1, Nov 1, Dec 1) and a paid spend anomaly on Oct 20.

## Models Built
8 models total across two dependent variables × with/without unemployment rate × contemporaneous/lagged:

| Model | Dependent Var | UE Rate | Lag | R² |
|---|---|---|---|---|
| A | Direct Visits | Yes | No | 0.533 |
| B | Direct Enrollments | Yes | No | 0.464 |
| C | Direct Visits | Yes | t-1,2,3 | 0.542 |
| D | Direct Enrollments | Yes | t-1,2,3 | 0.479 |
| E | Direct Visits | No | No | 0.524 |
| F | Direct Enrollments | No | No | 0.462 |
| G | Direct Visits | No | t-1,2,3 | 0.533 |
| H | Direct Enrollments | No | t-1,2,3 | 0.476 |

**Independent variables:** AI visibility score, brand spend ($K), NB spend ($K), weekend flag, month seasonality (sin/cos). Robust standard errors (HC3) used throughout.

## Key Findings
- **AI visibility:** Positive direction across all specs (~+400–700 daily visits, ~+3–7 daily enrollments per +1pt score) but **not statistically significant** (p~0.14–0.36). Signal is real but noisy.
- **Root cause of weak signal:** AI visibility score trended downward monotonically Jun→Nov (55→33), making it hard to disentangle from seasonal effects with only 8 months of data. Need more score variation.
- **Unemployment rate:** Added as external control. Directionally positive for visits, negative for enrollments — but VIF=16 due to collinearity with seasonal terms. Not recommended as a control until longer time series is available.
- **Strongest drivers:** Weekend effect (−24K visits / −452 enrollments, p<0.001) and NB spend (+276 visits per $1K, p<0.001).
- **Brand spend:** No independent effect on the direct channel in any model.

## Output Files
| File | Description |
|---|---|
| `regression_analysis.py` | Full analysis script — re-run to reproduce all results |
| `regression_data.csv` | 206-row clean dataset with fitted values + residuals for all 4 contemp models |
| `regression_coefficients.csv` | All 8 models × all variables: coef, std err, t, p, CI, significance |
| `outliers_removed.csv` | The 17 flagged outlier rows with dates and values |
| `regression_results.png` | 9-panel diagnostic chart |
| `regression_summary.txt` | Full statsmodels output for all 8 models |

## Next Steps (Q3 revisit)
1. **Extend the dataset** — pull data through Q2/Q3 2026 to get more AI score variation and a longer time series
2. **Add brand search clicks** (GSC) as a mediator variable to test AI → brand demand → direct path
3. **Consider weekly grain** instead of daily to reduce noise and autocorrelation (Durbin-Watson ~0.9 suggests serial correlation in daily data)
4. **HDYHAU validation** — cross-reference modeled AI effect against self-reported "How did you hear about us" ChatGPT responses
5. **Revisit unemployment rate** once 18+ months of data available — currently too collinear with seasonality to be useful

## To Resume This Analysis
Open Claude Code in this folder and say: *"Resume the AI visibility regression analysis — read the README and regression_analysis.py to get context."*
