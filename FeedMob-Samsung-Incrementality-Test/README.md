# FeedMob × Samsung CTV Incrementality Test

PSA-controlled incrementality test measuring the impact of **Samsung Ads CTV** (run through **FeedMob**) on Chime enrollments. Ran **2026-07-07 → 2026-07-29** (ended ~1 week early once the lift was clearly significant and to stop the test inflating Samsung's July CAC). Companion read: [`METHODOLOGY.md`](METHODOLOGY.md).

> **Status: PRELIMINARY.** Enrollment lift and iCPE are validated on Chime-internal member matches; the app-enroll count reconciliation (AppsFlyer vs FeedMob tracker) and P360 fraud treatment are still being confirmed (see Open items).

## Design (locked ~2026-07-02 with Samsung / FeedMob)

- **Type:** PSA-controlled, **device (PSID)-level** randomization across all DMAs (not a geo test).
- **Split:** **80% Test** (Chime ads) / **20% Control** (neutral PSA "house" ads) → traffic ratio **4:1**.
- **Budget:** $300K total ($270K Test / $30K Control). Evergreen Samsung BAU ($550K) is separate/mutually exclusive.
- **Primary KPI:** enrollments (app + web). Direct deposits (DDs) = directional read only.
- **Success bar:** **5–10% enrollment lift.** iCPE benchmark **$300–600** (originally <$200 in the design doc; revised on 7/2 as unrealistic for CTV — anchored on the 5–10% lift instead).
- **Attribution:** app VT 24h / AF equal-attribution 1h; web VT 3-day. Standard readout excludes overlapping IPs (Samsung prior 3%; actual ~5%).

## Headline results (full test, preliminary)

| Metric | Result | Benchmark |
|---|---|---|
| **iCPE** | **~$110–115** | $300–600 — well below (strong) |
| **Enrollment lift** (Test vs PSA control) | **~+100%** (99% tracker-corrected → 116% tracker as-is) | 5–10% — far exceeded |
| Statistical significance | Yes (p < 0.001) | — |
| Direct-deposit (CAC) lift | Not yet readable | too few DDs (~2 wks post-test) |

Delivery verified balanced at **~4:1** on impressions (16.5M : 4.1M), targeted TVs, and impressed TVs (reach rate ~21% each arm). **100% of both web and app enroll user IDs matched Chime members.**

## How enrollments are counted & matched

- **Web enrolls** — FeedMob site pixel. Daily/consolidated logs carry a Chime `user_id`; arm from `click_id` (**23454 = Test, 23453 = Control**); strict CTV-attributed rows are `funnel_category = "Direct - Samsung TV"`.
- **App enrolls** — AppsFlyer, `EDW`/`partner_db.appsflyer.appsflyer`, `event_name = 'successful_enrollment'`, `campaign ILIKE '%Samsung%Test/Control%'`; identity = `customer_user_id` (= Chime `user_id`, 100% populated on enroll events).
- **Match / validation** — both keys joined to `edw_db.core.member_details.user_id`. Web ∩ app overlap is negligible (~11 Test / 0 Control), so app+web is not meaningfully double-counted.

See [`METHODOLOGY.md`](METHODOLOGY.md) for the lift formula, significance test, and the reproduction SQL.

## Data & references

| Item | Location |
|---|---|
| Daily tracker (Lift Calc + Daily Input) | Google Sheet `1Q903HUqQpqx1ZFmsHj5uXsx0vkEXwDKBarZrPy4pvt8` |
| Design doc | Google Doc `1BwMhDl8j3ZufOXN5opTJ4p6d2niiHmzrvZRPCb6qZVc` |
| Enroll / impression logs + consolidated UID file | Drive folder `1GivJKTfzrhMpU5NL_0kUBh--VTVW2HmM` |
| Director one-pager | Google Doc `19dEgCt8w9En-ISmWgaiD8GQsYyvby5PefBC3qwRz4lU` |
| Jira | ALYTACQ-777 (setup), ALYTACQ-986 / 987 (reviews), ALYTACQ-988 (final readout) |
| Discussion / decisions | Slack `#feedmob-chime` |

## Open items (before final readout)

1. **App-enroll reconciliation** — our all-dates AppsFlyer pull (2,037 Test / 258 Control distinct CUID) vs the tracker's windowed app enrolls (1,637 / 191); likely attribution-window/dedup, not fraud.
2. **P360 fraud** — flag rate ended high (~26%); confirm it stays symmetric across arms (per Slack w/ Kelly Baykal, Sally Chi, Alejandra Segovia).
3. **Control-enroll count bug** — the tracker's derived Control app+web total (391) drops the 7/23–24 app enrolls; correct value is 262 app + 163 web = **425** (raises lift denominator, lowers lift from ~116% to ~99%).
4. **Overlap haircut** — tracker still applies the 3% placeholder; actual IP↔PSID overlap is ~5.1%.
5. **DD / CAC read** — ~2 weeks after test end, once direct deposits mature.
