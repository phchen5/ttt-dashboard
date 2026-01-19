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

tab_species, tab_trait, tab_spatial, tab_quality, tab_table = st.tabs(
    ["Species", "Trait", "Spatial", "Data quality", "Table"]
)

with tab_species:
    st.header("Species")

    if "AccSpeciesName" not in df.columns:
        st.error("Column 'AccSpeciesName' not found in the dataset.")
        st.stop()

    species_list = sorted(df["AccSpeciesName"].dropna().unique())
    selected_species = st.selectbox("Select a species", species_list)

    species_df = df[df["AccSpeciesName"] == selected_species].copy()

    # Ensure numeric columns behave
    for col in ["Year", "DayOfYear", "Value", "ErrorRisk", "Latitude", "Longitude", "Elevation"]:
        if col in species_df.columns:
            species_df[col] = pd.to_numeric(species_df[col], errors="coerce")

    # ---- Summary metrics ----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(species_df):,}")
    c2.metric("Traits measured", species_df["Trait"].nunique() if "Trait" in species_df.columns else 0)
    c3.metric("Sites", species_df["SiteName"].nunique() if "SiteName" in species_df.columns else 0)
    if "Year" in species_df.columns and species_df["Year"].notna().any():
        c4.metric("Years", f"{int(species_df['Year'].min())} – {int(species_df['Year'].max())}")
    else:
        c4.metric("Years", "N/A")

    st.divider()

    # ---- Preview table ----
    st.subheader("Row preview (first 200)")

    preview_cols = [
        "AccSpeciesName", "Trait", "Value", "Units", "Year", "DayOfYear",
        "SiteName", "SubsiteName", "Treatment",
        "Latitude", "Longitude", "Elevation",
        "ValueKindName", "IndividualID", "DataContributor",
        "ErrorRisk", "Comments"
    ]
    preview_cols = [c for c in preview_cols if c in species_df.columns]
    st.dataframe(species_df[preview_cols].head(200), use_container_width=True)
