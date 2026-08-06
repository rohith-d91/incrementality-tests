# FeedMob × Samsung CTV Incrementality — Methodology

One-page reference for the design, lift measurement, and validation. Companion: [`README.md`](README.md).

---

## Goal

Measure the incremental impact of **Samsung Ads CTV** (via FeedMob) on Chime **enrollments** (primary KPI; app + web). Direct deposits are a directional secondary read.

---

## Design — PSA-controlled, device-level

Samsung randomly split its ML-targeted TV devices (**PSIDs**) into two mutually exclusive, non-overlapping groups at a **4:1** ratio:

| Group | Share | Ad content | Budget | Targeted PSIDs |
|---|---|---|---|---|
| **Test** | 80% | Chime evergreen CTV ads | $240K | 13.4M |
| **Control** | 20% | Neutral PSA / house ads ("Love Your Mind") | $60K | 3.36M |

Because assignment is random, any difference in enrollment **rate** between the groups is the incremental effect of the Chime ads. Samsung guarantees the two PSID sets (and their household IPs) are non-overlapping for the test duration.

**Periods:** launched **2026-07-07**; ended **2026-07-29** (~1 week early vs the planned 8/04, on clear significance + to curb July CAC).

---

## Enrollment measurement (app + web)

| Channel | Source | Arm identifier | Identity key |
|---|---|---|---|
| **Web** | FeedMob site pixel (daily/consolidated logs) | `click_id` — **23454 = Test, 23453 = Control**; strict CTV set = `funnel_category = "Direct - Samsung TV"` | Chime `user_id` |
| **App** | AppsFlyer (`partner_db.appsflyer.appsflyer`), `event_name = 'successful_enrollment'`, `campaign ILIKE '%Samsung%Test/Control%'` | campaign name | `customer_user_id` (= Chime `user_id`) |

Both identity keys are joined to `edw_db.core.member_details.user_id`. **100% match** on both channels (web 1,049 Test / 129 Control; app 2,037 / 258 distinct CUID — every ID a real Chime member). Web ∩ app overlap ≈ 11 Test / 0 Control → app+web double-counting is negligible.

> Note: `customer_user_id` is populated on 100% of `successful_enrollment` events; pre-registration events (`Sign_Up_Button_Tapped`, `Enrollment_Submitted`, etc.) have low/no CUID — expected, as no `user_id` exists before registration.

---

## Lift & iCPE

Cumulative Test vs Control enrollments, with Control **scaled up 4×** to form the test-equivalent baseline:

```
Enroll lift %   = ( Test enrolls  −  Control enrolls × 4 )  /  ( Control enrolls × 4 )
iCPE            = Test media spend  /  incremental enrolls
```

Full-test (7/07–7/29), app + web:

| | Test | Control |
|---|---|---|
| App (AF) | 2,078 | 262 |
| Web (pixel) | 1,300 | 163 |
| **Total** | **3,378** | **425** (tracker derived shows 391 — undercounts; see below) |

- **Lift = +99%** using the corrected Control total (425); the tracker shows **+116%** using its derived 391.
- **iCPE ≈ $110–115** (excl. ~5% IP overlap). Test spend ≈ $185K.

---

## Statistical significance

Rate-ratio test on per-impression enrollment rates (Poisson, log scale):

```
z = ln(RR) / sqrt(1/n_test + 1/n_control)
```

`z ≈ 13`, **p < 0.001** — significant even under a conservative ×4 SE inflation for clustering. 95% CI on the lift roughly **+77% to +117%**. Significance was never the binding constraint (large effect, thousands of enrolls); the open questions are *bias/reconciliation*, not detectability.

---

## Validation performed

1. **Delivery balance** — impressions 16.5M : 4.1M = **4.06:1**; targeted TVs **4.00:1**; impressed TVs **4.01:1**; reach rate (impressed/targeted) **~21% in both arms** → no delivery/matching asymmetry.
2. **Identity** — 100% of web + app enroll IDs matched Chime members.
3. **Fraud & funnel symmetry** — P360 flag rate and install→enroll CVR symmetric across arms (so the lift isn't one arm being cleaner).

---

## Known limitations / caveats

1. **Control-count bug** — tracker's derived Control app+web (391) drops the 7/23–24 app enrolls; correct = 262 + 163 = **425**. Undercounting Control inflates the lift (~116% → ~99%). Cross-check: a blended lift cannot exceed *both* its app-only (+114%) and web-only (+103%) parts — it did (116%), confirming the undercount.
2. **App-enroll definition** — all-dates AppsFlyer CUID counts (2,037 / 258) exceed the tracker's windowed app enrolls (1,637 / 191); attribution-window/dedup difference, reconciliation pending.
3. **P360 fraud** — ended ~26% (above the 10% ceiling); symmetric across arms so far, being reconfirmed with FeedMob.
4. **Overlap haircut** — actual IP↔PSID overlap ~5.1% vs the 3% placeholder in the tracker's Lift Calc.
5. **Control power** — reached ~425 enrolls vs the 600 pre-set target; the observed effect is large enough to be significant regardless.
6. **Generalization** — high-intent, ML-targeted Samsung audience; the lift and low iCPE may not hold when scaling to broader inventory.
7. **DD / CAC** — 15 Test / 2 Control DDs → not readable; directional read ~2 weeks post-test.

---

## Reproducing the app-side match

```sql
-- App enrolls by arm, matched to Chime members
SELECT CASE WHEN campaign ILIKE '%Samsung%Test%' THEN 'Test' ELSE 'Control' END AS arm,
       COUNT(DISTINCT af.customer_user_id) AS distinct_cuid,
       COUNT(DISTINCT md.user_id)          AS matched_members
FROM partner_db.appsflyer.appsflyer af
LEFT JOIN edw_db.core.member_details md
  ON md.user_id::varchar = af.customer_user_id::varchar
WHERE (campaign ILIKE '%Samsung%Test%' OR campaign ILIKE '%Samsung%Control%')
  AND event_name = 'successful_enrollment'
GROUP BY 1;
```

Web side: load the FeedMob enroll logs (or consolidated UID file) into a warehouse table and join `user_id → member_details.user_id`; arm via `click_id`.

---

*Owner: Rohith Devarasetty (rohith.devarasetty@chime.com). Preliminary — pending the reconciliation items above.*
