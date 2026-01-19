import pandas as pd
import altair as alt
import streamlit as st

from utils import (
    RAW_URL,
    LOCAL_CSV,
    META_FILE,
    fetch_csv_if_needed,
)

st.set_page_config(
    page_title="TTT – Data Explorer",
    layout="wide",
)

# -----------------------------
# Data loading
# -----------------------------
@st.cache_data(show_spinner="Fetching & loading dataset...")
def load_data() -> pd.DataFrame:
    csv_path = fetch_csv_if_needed(RAW_URL, LOCAL_CSV)
    df = pd.read_csv(csv_path)

    # Lightweight type safety
    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    if "DayOfYear" in df.columns:
        df["DayOfYear"] = pd.to_numeric(df["DayOfYear"], errors="coerce")
    if "Value" in df.columns:
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    if "ErrorRisk" in df.columns:
        df["ErrorRisk"] = pd.to_numeric(df["ErrorRisk"], errors="coerce")

    return df


def _safe_unique(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return []
    return sorted([x for x in df[col].dropna().unique()])

# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.header("Data")

    # Force refresh: delete cached file + meta then rerun
    if st.button("Force refresh from source"):
        try:
            if LOCAL_CSV.exists():
                LOCAL_CSV.unlink()
            if META_FILE.exists():
                META_FILE.unlink()
        except Exception:
            pass
        st.cache_data.clear()
        st.rerun()

    st.caption("Source")
    st.code(RAW_URL, language="text")


df = load_data()

# -----------------------------
# Header + overview
# -----------------------------
st.title("Tundra Trait Team (TTT) Database Explorer")

st.markdown(
    """
This dashboard provides an exploratory overview of the Tundra Trait Team (TTT) database,
including spatial coverage, trait distributions, and data quality indicators.
"""
)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Observations", f"{len(df):,}" if len(df) else "0")
c2.metric("Traits", df["Trait"].nunique() if "Trait" in df.columns else 0)
c3.metric("Species", df["AccSpeciesName"].nunique() if "AccSpeciesName" in df.columns else 0)
if "Year" in df.columns and df["Year"].notna().any():
    c4.metric("Year range", f"{int(df['Year'].min())} – {int(df['Year'].max())}")
else:
    c4.metric("Year range", "N/A")

st.divider()

# -----------------------------
# Filters (main area)
# -----------------------------
st.subheader("Filters")

f1, f2, f3, f4 = st.columns(4)

traits = _safe_unique(df, "Trait")
species = _safe_unique(df, "AccSpeciesName")
sites = _safe_unique(df, "SiteName")
treatments = _safe_unique(df, "Treatment")

with f1:
    selected_trait = st.selectbox("Trait", traits, index=0 if traits else None)
with f2:
    selected_species = st.selectbox("Species", ["All"] + species, index=0)
with f3:
    selected_site = st.selectbox("Site", ["All"] + sites, index=0)
with f4:
    selected_treatment = st.selectbox("Treatment", ["All"] + treatments, index=0)

# Year slider
if "Year" in df.columns and df["Year"].notna().any():
    year_min = int(df["Year"].min())
    year_max = int(df["Year"].max())
    year_range = st.slider("Year range", year_min, year_max, (year_min, year_max))
else:
    year_range = None

# Apply filters
filtered = df.copy()

if selected_trait and "Trait" in filtered.columns:
    filtered = filtered[filtered["Trait"] == selected_trait]

if selected_species != "All" and "AccSpeciesName" in filtered.columns:
    filtered = filtered[filtered["AccSpeciesName"] == selected_species]

if selected_site != "All" and "SiteName" in filtered.columns:
    filtered = filtered[filtered["SiteName"] == selected_site]

if selected_treatment != "All" and "Treatment" in filtered.columns:
    filtered = filtered[filtered["Treatment"] == selected_treatment]

if year_range and "Year" in filtered.columns:
    filtered = filtered[filtered["Year"].between(year_range[0], year_range[1])]

st.caption(f"Filtered rows: {len(filtered):,}")