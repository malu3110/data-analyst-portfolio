"""Cross-Border Truck Wait Monitor — public dashboard.

Reads only the dbt marts. Each section maps to a user story in
docs/requirements.md (US-xx noted in comments).
"""
import os
from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import psycopg
import streamlit as st

REPO_URL = "https://github.com/malu3110/data-analyst-portfolio"
STALE_BANNER_HOURS = 2  # US-02
BLUE, ORANGE = "#2a78d6", "#eb6834"  # categorical slots 1-2 (standard, FAST)
LANE_COLORS = alt.Scale(domain=["Standard", "FAST"], range=[BLUE, ORANGE])

st.set_page_config(page_title="Border Truck Waits", page_icon="🚚", layout="wide")


def database_url() -> str:
    try:
        return st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.environ["DATABASE_URL"]


@st.cache_data(ttl=600, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    with psycopg.connect(database_url()) as conn:
        cur = conn.execute(sql)
        cols = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def describe_wait(status, minutes, stale) -> str:
    """US-03: missing is never shown as zero."""
    if status is None or pd.isna(status):
        return "No FAST lane"
    if status == "reported":
        text = f"{int(minutes)} min"
        return f"{text} (stale)" if stale else text
    return {
        "closed": "Closed",
        "pending": "Not reported",
        "not_applicable": "No lane",
        "unparsed": "Not reported",
    }.get(status, "Not reported")


def csv_button(df: pd.DataFrame, name: str) -> None:
    """US-11: download what is on screen."""
    st.download_button("Download CSV", df.to_csv(index=False).encode(), f"{name}.csv", "text/csv", key=f"dl-{name}")


current = query("select * from marts.mart_current_wait")
crossings = query("select * from marts.dim_crossing where has_commercial_lanes")
profile = query("select * from marts.mart_hourly_profile")
fast = query("select * from marts.mart_fast_vs_standard")
volume = query("select * from marts.mart_truck_volume_monthly")
health = query("select * from marts.mart_pipeline_health order by run_date")
history = query("select * from marts.mart_history_summary").iloc[0]

# ---------------------------------------------------------------- header
st.title("Cross-Border Truck Wait Monitor")
st.caption(
    "Commercial truck waits at US land ports of entry, captured hourly from CBP's public feed. "
    "CBP publishes only the current snapshot, so this pipeline keeps the history. "
    f"Observed history, not a forecast. [Source code & requirements]({REPO_URL})"
)

# US-02: freshness is always visible
now = datetime.now(timezone.utc)
last_capture = pd.to_datetime(current["captured_at"]).max() if not current.empty else None
if last_capture is None:
    st.error("No data loaded yet.")
    st.stop()
age = now - last_capture.to_pydatetime()
if age > timedelta(hours=STALE_BANNER_HOURS):
    st.warning(
        f"Data may be out of date: the last successful capture was {last_capture:%Y-%m-%d %H:%M} UTC "
        f"({age.total_seconds() / 3600:.1f} hours ago)."
    )
else:
    st.caption(f"Last capture: {last_capture:%Y-%m-%d %H:%M} UTC · history since {history.first_capture_at:%Y-%m-%d} ({history.captures} captures)")

tab_now, tab_hour, tab_fast, tab_volume, tab_health, tab_about = st.tabs(
    ["Now", "Typical by hour", "FAST vs standard", "Truck volume", "Pipeline health", "About"]
)

# ---------------------------------------------------------------- Now (US-01, US-03, US-07)
with tab_now:
    c1, c2, c3 = st.columns([1, 2, 1])
    border = c1.radio("Border", ["US-Mexico", "US-Canada"], horizontal=True)
    ports = sorted(current.loc[current.border == border, "port_name"].unique())
    area = c2.selectbox("Port area (compare its crossings)", ["All"] + ports)
    hour_choice = c3.selectbox(
        "Planned arrival (local hour)", ["Now"] + [f"{h:02d}:00" for h in range(24)],
        help="Typical wait is looked up for this local hour at each crossing.",
    )

    view = current[current.border == border].copy()
    if area != "All":
        view = view[view.port_name == area]

    def arrival_hour(offset):
        if hour_choice != "Now":
            return int(hour_choice[:2])
        if offset is None or pd.isna(offset):
            return None
        return (now + timedelta(hours=float(offset))).hour

    view["arrival_hour"] = view["utc_offset_hours"].map(arrival_hour)
    std_profile = profile[profile.lane_type == "standard"][["port_number", "local_hour", "n_readings", "median_delay_minutes", "is_sufficient"]]
    view = view.merge(std_profile, how="left", left_on=["port_number", "arrival_hour"], right_on=["port_number", "local_hour"])

    def typical(row) -> str:
        n = 0 if pd.isna(row.n_readings) else int(row.n_readings)
        if not row.is_sufficient or pd.isna(row.is_sufficient):
            return f"Insufficient history (n = {n})"
        return f"{row.median_delay_minutes:.0f} min (n = {n})"

    reporting = view[(view.standard_status == "reported") & (~view.standard_is_stale.fillna(False))]
    m1, m2, m3 = st.columns(3)
    m1.metric("Crossings reporting a current wait", f"{len(reporting)} of {len(view)}")
    m2.metric("Median standard-lane wait", f"{reporting.standard_delay_minutes.median():.0f} min" if len(reporting) else "—")
    if len(reporting):
        worst = reporting.loc[reporting.standard_delay_minutes.idxmax()]
        m3.metric("Longest standard-lane wait", f"{int(worst.standard_delay_minutes)} min", worst.crossing_label, delta_color="off")

    table = pd.DataFrame({
        "Crossing": view.crossing_label,
        "Standard lane": [describe_wait(s, m, x) for s, m, x in zip(view.standard_status, view.standard_delay_minutes, view.standard_is_stale)],
        "Typical (standard) at arrival hour": view.apply(typical, axis=1),
        "FAST lane": [describe_wait(s, m, x) for s, m, x in zip(view.fast_status, view.fast_delay_minutes, view.fast_is_stale)],
        "Lanes open (std)": view.standard_lanes_open.map(lambda n: "—" if pd.isna(n) else str(int(n))),
        "CBP updated": view.standard_update_time_text.fillna("—"),
        "_sort": view.standard_delay_minutes.where(view.standard_status == "reported"),
    }).sort_values("_sort", na_position="last").drop(columns="_sort")
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption(
        "Wait = CBP's estimate of time to reach the primary inspection booth. "
        "'Not reported' and 'Closed' are never counted as zero. "
        "'Stale' = CBP's last update is over 2 hours old; stale readings are excluded from all statistics."
    )
    csv_button(table, "current_waits")

# ---------------------------------------------------------------- Typical by hour (US-06)
with tab_hour:
    options = crossings.sort_values(["border", "crossing_label"])
    label = st.selectbox("Crossing", options.crossing_label, key="hour_crossing")
    pn = options.loc[options.crossing_label == label, "port_number"].iloc[0]
    p = profile[profile.port_number == pn].copy()
    p["Lane"] = p.lane_type.map({"standard": "Standard", "fast": "FAST"})
    ok = p[p.is_sufficient]
    if ok.empty:
        st.info("Not enough history yet for this crossing (needs at least 5 fresh readings per hour).")
    else:
        hover = alt.selection_point(fields=["local_hour"], nearest=True, on="pointerover", empty=False)
        x = alt.X("local_hour:Q", title="Local hour at the crossing", scale=alt.Scale(domain=[0, 23]), axis=alt.Axis(tickCount=12))
        band = alt.Chart(ok).mark_area(opacity=0.15).encode(
            x=x, y=alt.Y("min_delay_minutes:Q", title="Wait (minutes)"), y2="max_delay_minutes:Q",
            color=alt.Color("Lane:N", scale=LANE_COLORS, legend=None),
        )
        line = alt.Chart(ok).mark_line(strokeWidth=2).encode(
            x=x, y="median_delay_minutes:Q", color=alt.Color("Lane:N", scale=LANE_COLORS, legend=alt.Legend(orient="top", title=None)),
        )
        points = alt.Chart(ok).mark_point(size=60, filled=True).encode(
            x=x, y="median_delay_minutes:Q", color=alt.Color("Lane:N", scale=LANE_COLORS),
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=[alt.Tooltip("Lane:N"), alt.Tooltip("local_hour:Q", title="Hour"),
                     alt.Tooltip("median_delay_minutes:Q", title="Median (min)", format=".0f"),
                     alt.Tooltip("min_delay_minutes:Q", title="Min"), alt.Tooltip("max_delay_minutes:Q", title="Max"),
                     alt.Tooltip("n_readings:Q", title="Readings (n)")],
        ).add_params(hover)
        rule = alt.Chart(ok).mark_rule(color="#888", strokeWidth=1).encode(x=x).transform_filter(hover)
        st.altair_chart((band + line + rule + points).properties(height=360), width="stretch")
        st.caption("Line = median; shaded band = observed min–max. Hours with fewer than 5 fresh readings are omitted.")
    missing = p[~p.is_sufficient]
    if not missing.empty:
        st.caption("Insufficient history: " + ", ".join(f"{r.Lane} {int(r.local_hour):02d}:00 (n = {int(r.n_readings)})" for r in missing.itertuples()))
    out = p[["Lane", "local_hour", "n_readings", "median_delay_minutes", "min_delay_minutes", "max_delay_minutes", "is_sufficient"]].sort_values(["Lane", "local_hour"])
    with st.expander("Table view"):
        st.dataframe(out, hide_index=True, width="stretch")
    csv_button(out, "hourly_profile")

# ---------------------------------------------------------------- FAST vs standard (US-08)
with tab_fast:
    st.markdown("Median minutes the FAST lane saved compared with the standard lane, using readings CBP published at the same time for the same crossing.")
    fb = st.radio("Border", ["US-Mexico", "US-Canada"], horizontal=True, key="fast_border")
    f = fast[(fast.border == fb) & fast.is_sufficient].sort_values("median_minutes_saved", ascending=False)
    if f.empty:
        st.info("Not enough paired readings yet.")
    else:
        chart = alt.Chart(f).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
            x=alt.X("median_minutes_saved:Q", title="Median minutes saved by FAST", axis=alt.Axis(tickCount=6)),
            y=alt.Y("crossing_label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
            tooltip=[alt.Tooltip("crossing_label:N", title="Crossing"),
                     alt.Tooltip("median_minutes_saved:Q", title="Saved (min)", format=".0f"),
                     alt.Tooltip("median_standard_minutes:Q", title="Standard median", format=".0f"),
                     alt.Tooltip("median_fast_minutes:Q", title="FAST median", format=".0f"),
                     alt.Tooltip("n_pairs:Q", title="Paired readings (n)")],
        ).properties(height=max(200, 28 * len(f)))
        st.altair_chart(chart, width="stretch")
    no_fast = sorted(set(crossings[crossings.border == fb].crossing_label) - set(fast.crossing_label))
    if no_fast:
        st.caption("No FAST readings: " + ", ".join(no_fast))
    out = f[["crossing_label", "n_pairs", "median_standard_minutes", "median_fast_minutes", "median_minutes_saved"]]
    with st.expander("Table view"):
        st.dataframe(out, hide_index=True, width="stretch")
    csv_button(out, "fast_vs_standard")

# ---------------------------------------------------------------- Truck volume (US-05)
with tab_volume:
    latest = pd.to_datetime(volume.month).max()
    st.markdown(f"Inbound truck crossings by port, from BTS Border Crossing Entry Data. Latest month available: **{latest:%B %Y}** (BTS publishes with a lag).")
    vb = st.radio("Border", ["US-Mexico", "US-Canada"], horizontal=True, key="vol_border")
    v = volume[volume.border == vb].copy()
    v["month"] = pd.to_datetime(v.month)
    last12 = v[v.month > latest - pd.DateOffset(months=12)]
    top = last12.groupby("port_name", as_index=False).trucks.sum().nlargest(15, "trucks")
    bars = alt.Chart(top).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
        x=alt.X("trucks:Q", title="Trucks, last 12 months", axis=alt.Axis(format="~s", tickCount=6)),
        y=alt.Y("port_name:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        tooltip=[alt.Tooltip("port_name:N", title="Port"), alt.Tooltip("trucks:Q", title="Trucks", format=",")],
    ).properties(height=30 * len(top), title="Top ports by inbound trucks (last 12 months)")
    st.altair_chart(bars, width="stretch")
    port = st.selectbox("Monthly trend for port", top.port_name, key="trend_port")
    trend = v[v.port_name == port].groupby("month", as_index=False).trucks.sum()
    line = alt.Chart(trend).mark_line(color=BLUE, strokeWidth=2, point=alt.OverlayMarkDef(size=40, filled=True)).encode(
        x=alt.X("month:T", title=None), y=alt.Y("trucks:Q", title="Inbound trucks per month", axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("trucks:Q", format=",")],
    ).properties(height=300, title=f"{port}: inbound trucks per month")
    st.altair_chart(line, width="stretch")
    csv_button(top, "truck_volume_top_ports")

# ---------------------------------------------------------------- Pipeline health (success metrics)
with tab_health:
    h = health.copy()
    total_expected, total_hours = h.expected_hourly_runs.sum(), h.hours_with_success.sum()
    k1, k2, k3 = st.columns(3)
    k1.metric("Hourly capture success", f"{100 * total_hours / total_expected:.1f}%" if total_expected else "—", help="Hours with a successful capture ÷ hours scheduled. Target ≥ 95%.")
    k2.metric("Failed runs", int(h.runs_failed.sum()))
    k3.metric("Usable lane readings", f"{100 * h.usable_readings.sum() / max(1, h.lane_readings.sum()):.0f}%", help="Reported and fresh, out of all commercial lane readings (closed / pending / stale are not usable).")
    st.dataframe(h.rename(columns={
        "run_date": "Date (UTC)", "expected_hourly_runs": "Hours scheduled", "hours_with_success": "Hours captured",
        "runs_succeeded": "Successful runs", "runs_failed": "Failed runs", "lane_readings": "Lane readings",
        "usable_readings": "Usable", "pct_usable": "% usable"}), hide_index=True, width="stretch")

# ---------------------------------------------------------------- About
with tab_about:
    st.markdown(f"""
**The problem.** Cross-border dispatchers and planners can see CBP's current wait at a crossing, but not
what it is *typically* like at the hour their truck will arrive, whether a nearby crossing is usually
faster, or how much the FAST lane actually saves. CBP's public feed has no history.

**What this does.** A scheduled job captures CBP's feed every hour into Postgres; dbt cleans and models it
(missing values stay missing, stale readings are flagged); this app shows current waits next to observed
history, plus BTS monthly truck volumes for context.

**What it is not.** Not a forecast, not a routing tool, and the "typical" figures only cover the period the
pipeline has been running. This is a personal portfolio project; the users and requirements behind it are a
design exercise, described in the [requirements document]({REPO_URL}/blob/main/docs/requirements.md).

**Sources.** [CBP Border Wait Times](https://bwt.cbp.gov) · [BTS Border Crossing Entry Data](https://data.bts.gov/Research-and-Statistics/Border-Crossing-Entry-Data/keg4-3bc2)
""")
