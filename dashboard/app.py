import os
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "healthcare_db")

    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = get_database_url()

PLOTLY_TEMPLATE = "plotly_white"
COLORWAY = ["#0EA5E9", "#14B8A6", "#F97316", "#EF4444", "#A855F7", "#22C55E", "#64748B"]
SATISFACTION_COLORS = {"Excellent": "#22C55E", "Good": "#0EA5E9", "Neutral": "#94A3B8"}


def format_compact_number(value: float | int) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "—"


def format_minutes(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{float(value):.0f}"


def format_days(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{float(value):.1f}"


def format_usd(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"${float(value):,.0f}"

def format_usd_compact(value: float) -> str:
    if pd.isna(value):
        return "—"
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"${value/1_000_000:,.1f}M"
    if abs_value >= 1_000:
        return f"${value/1_000:,.1f}K"
    return f"${value:,.0f}"


def format_pct(value: float, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.{digits}f}%"


def format_pp_delta(curr: float, prev: float, digits: int = 1) -> str | None:
    if prev is None or pd.isna(prev) or curr is None or pd.isna(curr):
        return None
    diff = (float(curr) - float(prev)) * 100
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:.{digits}f} pp"


def safe_delta(curr: float, prev: float) -> float | None:
    if curr is None or pd.isna(curr) or prev is None or pd.isna(prev):
        return None
    return float(curr - prev)


def get_prev_period_range(start: date, end: date) -> tuple[date, date]:
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start, prev_end


def apply_app_style() -> None:
    st.markdown(
        """
        <style>
          .stApp {
            background:
              radial-gradient(900px circle at 8% 2%, rgba(14,165,233,0.16), transparent 42%),
              radial-gradient(900px circle at 92% 8%, rgba(20,184,166,0.16), transparent 42%),
              #f8fafc;
          }
          .block-container { padding-top: 1.15rem; padding-bottom: 2.5rem; max-width: 1180px; }
          .subtle { color: rgba(51, 65, 85, 0.92); font-size: 0.95rem; }
          .section-title { font-size: 1.05rem; font-weight: 650; margin: 0.25rem 0 0.6rem 0; color: #0f172a; }

          /* Metric cards */
          div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.85);
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 16px;
            padding: 14px 14px 12px 14px;
            box-shadow: 0 10px 30px rgba(2, 6, 23, 0.05);
          }
          [data-testid="stMetricLabel"] { color: rgba(30, 41, 59, 0.9); }
          [data-testid="stMetricValue"] { font-size: 1.55rem; color: #0f172a; }
          [data-testid="stMetricDelta"] { font-size: 0.95rem; }

          /* Tabs */
          .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.75);
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            padding: 8px 14px;
            margin-right: 8px;
          }
          .stTabs [aria-selected="true"] {
            background: rgba(14,165,233,0.14);
            border: 1px solid rgba(14,165,233,0.35);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def get_connection_hint(error: Exception) -> str | None:
    msg = str(error).lower()
    db_host = os.getenv("DB_HOST")

    if "could not translate host name" in msg and db_host == "postgres":
        return (
            "Your app is trying to connect to `DB_HOST=postgres`, which only resolves when the app is running "
            "inside the same Docker Compose network as the `postgres` service.\n\n"
            "- If you run Streamlit locally: set `DB_HOST=localhost` (or create `.env.local` with local settings).\n"
            "- If you run in Docker: start with `docker compose up --build` (or at least `docker compose up -d postgres`) "
            "and run the dashboard via Docker Compose (not plain `docker run`). "
            "(Docker Compose uses `.env.docker` by default in this repo.)"
        )

    if "connection refused" in msg:
        return (
            "Postgres is reachable but not accepting connections yet. Make sure the `postgres` container is healthy "
            "and the database is up before loading the dashboard."
        )

    return None


@st.cache_data(show_spinner="Loading data from Postgres...")
def load_fact_visits() -> pd.DataFrame:
    engine = get_engine()
    query = text(
        """
        SELECT
            f.visit_id,
            f.patient_id,
            f.visit_date,
            f.visit_type,
            f.er_wait_time_min,
            f.days_stayed,
            f.treatment_cost,
            f.charges_per_md,
            f.satisfaction_category,
            f.year,
            f.month,
            f.month_name,
            f.quarter,
            d.division_name,
            d.doctor_name,
            d.specialty,
            p.gender,
            p.age,
            p.city,
            p.insurance_type
        FROM fact_visits f
        JOIN dim_department d ON f.department_id = d.department_id
        JOIN dim_patient p ON f.patient_id = p.patient_id
        """
    )
    df = pd.read_sql(query, engine)
    df["visit_date"] = pd.to_datetime(df["visit_date"], errors="coerce")
    return df.dropna(subset=["visit_date"]).copy()


st.set_page_config(
    page_title="Healthcare Analytics Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_app_style()
px.defaults.template = PLOTLY_TEMPLATE
px.defaults.color_discrete_sequence = COLORWAY

st.title("Healthcare Analytics")
st.markdown(
    '<div class="subtle">Fast insights into visits, wait times, costs, and satisfaction — slice the data using filters.</div>',
    unsafe_allow_html=True,
)

st.sidebar.header("Filters")

if st.sidebar.button("Refresh data"):
    load_fact_visits.clear()

try:
    visits = load_fact_visits()
except OperationalError as exc:
    hint = get_connection_hint(exc)
    st.error("Database connection failed.")
    if hint:
        st.info(hint)
    else:
        st.code(str(exc))
    st.stop()

min_date = visits["visit_date"].min().date()
max_date = visits["visit_date"].max().date()

date_range = st.sidebar.date_input(
    "Visit date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

division_options = ["All"] + sorted(visits["division_name"].dropna().unique().tolist())
division = st.sidebar.selectbox("Division", options=division_options, index=0)

visit_type_options = ["All"] + sorted(visits["visit_type"].dropna().unique().tolist())
visit_type = st.sidebar.selectbox("Visit type", options=visit_type_options, index=0)

insurance_options = ["All"] + sorted(visits["insurance_type"].dropna().unique().tolist())
insurance = st.sidebar.selectbox("Insurance", options=insurance_options, index=0)

gender_options = ["All"] + sorted(visits["gender"].dropna().unique().tolist())
gender = st.sidebar.selectbox("Gender", options=gender_options, index=0)

age_min, age_max = int(visits["age"].min()), int(visits["age"].max())
age_range = st.sidebar.slider("Age", min_value=age_min, max_value=age_max, value=(age_min, age_max))

filtered = visits.loc[
    (visits["visit_date"].dt.date >= start_date)
    & (visits["visit_date"].dt.date <= end_date)
].copy()

if division != "All":
    filtered = filtered.loc[filtered["division_name"] == division]
if visit_type != "All":
    filtered = filtered.loc[filtered["visit_type"] == visit_type]
if insurance != "All":
    filtered = filtered.loc[filtered["insurance_type"] == insurance]
if gender != "All":
    filtered = filtered.loc[filtered["gender"] == gender]
filtered = filtered.loc[(filtered["age"] >= age_range[0]) & (filtered["age"] <= age_range[1])]

prev_start, prev_end = get_prev_period_range(start_date, end_date)
prev_df = visits.loc[
    (visits["visit_date"].dt.date >= prev_start) & (visits["visit_date"].dt.date <= prev_end)
].copy()
if division != "All":
    prev_df = prev_df.loc[prev_df["division_name"] == division]
if visit_type != "All":
    prev_df = prev_df.loc[prev_df["visit_type"] == visit_type]
if insurance != "All":
    prev_df = prev_df.loc[prev_df["insurance_type"] == insurance]
if gender != "All":
    prev_df = prev_df.loc[prev_df["gender"] == gender]
prev_df = prev_df.loc[(prev_df["age"] >= age_range[0]) & (prev_df["age"] <= age_range[1])]

top_bar_left, top_bar_right = st.columns([3, 1])
with top_bar_left:
    st.markdown(
        f'<div class="subtle"><b>Current period:</b> {start_date} → {end_date} '
        f'• <b>Previous:</b> {prev_start} → {prev_end}</div>',
        unsafe_allow_html=True,
    )
with top_bar_right:
    st.metric("Visits", f"{len(filtered):,}", delta=safe_delta(float(len(filtered)), float(len(prev_df))))

total_visits = int(len(filtered))
number_of_inpatients = int((filtered["visit_type"] == "Inpatient").sum())
number_of_outpatients = int((filtered["visit_type"] == "Outpatient").sum())
average_er_wait_time_min = float(filtered["er_wait_time_min"].mean()) if len(filtered) else 0.0
median_er_wait_time_min = float(filtered["er_wait_time_min"].median()) if len(filtered) else float("nan")
p90_er_wait_time_min = float(filtered["er_wait_time_min"].quantile(0.9)) if len(filtered) else float("nan")
avg_days = (
    filtered.loc[filtered["visit_type"] == "Inpatient", "days_stayed"]
    .replace(0, pd.NA)
    .mean()
    if len(filtered)
    else 0.0
)
average_days_stayed = float(0.0 if pd.isna(avg_days) else avg_days)

prev_inpatients = int((prev_df["visit_type"] == "Inpatient").sum())
prev_outpatients = int((prev_df["visit_type"] == "Outpatient").sum())
prev_wait = float(prev_df["er_wait_time_min"].mean()) if len(prev_df) else float("nan")
prev_median_wait = float(prev_df["er_wait_time_min"].median()) if len(prev_df) else float("nan")
prev_p90_wait = float(prev_df["er_wait_time_min"].quantile(0.9)) if len(prev_df) else float("nan")
prev_days = (
    prev_df.loc[prev_df["visit_type"] == "Inpatient", "days_stayed"].replace(0, pd.NA).mean()
    if len(prev_df)
    else float("nan")
)
prev_days = float("nan") if pd.isna(prev_days) else float(prev_days)

unique_patients = int(filtered["patient_id"].nunique()) if len(filtered) else 0
prev_unique_patients = int(prev_df["patient_id"].nunique()) if len(prev_df) else 0

total_treatment_cost = float(filtered["treatment_cost"].sum()) if len(filtered) else 0.0
total_charges = float(filtered["charges_per_md"].sum()) if len(filtered) else 0.0
prev_total_treatment_cost = float(prev_df["treatment_cost"].sum()) if len(prev_df) else float("nan")
prev_total_charges = float(prev_df["charges_per_md"].sum()) if len(prev_df) else float("nan")

inpatient_rate = (number_of_inpatients / total_visits) if total_visits else float("nan")
prev_total_visits = int(len(prev_df))
prev_inpatient_rate = (prev_inpatients / prev_total_visits) if prev_total_visits else float("nan")

avg_cost_per_visit = float(filtered["treatment_cost"].mean()) if total_visits else float("nan")
avg_charge_per_visit = float(filtered["charges_per_md"].mean()) if total_visits else float("nan")
prev_avg_cost_per_visit = float(prev_df["treatment_cost"].mean()) if prev_total_visits else float("nan")
prev_avg_charge_per_visit = float(prev_df["charges_per_md"].mean()) if prev_total_visits else float("nan")

charge_multiple = (avg_charge_per_visit / avg_cost_per_visit) if avg_cost_per_visit and not pd.isna(avg_cost_per_visit) else float("nan")
prev_charge_multiple = (
    (prev_avg_charge_per_visit / prev_avg_cost_per_visit)
    if prev_avg_cost_per_visit and not pd.isna(prev_avg_cost_per_visit)
    else float("nan")
)

excellent_rate = (
    float((filtered["satisfaction_category"] == "Excellent").mean()) if total_visits else float("nan")
)
prev_excellent_rate = (
    float((prev_df["satisfaction_category"] == "Excellent").mean()) if prev_total_visits else float("nan")
)

st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
kpi_row_1 = st.columns(4)
kpi_row_1[0].metric("Patients", format_compact_number(unique_patients), delta=safe_delta(unique_patients, prev_unique_patients))
kpi_row_1[1].metric("Visits", format_compact_number(total_visits), delta=safe_delta(total_visits, prev_total_visits))
kpi_row_1[2].metric("Inpatient rate", format_pct(inpatient_rate), delta=format_pp_delta(inpatient_rate, prev_inpatient_rate))
kpi_row_1[3].metric("Avg ER wait (min)", format_minutes(average_er_wait_time_min), delta=safe_delta(average_er_wait_time_min, prev_wait))

kpi_row_2 = st.columns(4)
kpi_row_2[0].metric("Median ER wait (min)", format_minutes(median_er_wait_time_min), delta=safe_delta(median_er_wait_time_min, prev_median_wait))
kpi_row_2[1].metric("P90 ER wait (min)", format_minutes(p90_er_wait_time_min), delta=safe_delta(p90_er_wait_time_min, prev_p90_wait))
kpi_row_2[2].metric("Avg cost / visit", format_usd_compact(avg_cost_per_visit), delta=safe_delta(avg_cost_per_visit, prev_avg_cost_per_visit))
kpi_row_2[3].metric("Avg charge / visit", format_usd_compact(avg_charge_per_visit), delta=safe_delta(avg_charge_per_visit, prev_avg_charge_per_visit))

kpi_row_3 = st.columns(4)
kpi_row_3[0].metric("Inpatients", format_compact_number(number_of_inpatients), delta=safe_delta(number_of_inpatients, prev_inpatients))
kpi_row_3[1].metric("Outpatients", format_compact_number(number_of_outpatients), delta=safe_delta(number_of_outpatients, prev_outpatients))
kpi_row_3[2].metric("Charge multiple", f"{charge_multiple:.2f}x" if not pd.isna(charge_multiple) else "—", delta=safe_delta(charge_multiple, prev_charge_multiple))
kpi_row_3[3].metric("Excellent satisfaction", format_pct(excellent_rate), delta=format_pp_delta(excellent_rate, prev_excellent_rate))

st.caption("Tip: deltas compare the current date range to the previous period of the same length.")

st.markdown("---")

tabs = st.tabs(["Trends", "Operations", "Satisfaction", "Details"])

patients_by_div = (
    filtered.groupby("division_name", as_index=False)
    .size()
    .rename(columns={"size": "patient_count"})
    .sort_values("patient_count", ascending=False)
)

wait_time_by_div = (
    filtered.groupby("division_name", as_index=False)["er_wait_time_min"]
    .mean()
    .rename(columns={"er_wait_time_min": "avg_wait_time"})
    .sort_values("avg_wait_time", ascending=False)
)

satisfaction_by_div = (
    filtered.groupby(["division_name", "satisfaction_category"], as_index=False)
    .size()
    .rename(columns={"size": "satisfaction_count"})
    .sort_values(["division_name", "satisfaction_category"])
)

monthly_inout = (
    filtered.groupby(["year", "month", "month_name"], as_index=False)
    .agg(
        number_of_inpatients=("visit_type", lambda s: int((s == "Inpatient").sum())),
        number_of_outpatients=("visit_type", lambda s: int((s == "Outpatient").sum())),
    )
    .sort_values(["year", "month"])
)
monthly_inout["period"] = monthly_inout["month_name"] + "-" + monthly_inout["year"].astype(str)

monthly_costs = (
    filtered.groupby(["year", "month", "month_name"], as_index=False)
    .agg(
        total_treatment_cost=("treatment_cost", "sum"),
        total_charges=("charges_per_md", "sum"),
    )
    .sort_values(["year", "month"])
)
monthly_costs["period"] = monthly_costs["month_name"] + "-" + monthly_costs["year"].astype(str)

if filtered.empty:
    st.warning("No visits match the current filters. Adjust filters in the sidebar.")

with tabs[0]:
    left, right = st.columns([2, 1])
    with left:
        st.markdown('<div class="section-title">Costs & Charges</div>', unsafe_allow_html=True)
        if monthly_costs.empty:
            st.info("No data for monthly costs.")
        else:
            fig_cost = go.Figure()
            fig_cost.add_trace(
                go.Scatter(
                    x=monthly_costs["period"],
                    y=monthly_costs["total_charges"],
                    mode="lines+markers",
                    name="Charges",
                    line=dict(width=3, color=COLORWAY[0]),
                    hovertemplate="%{x}<br>Charges: $%{y:,.0f}<extra></extra>",
                )
            )
            fig_cost.add_trace(
                go.Scatter(
                    x=monthly_costs["period"],
                    y=monthly_costs["total_treatment_cost"],
                    mode="lines+markers",
                    name="Treatment cost",
                    line=dict(width=3, color=COLORWAY[1]),
                    hovertemplate="%{x}<br>Cost: $%{y:,.0f}<extra></extra>",
                )
            )
            fig_cost.update_layout(
                template=PLOTLY_TEMPLATE,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                xaxis_title="Month",
                yaxis_title="USD",
                colorway=COLORWAY,
                height=360,
                hovermode="x unified",
            )
            st.plotly_chart(fig_cost, use_container_width=True)

    with right:
        st.markdown('<div class="section-title">Inpatients vs Outpatients</div>', unsafe_allow_html=True)
        if monthly_inout.empty:
            st.info("No data for monthly in/out patients.")
        else:
            fig_inout = go.Figure()
            fig_inout.add_trace(
                go.Scatter(
                    x=monthly_inout["period"],
                    y=monthly_inout["number_of_inpatients"],
                    mode="lines+markers",
                    name="Inpatients",
                    line=dict(width=3, color=COLORWAY[2]),
                    hovertemplate="%{x}<br>Inpatients: %{y:,.0f}<extra></extra>",
                )
            )
            fig_inout.add_trace(
                go.Scatter(
                    x=monthly_inout["period"],
                    y=monthly_inout["number_of_outpatients"],
                    mode="lines+markers",
                    name="Outpatients",
                    line=dict(width=3, color=COLORWAY[3]),
                    hovertemplate="%{x}<br>Outpatients: %{y:,.0f}<extra></extra>",
                )
            )
            fig_inout.update_layout(
                template=PLOTLY_TEMPLATE,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                xaxis_title="Month",
                yaxis_title="Visits",
                colorway=COLORWAY,
                height=360,
                hovermode="x unified",
            )
            st.plotly_chart(fig_inout, use_container_width=True)

with tabs[1]:
    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="section-title">Patient Mix</div>', unsafe_allow_html=True)
        if patients_by_div.empty:
            st.info("No data for patients-by-division.")
        else:
            fig_div = px.bar(
                patients_by_div.head(10),
                x="patient_count",
                y="division_name",
                orientation="h",
                text="patient_count",
            )
            fig_div.update_traces(textposition="outside", cliponaxis=False)
            fig_div.update_layout(
                template=PLOTLY_TEMPLATE,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Visits",
                yaxis_title="Division",
                colorway=COLORWAY,
                height=380,
            )
            st.plotly_chart(fig_div, use_container_width=True)

    with right:
        st.markdown('<div class="section-title">Average ER Wait (by division)</div>', unsafe_allow_html=True)
        if wait_time_by_div.empty:
            st.info("No data for wait-time-by-division.")
        else:
            fig_wait = px.bar(
                wait_time_by_div.head(10),
                x="avg_wait_time",
                y="division_name",
                orientation="h",
                text="avg_wait_time",
            )
            fig_wait.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
            fig_wait.update_layout(
                template=PLOTLY_TEMPLATE,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Minutes",
                yaxis_title="Division",
                colorway=COLORWAY,
                height=380,
            )
            st.plotly_chart(fig_wait, use_container_width=True)

    st.markdown('<div class="section-title">Wait Time Distribution</div>', unsafe_allow_html=True)
    if filtered.empty:
        st.info("No data for wait time distribution.")
    else:
        hist_col1, hist_col2 = st.columns([2, 1])
        with hist_col1:
            fig_hist = px.histogram(
                filtered,
                x="er_wait_time_min",
                nbins=30,
                color_discrete_sequence=[COLORWAY[0]],
            )
            fig_hist.update_layout(
                template=PLOTLY_TEMPLATE,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="ER wait time (min)",
                yaxis_title="Visits",
                height=300,
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        with hist_col2:
            st.metric("Median wait (min)", format_minutes(median_er_wait_time_min))
            st.metric("P90 wait (min)", format_minutes(p90_er_wait_time_min))
            st.metric("Avg stay (days)", format_days(average_days_stayed), delta=safe_delta(average_days_stayed, prev_days))

with tabs[2]:
    st.markdown('<div class="section-title">Satisfaction (stacked)</div>', unsafe_allow_html=True)
    if satisfaction_by_div.empty:
        st.info("No data for satisfaction-by-division.")
    else:
        order = ["Excellent", "Good", "Neutral"]
        satisfaction_by_div["satisfaction_category"] = pd.Categorical(
            satisfaction_by_div["satisfaction_category"], categories=order, ordered=True
        )
        fig_sat = px.bar(
            satisfaction_by_div,
            x="division_name",
            y="satisfaction_count",
            color="satisfaction_category",
            barmode="stack",
            category_orders={"satisfaction_category": order},
            color_discrete_map=SATISFACTION_COLORS,
        )
        fig_sat.update_layout(
            template=PLOTLY_TEMPLATE,
            margin=dict(l=10, r=10, t=10, b=10),
            legend_title_text="",
            xaxis_title="Division",
            yaxis_title="Count",
            height=420,
        )
        st.plotly_chart(fig_sat, use_container_width=True)

with tabs[3]:
    st.markdown('<div class="section-title">Underlying Visits</div>', unsafe_allow_html=True)
    st.caption("Use filters in the sidebar to narrow results, then explore or export.")
    show_cols = [
        "visit_date",
        "division_name",
        "doctor_name",
        "visit_type",
        "er_wait_time_min",
        "days_stayed",
        "treatment_cost",
        "charges_per_md",
        "satisfaction_category",
        "insurance_type",
        "gender",
        "age",
        "city",
    ]
    display_df = filtered[show_cols].sort_values("visit_date", ascending=False).copy()
    st.dataframe(
        display_df,
        use_container_width=True,
        height=420,
        column_config={
            "visit_date": st.column_config.DateColumn("visit_date"),
            "er_wait_time_min": st.column_config.NumberColumn("er_wait_time_min", format="%.0f"),
            "days_stayed": st.column_config.NumberColumn("days_stayed", format="%.0f"),
            "treatment_cost": st.column_config.NumberColumn("treatment_cost", format="$%.0f"),
            "charges_per_md": st.column_config.NumberColumn("charges_per_md", format="$%.0f"),
        },
    )
    st.download_button(
        "Download CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_visits.csv",
        mime="text/csv",
        use_container_width=True,
    )
