# Cross-Border Truck Wait Monitor

**Live dashboard:** _link added once deployed — see [docs/deployment.md](docs/deployment.md)_
· **Requirements:** [docs/requirements.md](docs/requirements.md)
· **Process flows:** [docs/process-flow.drawio](docs/process-flow.drawio)

## The business problem

A truck crossing from Mexico or Canada into the US can lose minutes or hours at the
border, and that delay pushes back every appointment after it. US Customs and Border
Protection (CBP) publishes an estimated wait for commercial trucks at each land port,
refreshed about hourly, but **only as a live snapshot. CBP's public feed keeps no history.**

So someone planning a cross-border move can see how long the queue is *right now*,
but not the things that actually drive planning:

- What is the wait *typically* like at the hour my truck will arrive?
- Is a nearby crossing usually faster?
- How much time does the FAST (trusted-shipper) lane really save here?

This project builds the missing history. A scheduled pipeline captures CBP's feed every
hour, cleans and models it, and serves a dashboard that puts the current wait next to
the observed typical wait by crossing and hour, with monthly truck volumes from the
Bureau of Transportation Statistics (BTS) for context.

> **Scope note.** This is a personal portfolio project. The users, stakeholders and
> requirements in the docs are a *design exercise* ("if this were a real product, who
> would use it and why"), not requirements gathered from real people. The dashboard
> shows observed history, not a forecast.

## Who it's for (hypothetical personas)

| Persona | Decision it supports |
|---|---|
| Cross-border dispatcher | Which crossing to send a truck to, and what ETA buffer to give |
| Transportation planner (shipper) | Which crossings are unreliable; is FAST/C-TPAT enrolment worth it |
| Operations analyst | Clean, documented history to combine with internal shipment data |

Full stakeholder map, user stories with Given/When/Then acceptance criteria,
as-is/to-be swimlanes, success metrics, scope, assumptions and risks:
**[docs/requirements.md](docs/requirements.md)**.

## What the data showed on day one

Both sources were verified live from GitHub Actions before any pipeline code was
written ([verify-sources workflow](.github/workflows/verify-sources.yml)). One real
snapshot (2026-10-01, about 09:12 UTC, overnight in North America) shows why the cleaning
layer matters:

- CBP lists **85 crossings; 53 have commercial lanes** (28 US–Mexico, 25 US–Canada).
- Of the **106 commercial lane readings** (standard + FAST), only **21 carried a number**.
  The rest were "Update Pending" (40), "Lanes Closed" (23) or "N/A" (22).
- **11 of those 21 numbers were left over from the previous day.** CBP writes update
  times as `"At 6:00 am EDT"` with no date, so a naive parser would present yesterday's
  "0 minutes" as current. Only **10 readings (9%) were fresh and usable.**
- BTS shows how concentrated the freight is: **Laredo handled ~2.97 million inbound
  trucks** in the 12 months to August 2026, about 3× the next US–Mexico port
  (Otay Mesa, ~0.99 million).

Typical-wait-by-hour figures need history, so they fill in as the hourly pipeline runs.
The dashboard says "insufficient history (n = x)" until each crossing-hour has at
least 5 fresh readings, rather than showing a misleading number.

## How it works

```
GitHub Actions (cron)               Postgres (Neon)                          Streamlit Community Cloud
hourly  ─ ingest CBP ─ raw JSON ─▶  raw.cbp_snapshot   ─┐
weekly  ─ ingest BTS ─ rows ─────▶  raw.bts_truck_crossing ─┼─ dbt ─▶ staging.* ─▶ marts.* ─▶ dashboard
every run ─ run log ─────────────▶  raw.pipeline_run   ─┘
```

| Layer | What it does | Where |
|---|---|---|
| Ingestion | Fetches with retries, validates the schema (fails loudly if CBP changes a field), stores the **untouched** JSON; identical payloads stored once (SHA-256) | [`pipeline/`](pipeline) |
| Raw storage | Postgres `raw` schema: snapshots, BTS rows, a run log of every success/failure | [`pipeline/sql/schema.sql`](pipeline/sql/schema.sql) |
| Transformation | dbt: flatten JSON, infer the date of each CBP update and convert to UTC, keep missing values NULL with a reason, flag stale readings, dedupe, build marts | [`transform/`](transform) |
| Tests | 15 pytest tests on real captured payloads; 24 dbt data tests; a dbt unit test for the date-inference edge cases (yesterday's reading, a reading taken before local midnight and captured after it) | [`tests/`](tests), [`transform/`](transform) |
| Scheduling | GitHub Actions: hourly CBP + dbt build, weekly BTS, CI on every push | [`.github/workflows/`](.github/workflows) |
| Dashboard | Streamlit + Altair, reads only the marts | [`app/streamlit_app.py`](app/streamlit_app.py) |

### Data-quality decisions (and why)

| Decision | Reason | Story |
|---|---|---|
| Missing is never zero: "Update Pending" / "Closed" stay NULL with a status | A closed lane is not a 0-minute wait | US-03 |
| Reading date inferred from capture time; future times roll back a day | CBP update times have no date | US-02, US-09 |
| Readings older than 2 h flagged stale and excluded from statistics | Frozen values would drag medians toward old data | US-09 |
| Same crossing × lane × CBP update time counted once | Hourly re-captures of an unchanged feed must not double-count | US-04 |
| Minimum 5 readings before showing a typical wait | One week of data supports only so much; say so | US-06 |
| Every run logged, success or failure | Missed hours are measured, not guessed | US-04, US-10 |

### Marts

| Model | Grain | Answers |
|---|---|---|
| `mart_current_wait` | crossing | What is the wait now? (US-01) |
| `mart_hourly_profile` | crossing × lane × local hour | What is it typically like at my arrival hour? (US-06) |
| `mart_fast_vs_standard` | crossing | How much does FAST save? (US-08) |
| `mart_truck_volume_monthly` | port × month | Which crossings carry the freight? (US-05) |
| `mart_pipeline_health` | day | Is the capture keeping up; how much data is usable? |
| `dim_crossing` | crossing | Names, border, time zone, BTS port volume |

## Run it locally

Requires Python 3.11+ and a Postgres database.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # edit DATABASE_URL and the PG* values
set -a && . ./.env && set +a

python -m pipeline.ingest_cbp   # capture the current CBP snapshot
python -m pipeline.ingest_bts   # load BTS monthly truck crossings
cd transform && dbt build --profiles-dir . && cd ..
streamlit run app/streamlit_app.py

# tests (use a separate, disposable database)
TEST_DATABASE_URL=postgresql://... python -m pytest
```

For UI work before real history accumulates, `python -m scripts.seed_demo_history`
generates a week of **synthetic** waits from the real snapshot. It refuses to run against
anything but a localhost database, so demo numbers can never reach the deployed dashboard.

## Limitations (stated plainly)

- History starts when the pipeline was switched on. One week supports hour-of-day
  patterns, not weekly seasonality or forecasting.
- CBP's figure is an *estimate* of time to reach primary inspection, reported by each
  port; measurement may differ between ports.
- Northbound (into the US) only. CBP does not publish southbound waits.
- GitHub's scheduler is best-effort: runs can be delayed and occasionally skipped (the
  pipeline-health view reports this), and scheduled workflows pause after 60 days without
  repository activity.
- Success metrics are project-delivery metrics (capture rate, freshness, test pass rate).
  Business outcomes such as reduced dwell time are hypothetical and are not claimed.

## Repository layout

```
docs/          requirements, build plan, deployment guide, swimlane diagrams
pipeline/      ingestion (CBP, BTS), run log, raw schema
transform/     dbt project: staging → intermediate → marts, tests, seeds
app/           Streamlit dashboard (+ its own requirements.txt for Streamlit Cloud)
scripts/       source verification, fixture capture, CI/demo helpers
tests/         pytest suite + real captured source fixtures
```

## Data sources

- **CBP Border Wait Times**: `https://bwt.cbp.gov/api/bwtnew`, public JSON, no key.
- **BTS Border Crossing Entry Data**: `https://data.bts.gov/resource/keg4-3bc2.json`,
  Socrata open-data API, measure = Trucks.

Both are US federal government open data.
