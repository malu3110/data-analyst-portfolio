# Cross-Border Truck Wait Monitor — Requirements

| | |
|---|---|
| **Author** | Rose |
| **Version** | 0.1 (draft, written before any code) |
| **Date** | 2026-10-01 |
| **Status** | Draft — data sources pending live verification (see §9) |

> **About this document.** This is a personal portfolio project. There is no
> client, no sponsor, and no stakeholders were interviewed. Everything below is
> a **design exercise**: *if this were a real product, here is who would use it,
> why, and how we would know it worked.* Personas are hypothetical archetypes
> built from publicly described cross-border trucking practice and general
> logistics-domain knowledge, not from requirements gathered from real people.
> Where a statement is an assumption, it is labelled as one.

---

## 1. Problem statement

US Customs and Border Protection (CBP) publishes an estimated wait time for
commercial trucks at each land port of entry on the US–Mexico and US–Canada
borders, refreshed roughly hourly. That feed is a **snapshot**: each update
overwrites the last, and CBP's public feed exposes no history.

As a result, anyone planning a cross-border truck move can see *how long the
queue is right now*, but cannot easily answer the questions that actually
drive planning:

- *What is the wait typically like at the hour my truck will arrive?*
- *Is a nearby crossing usually faster?*
- *How much time does the FAST (trusted-shipper) lane actually save here?*
- *Which crossings are unpredictable, so I should pad the ETA?*

**Problem statement:** Cross-border dispatchers and transportation planners
choose crossings and set ETAs using a point-in-time wait estimate and habit,
because no accessible history of commercial border wait times exists. This
leads to avoidable delay, padded or missed delivery windows, and no learning
from past crossings.

**Proposed solution (this project):** a scheduled pipeline that captures CBP's
hourly commercial-lane snapshot into a database, so history accumulates over time.
It cleans and models that history and publishes a dashboard showing current
waits next to typical waits by crossing and hour. Long-run monthly truck
volumes from the Bureau of Transportation Statistics (BTS) give context on
which crossings matter most.

## 2. Business context

- **Why the border matters to freight.** A large share of US–Mexico trade moves
  by truck through a handful of land ports (for example Laredo, Otay Mesa,
  El Paso area crossings), and US–Canada truck freight is concentrated at
  crossings such as Detroit and Buffalo. A border delay pushes back every
  downstream appointment: dock times, driver hours-of-service, and delivery windows.
- **Nearshoring** of manufacturing to Mexico has increased attention on
  northbound truck capacity and border reliability. *(Context, not a claim
  this project measures.)*
- **FAST lanes** are dedicated lanes for carriers, importers and drivers
  enrolled in CBP's trusted-trader programmes (FAST / C-TPAT). Whether
  enrolment is "worth it" at a given crossing is a real business question that
  wait-time history can inform.
- **Personal link:** I spent two years on a US logistics client's ground
  shipment platform. This project extends that domain into the analytics and
  data-engineering side. It does **not** claim cross-border dispatch experience.

## 3. Stakeholder map and personas

### 3.1 Stakeholder map (hypothetical)

| Stakeholder | Role relative to product | Interest | Influence | Engagement strategy (if real) |
|---|---|---|---|---|
| Cross-border dispatcher (carrier) | **Primary user** | High | Medium | Co-design the "now vs typical" view; usability test |
| Transportation planner / logistics manager (shipper) | **Primary user** | High | High | Owns lane strategy; reviews weekly reliability view |
| Operations / network analyst | Secondary user | High | Medium | Uses CSV export and marts for own analysis |
| Customer service / account manager | Secondary user | Medium | Low | Consumes ETA buffers indirectly |
| Truck drivers | Affected, not a user | High | Low | Benefit from better crossing choice; no direct UI |
| Receivers / consignees | Affected, not a user | Medium | Low | Receive more realistic ETAs |
| CBP (data publisher) | Data provider | Low | High (can change or remove the feed) | Respect terms; monitor for schema changes |
| BTS (data publisher) | Data provider | Low | Medium | Same |
| Hiring manager / reviewer | Actual audience of this portfolio | — | — | README, requirements doc, live dashboard |

Power/interest summary: **manage closely** = planner; **keep satisfied** =
data publishers (the product dies if the feed changes); **keep informed** =
dispatcher, analyst; **monitor** = customer service, drivers, receivers.

### 3.2 Personas (hypothetical archetypes)

**P1 — "Dispatcher Dana", cross-border carrier dispatcher**
- Runs 20–40 northbound loads a day for a mid-size carrier crossing at the
  Laredo-area ports.
- *Goal:* get trucks across and to their delivery appointments on time.
- *Today (assumed):* checks the CBP site for the usual crossing before release
  and relies on driver phone calls when queues are long.
- *Frustration:* "The site tells me what it's like now, not what it'll be like
  in three hours when my driver gets there."
- *Needs:* current vs typical wait for candidate crossings at the planned
  arrival hour, with an obvious freshness indicator.

**P2 — "Planner Priya", transportation planner at a manufacturer with Mexican plants**
- Sets lane strategy and carrier requirements and reports on on-time delivery.
- *Goal:* reliable transit times; justify or reject FAST/C-TPAT investment.
- *Needs:* weekly view of which crossings are slow or unpredictable, and the
  measured standard-vs-FAST difference.

**P3 — "Analyst Alex", operations analyst**
- *Goal:* blend border waits with internal shipment data.
- *Needs:* clean, documented, downloadable data with clear definitions.

## 4. User stories and acceptance criteria

Priority uses MoSCoW. "Release" maps to the build plan: **D1** = day-one base,
**W1** = week-one extensions.

| ID | Story | Priority | Release |
|---|---|---|---|
| US-01 | Current commercial waits by crossing | Must | D1 |
| US-02 | Data freshness is always visible | Must | D1 |
| US-03 | Missing data is never shown as zero | Must | D1 |
| US-04 | Pipeline captures every hourly snapshot exactly once | Must | D1 |
| US-05 | Long-run truck volume context (BTS) | Should | D1 |
| US-06 | Typical wait by hour of day | Must | W1 |
| US-07 | Compare crossings within the same port area | Should | W1 |
| US-08 | Standard vs FAST lane difference | Should | W1 |
| US-09 | Stale-reading detection | Should | W1 |
| US-10 | Pipeline failure is noticed | Should | W1 |
| US-11 | Download modelled data | Could | W1 |

---

**US-01 — Current commercial waits**
*As a dispatcher, I want to see the current commercial wait at each crossing on
a chosen border so that I can decide where to send a truck.*
- **Given** at least one snapshot has been loaded,
  **when** I open the dashboard and select the US–Mexico border,
  **then** I see one row per crossing with commercial lanes, showing standard
  lane delay (minutes), FAST lane delay (minutes), lanes open, port status,
  and CBP's reported update time.
- **Given** a crossing has no commercial lanes,
  **when** the table renders,
  **then** that crossing is excluded rather than shown with blanks.

**US-02 — Freshness visible**
*As a dispatcher, I want to know how old the data is so that I don't act on
stale numbers.*
- **Given** the most recent successful load is more than 2 hours old,
  **when** I open the dashboard,
  **then** a warning banner states the time of the last successful load.
- **Given** any row,
  **then** both CBP's reported update time and our capture time are shown, in a
  stated time zone.

**US-03 — Missing ≠ zero**
*As a planner, I want missing readings shown as missing so that I don't
mistake "not reported" for "no wait".*
- **Given** CBP reports a lane as closed or the delay as blank,
  **when** it is stored and displayed,
  **then** it is stored as NULL with a status reason and displayed as
  "Not reported" or "Closed", never as 0.
- **Given** summary statistics are computed,
  **then** NULL readings are excluded from averages and medians, and the
  count of included readings is shown.

**US-04 — Exactly-once capture**
*As the data owner, I want each CBP snapshot stored exactly once so that
history is complete and not double-counted.*
- **Given** the scheduled job runs twice against the same CBP update,
  **when** both runs load,
  **then** only one row exists per crossing × lane type × CBP update time
  (enforced by a unique key, verified by a dbt test).
- **Given** a scheduled run is skipped,
  **then** the gap is visible in a run-log table (expected vs actual runs).

**US-05 — Volume context**
*As a planner, I want to see long-run monthly truck crossings by port so that I
focus on the crossings that carry the most freight.*
- **Given** BTS monthly data has been loaded,
  **when** I open the "Volume" view,
  **then** I see the top ports by inbound truck crossings for the latest
  available 12 months and a monthly trend line for a selected port.
- **Then** the latest BTS month is labelled, since BTS data lags by months.

**US-06 — Typical wait by hour**
*As a dispatcher, I want the typical wait at a crossing for a given hour of day
so that I can plan for when the truck will actually arrive.*
- **Given** a crossing and an hour of day,
  **when** at least 5 non-null readings exist for that crossing and hour,
  **then** the median and the observed min–max range are shown with the
  reading count *n*.
- **Given** fewer than 5 readings exist,
  **then** the cell reads "Insufficient history (n = x)" instead of a number.
- *Note:* with about a week of history, only hour-of-day patterns are
  supportable. Hour-of-week and P90 buffers need several weeks (see §7).

**US-07 — Compare nearby crossings**
*As a dispatcher, I want to compare crossings in the same port area side by
side so that I can choose the faster one.*
- **Given** I select a port area (CBP port name, e.g. "Laredo"),
  **when** the comparison view loads,
  **then** each crossing in that area shows current wait and typical wait for
  the selected hour, sorted by current wait.

**US-08 — FAST vs standard**
*As a planner, I want the measured difference between standard and FAST lane
waits per crossing so that I can judge the value of FAST enrolment.*
- **Given** a crossing reports both lane types,
  **when** I view the FAST comparison,
  **then** I see the median of (standard − FAST) over paired readings at the
  same CBP update, with the pair count.
- **Given** a crossing has no FAST lane,
  **then** it is listed as "No FAST lane" and excluded from the comparison.

**US-09 — Stale readings**
*As an analyst, I want readings flagged when CBP's update time hasn't changed
so that frozen values don't distort statistics.*
- **Given** a crossing's CBP update time has not advanced for 3 or more
  consecutive captures,
  **then** those readings are flagged `is_stale = true` and excluded from
  typical-wait statistics.

**US-10 — Failure noticed**
*As the data owner, I want to be told when ingestion fails so that I can fix it
before history is lost.*
- **Given** an ingestion run errors (HTTP failure, schema change, DB error),
  **then** the job exits non-zero, which marks the scheduled workflow run as
  failed and triggers the platform's failure notification, and
  the raw response is not partially loaded.

**US-11 — Download**
*As an analyst, I want to download the modelled data shown in the dashboard as
CSV so that I can combine it with my own data.*
- **Given** any table view,
  **when** I click "Download CSV",
  **then** I receive the rows currently filtered, with column definitions
  documented in the README / data dictionary.

## 5. Process flows (for swimlane diagram)

The diagrams are in [`process-flow.drawio`](process-flow.drawio) (two pages:
As-Is and To-Be; open at app.diagrams.net). Static previews:
[as-is](diagrams/as-is.svg), [to-be](diagrams/to-be.svg). Both are generated
by `diagrams/build_process_flow.py`. The **as-is** flow is an *assumed* process for a design
exercise, based on how the public CBP tool is designed to be used. It is not an
observed process.

### 5.1 As-is (assumed)

| # | Lane | Step |
|---|---|---|
| 1 | Customer (shipper) | Tenders cross-border load with delivery window |
| 2 | Dispatcher | Assigns driver; picks crossing, usually the habitual default |
| 3 | Dispatcher ↔ CBP website | Checks current wait for that one crossing (snapshot only) |
| 4 | Driver | Drives to crossing; joins commercial queue |
| 5 | Driver | *Decision:* queue much longer than expected? |
| 6a | Dispatcher | Yes → driver phones in; dispatcher revises ETA manually |
| 7a | Customer | Receives reactive, late ETA change (phone/email) |
| 6b | Driver | No (or after the wait) → crosses, continues to delivery |

**Pain points**
- **PP1.** Snapshot only: no view of what the wait will be at the arrival hour.
- **PP2.** Crossing chosen by habit, not by comparing alternatives.
- **PP3.** Delays aren't recorded, so the organisation never learns which crossings are unreliable.
- **PP4.** ETA changes are reactive and phone-driven.

### 5.2 To-be (proposed)

| # | Lane | Step |
|---|---|---|
| 1 | Data pipeline | Hourly: fetch CBP snapshot (scheduled) |
| 2 | Data pipeline | Store raw snapshot in Postgres (idempotent) |
| 3 | Data pipeline | Transform: clean, flag stale/missing, compute hourly patterns |
| 4 | Dashboard | Shows current + typical wait by crossing and hour, freshness banner |
| 5 | Customer | Tenders load with delivery window |
| 6 | Dispatcher | Compares candidate crossings for planned arrival hour (dashboard) |
| 7 | Dispatcher | Chooses crossing; sets ETA including border buffer |
| 8 | Driver | Crosses at chosen crossing |
| 9 | Customer | Receives ETA that already accounts for the border |
| 10 | Planner | Weekly: reviews crossing reliability and FAST savings |

**Design principle:** the dashboard *informs* the decision. The dispatcher
still owns it. No automated routing (see §7).

Pain point → requirement traceability: PP1 → US-06; PP2 → US-07; PP3 → US-04,
US-06, US-09; PP4 → US-06 (buffer input; automated customer notification is
out of scope).

## 6. Success metrics

Two tiers, kept separate on purpose:

**6.1 Product outcome metrics (hypothetical; cannot be measured in a
personal project).** If this were a real product, success would be measured by:
- Reduction in average border dwell per load vs a pre-adoption baseline
- Delivery-window adherence for cross-border loads
- Share of ETA revisions made *before* dispatch vs after the truck is queued
- Weekly active dispatchers / planners

I will not claim any of these were achieved.

**6.2 Project delivery metrics (measured and reported in the README).**

| Metric | Target | Measured by |
|---|---|---|
| Scheduled ingestion success rate over the first full week | ≥ 95% of expected hourly runs | run-log table |
| Data freshness at random check | latest load < 2 h old in ≥ 90% of checks | run-log vs clock |
| Duplicate snapshot rows | 0 | dbt `unique` test |
| dbt tests passing on main | 100% | CI / `dbt build` |
| Commercial crossings covered | all crossings CBP reports with commercial lanes | count vs source |
| Dashboard first load | < 5 s on a warm app | manual check |
| Hours of history at end of week 1 | ≥ 150 | row timestamps |

## 7. Scope

**In scope**
- Northbound (into the US) commercial truck waits, standard and FAST lanes,
  both borders, from CBP's public feed
- Monthly inbound truck crossings by port from BTS, as volume context
- Scheduled ingestion → Postgres → dbt models → public Streamlit dashboard
- Data quality handling: missing, closed, stale, duplicate

**Explicitly out of scope**
- **Southbound** waits into Mexico/Canada (not in CBP's feed)
- Passenger vehicle and pedestrian lanes
- **Forecasting / prediction** of future waits. One week of history can't
  support it honestly. It's a candidate once months have accumulated.
- Hour-of-week patterns and P90 buffers (need several weeks of history; the
  to-be flow's "buffer" uses median and range until then)
- Automated routing, ETA calculation to the border, or customer notifications
- Integration with any TMS or carrier system
- Users, login, alerts to end users
- Sub-hourly capture (the source updates about hourly)
- Customs documentation, brokerage, or inspection outcomes

## 8. Assumptions

- **A1.** CBP's feed remains public, free, unauthenticated, and permitted for
  programmatic use. *(To verify — §9.)*
- **A2.** CBP's estimate (time to reach primary inspection) is an acceptable
  proxy for border delay. It is an estimate, and measurement methods may differ by port.
- **A3.** CBP updates each crossing about hourly; hourly capture is sufficient.
- **A4.** CBP's update times are expressed in the port's local time zone and
  must be normalised to UTC. *(To verify — this affects every hourly statistic.)*
- **A5.** BTS monthly Border Crossing Entry Data remains available via its open
  data API; its truck counts are inbound only and lag by some months.
- **A6.** Free-tier hosting (GitHub Actions, a hosted Postgres free tier,
  Streamlit Community Cloud) is sufficient. Volume is roughly 100–200 crossings × 24
  captures/day, i.e. thousands of rows a day.
- **A7.** The as-is process in §5.1 reflects typical practice. If this were real,
  it would be validated through user interviews before build.

## 9. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Data sources not yet verified live** (network blocked during scoping) | — | High | **Gate:** verify endpoints, fields and freshness before Day 1 build; switch to Option B (IMF PortWatch) if CBP is unusable |
| R2 | CBP changes or removes the feed / schema | Low–Med | High | Store raw JSON; schema check fails loudly (US-10) |
| R3 | Scheduled runs delayed or skipped (GitHub cron is best-effort) | Med | Med | Dedupe on CBP update time; run-log gap report |
| R4 | Short history (~1 week) → weak patterns | Certain | Med | Minimum-n rules (US-06), honest labelling; keep pipeline running |
| R5 | Many NULL / closed / stale readings | Med | Med | US-03, US-09; report % usable readings |
| R6 | Time-zone errors (multiple zones, DST) | Med | High | Normalise to UTC at staging; dbt test on hour distribution |
| R7 | Free-tier DB sleeps or hits limits | Med | Low | Small data volume; cold-start tolerated; document |
| R8 | GitHub disables scheduled workflows after 60 days of repo inactivity | High (long-term) | Med | Note in README; periodic commit or re-enable |
| R9 | Users read "typical wait" as a prediction | Med | Med | UI copy: "observed history, not a forecast"; show *n* |
| R10 | Overstating the project in interviews | — | High | §6 separates measured from hypothetical; this disclaimer |

## 10. Data sources

| Source | Content | Access | Cadence | Verified? |
|---|---|---|---|---|
| CBP Border Wait Times API (`bwt.cbp.gov/api/bwtnew`) | Current wait, lanes open, status per crossing and lane type | Public JSON, no key | ~Hourly | **Not yet** (blocked during scoping) |
| BTS Border Crossing Entry Data (`data.bts.gov`, dataset `keg4-3bc2`) | Monthly inbound crossings by port and measure (e.g. Trucks) | Socrata open-data API | Monthly, lagged | **Not yet** |

## 11. Glossary

- **Port of entry / crossing:** CBP groups crossings under a port (e.g. port
  "Laredo" has several bridges). This project uses CBP's naming.
- **Primary inspection:** the first CBP booth. CBP's wait estimate is the
  time to reach it.
- **FAST:** Free and Secure Trade. Dedicated commercial lanes for enrolled
  carriers/drivers shipping for C-TPAT importers.
- **C-TPAT:** Customs Trade Partnership Against Terrorism, CBP's
  supply-chain security programme.
- **Snapshot:** a single read of CBP's current-state feed.
- **Median / range / n:** the summary statistics shown for typical waits.
  *n* is the number of non-null, non-stale readings behind them.
