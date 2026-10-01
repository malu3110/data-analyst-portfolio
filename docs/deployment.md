# Deployment guide

About 30 minutes, all on free tiers. Steps 1–4 need your own accounts, so they can't be
automated from the repo.

## 1. Database: Neon (free Postgres)

1. Sign up at https://neon.tech and create a project (any region; US East is closest
   to GitHub's runners and Streamlit Cloud).
2. Copy the connection string from **Connection Details**. It looks like
   `postgresql://neondb_owner:...@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require`.
   This is the **pipeline** connection (it can write).
3. Create a **read-only** login for the dashboard. In Neon's SQL editor:

   ```sql
   CREATE ROLE dashboard_reader WITH LOGIN PASSWORD 'choose-a-long-password';
   CREATE SCHEMA IF NOT EXISTS marts;
   GRANT USAGE ON SCHEMA marts TO dashboard_reader;
   GRANT SELECT ON ALL TABLES IN SCHEMA marts TO dashboard_reader;
   -- dbt recreates mart tables on every run; keep the grant on new tables:
   ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner IN SCHEMA marts
       GRANT SELECT ON TABLES TO dashboard_reader;
   ```

   The dashboard connection string is the same as above with
   `dashboard_reader:<password>` in place of the owner credentials.

## 2. GitHub: add the secret

Repository → **Settings → Secrets and variables → Actions → New repository secret**

- Name: `DATABASE_URL`
- Value: the **pipeline** (owner) connection string from step 1.2

## 3. Make the schedule live

Scheduled workflows only run from the repository's **default branch**.

1. Merge the working branch into `main` (or make the branch the default).
2. **Actions** tab → enable workflows if prompted.
3. Run once by hand to load data immediately:
   - **ingest-bts-weekly** → *Run workflow* (loads BTS monthly truck data since 2015)
   - **ingest-hourly** → *Run workflow* (first CBP snapshot + dbt build)
4. Both should go green. After that, `ingest-hourly` runs at minute 17 of every hour.

## 4. Dashboard: Streamlit Community Cloud

1. https://share.streamlit.io → **Create app** → *Deploy a public app from GitHub*.
2. Repository: `malu3110/data-analyst-portfolio`, branch `main`,
   main file `app/streamlit_app.py`. Python 3.11+.
3. **Advanced settings → Secrets**:

   ```toml
   DATABASE_URL = "postgresql://dashboard_reader:...@ep-xxxx.../neondb?sslmode=require"
   ```

4. Deploy. Copy the app URL into the top of `README.md`.

## 5. After a week

- Check the **Pipeline health** tab: hourly capture success should be ≥ 95%.
- Take screenshots of the live dashboard for the README.
- Update the README's "What the data showed" section with findings from real history
  (median waits by hour at the busiest crossings, measured FAST savings).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ingest-hourly` fails at "Ingest CBP snapshot" with `SchemaError` | CBP changed its JSON. The raw history is safe; update `REQUIRED_KEYS`/`LANE_KEYS` and the staging model |
| fails at dbt with `assert_known_tz_abbreviations` | CBP used a zone not in `transform/seeds/tz_abbreviations.csv`; add it |
| dashboard shows "Data may be out of date" | Scheduled runs stopped: check the Actions tab; GitHub pauses schedules after 60 days without repo activity |
| dashboard error about `marts.*` permission | Re-run the `GRANT`/`ALTER DEFAULT PRIVILEGES` statements in step 1.3 |
| Neon first query slow | Free-tier compute suspends when idle; first query wakes it (a few seconds) |
