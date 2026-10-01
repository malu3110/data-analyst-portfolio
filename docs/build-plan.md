# Build Plan

Companion to [requirements.md](requirements.md). Story IDs (US-xx) refer to §4 there.

## Architecture

```
 GitHub Actions (cron)                 Postgres (Neon free tier)                    Streamlit Community Cloud
 ─────────────────────                 ─────────────────────────                    ─────────────────────────
 hourly:  ingest CBP  ──raw JSON──▶  raw.cbp_snapshot (jsonb, 1 row/fetch)
 weekly:  ingest BTS  ──rows──────▶  raw.bts_border_crossing
 every run: log run   ────────────▶  raw.pipeline_run
 after ingest: dbt build ─────────▶  staging.*  ──▶  marts.*  ─────────────────▶  dashboard (public URL)
```

**Key design choices (and why)**
- **ELT, raw JSON first.** Ingestion stores CBP's response untouched; all parsing is
  in SQL (dbt). If CBP changes a field, history is not lost and only one model
  changes. (Risk R2.)
- **Idempotent raw load.** Each response is hashed; an identical payload is stored
  once. Staging dedups readings on crossing × lane × CBP update time. (US-04.)
- **Run log table.** Every run writes success/failure, so gaps in scheduling are
  measurable, not guessed. (US-04, US-10, success metrics §6.2.)
- **dbt for transforms + tests.** Uniqueness, not-null, accepted values, and
  freshness are enforced in code, not by eyeballing.
- **Free tier only.** GitHub Actions (public repo), Neon Postgres, Streamlit
  Community Cloud.

## Day 1 — working base (one focused day)

| # | Task | Stories | Est. |
|---|---|---|---|
| 0 | Verify CBP + BTS live; capture real sample payloads as test fixtures | R1 gate | 0.5 h |
| 1 | Repo skeleton, `requirements.txt`, config via env vars | — | 0.5 h |
| 2 | Raw schema + CBP ingest (hash-dedup) + run log; pytest against local Postgres | US-04, US-10 | 2 h |
| 3 | BTS ingest (truck measures, full refresh) | US-05 | 1 h |
| 4 | dbt: staging (flatten, UTC, NULL handling) + `mart_current_wait` + `mart_truck_volume` + tests | US-01, US-03, US-05 | 2 h |
| 5 | Streamlit: current waits + freshness banner + volume view | US-01–03, US-05 | 1.5 h |
| 6 | GitHub Actions: hourly ingest + dbt; weekly BTS; CI tests | US-04 | 0.5 h |
| 7 | Create Neon DB, add secret, deploy Streamlit, README v1 | — | 1 h |

**Day 1 done =** public link shows live current waits and BTS volume, and the hourly
job is accumulating history.

## Week 1 — evenings (≈ 1.5–2 h each)

| Evening | Task | Stories |
|---|---|---|
| 1 | Stale-reading flag; `mart_hourly_profile` with min-n rule | US-09, US-06 |
| 2 | Compare crossings within a port area | US-07 |
| 3 | FAST vs standard paired difference | US-08 |
| 4 | Pipeline health page: expected vs actual runs, % usable readings | US-04, §6.2 |
| 5 | CSV download; data dictionary; screenshots | US-11 |
| 6–7 | Measure §6.2 metrics on real week of data; write findings + limitations into README | — |

> The code for the week-1 marts is written up front (they're small SQL models), but they
> only become *meaningful* as history accumulates. The dashboard shows
> "insufficient history" until the min-n rule is met, so nothing is overstated.

## What I (Rose) must do by hand — needs my accounts

1. Create a free Neon project → copy the connection string.
2. GitHub repo → Settings → Secrets and variables → Actions → add `DATABASE_URL`.
3. share.streamlit.io → New app → this repo, `app/streamlit_app.py` → add `DATABASE_URL` secret.
4. Merge the branch into `main` (scheduled workflows only run from the default branch).

## Cut list (if time runs short, cut in this order)

1. CSV download (US-11)
2. Port-area comparison (US-07); the current-wait table is sortable anyway
3. FAST comparison (US-08)

Never cut: run log, dedup, NULL handling, freshness banner. Those are what make the
data trustworthy.
