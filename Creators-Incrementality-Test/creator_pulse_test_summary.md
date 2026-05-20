# Creator Incrementality Pulse Test — Design Summary

## What We're Testing

We want to measure how much of Chime's enrollment growth is **causally driven by creator spend**, not just correlated with it. The test uses a **pulse design**: pause creator spend for 2–3 weeks (off period), then ramp it up to $2–3M for 2–3 weeks (ramp period). By comparing daily enrollments across the two phases, we get a clean read on creator incrementality.

---

## Test Structure

| Phase | Duration | Creator Spend | Role |
|---|---|---|---|
| Pre-period | Jan 5 – Apr 19, 2026 | ~$700K/month (current) | Baseline validation only |
| Off period | ~2–3 weeks (June) | **$0** | Clean counterfactual |
| Ramp period | ~3 weeks (June–July) | **$3M** | Primary measurement |

**Why the off period matters:** The pre-period baseline already has creator spend baked in (~$700K/month). Turning creators off first gives us a clean $0-spend floor. Every enrollment above that floor during the ramp is then directly attributable to creators — no need to subtract any embedded contribution.

**Statistical design:** Two-sample t-test on daily enrollment means — off-period days vs ramp-period days. National scope, all DMAs included.

---

## Baseline Validation

The 2026 observed daily enrollment rate from the data closely matches the tool:

| Source | Daily Enrollments (μ) | Daily CV |
|---|---|---|
| CSV (all DMAs, 2026 YTD) | **19,866** | ~10% |
| Power calculator tool | 19,500 | 11% |

The two baselines are consistent. We use **μ = 19,500/day, CV = 11%** for the power analysis.

---

## Power Analysis

**Assumptions:**
- Significance level α = 10%
- Target power = 70%
- iCPE = $100/enrollment
- Baseline: 19,500 enrollments/day (no-spend floor)
- CV: 11% daily

### Days needed to detect a given lift

| Lift | Signal/day | Days needed | Budget implied |
|---|---|---|---|
| 5% | 975 | 46 days | $4.5M |
| 7% | 1,365 | 24 days | $3.3M |
| **8%** | **1,560** | **18 days** | **$2.8M** |
| 10% | 1,950 | 12 days | $2.3M |
| 12% | 2,340 | 8 days | $1.9M |

### Budget constraint — given $3M ramp at iCPE=$100

| Budget | Duration | Implied lift | Power | Verdict |
|---|---|---|---|---|
| $3M | 14 days | 11.0% | **84%** | ✓ Comfortably powered |
| **$3M** | **21 days** | **7.3%** | **~70%** | **✓ At target threshold** |
| $3M | 28 days | 5.5% | 59% | ✗ Underpowered |
| $2M | 14 days | 7.3% | 55% | ✗ Underpowered |
| $2M | 21 days | 4.9% | 42% | ✗ Underpowered |

---

## Recommendation

**$3M ramp over 3 weeks (21 days)** is the recommended design. It implies a 7.3% enrollment lift vs the off-period baseline and achieves ~70% power — right at the target threshold.

If flexibility exists on the budget, **$3M over 2 weeks** is the more robust option (84% power) and provides a cleaner, faster read.

**$2M is not sufficient** at any practical ramp duration — it tops out at 55% power over 2 weeks, which is well below the 70% target.

---

## Important Design Notes

1. **Not a geo test.** Creators run nationally, so this is a time-based pulse — not a DMA-split experiment. The off period serves as the control condition.

2. **Pre-period is for baseline validation only.** It includes embedded creator spend (~$700K/month → ~2–3% of observed enrollments). Do not use pre-period vs ramp as the primary comparison — use **off period vs ramp**.

3. **Budget math:** Budget = incremental enrollments × iCPE = MDE × μ × days × $100. This is the cost to generate the measured lift, not the total media spend ceiling.

4. **The $2.9M figure** from the power calculator = 8% × 19,500 × 18 days × $100. That scenario (18-day ramp, 8% MDE) requires $2.81M to be fully powered — consistent with the $3M / 3-week recommendation.

5. **Update dates before launch.** The off/ramp period dates in `creator_pulse_test.py` are placeholders. Once the test is scheduled, update `OFF_PERIOD_START`, `OFF_PERIOD_END`, `RAMP_PERIOD_START`, and `RAMP_PERIOD_END` in the CONFIG block to get the actual trend and lift charts.

---

## Open Questions

- What is the expected iCPE for creators? Analysis uses $100 — if the true number is higher, the test becomes harder to power at $3M.
- Will any other major campaigns be running concurrently during the off/ramp window? Concurrent spend changes would confound the off-period counterfactual.
- Is there a minimum off-period duration before the ramp? A full 2–3 week pause ensures the enrollment series has time to settle to the organic floor before the ramp begins.
