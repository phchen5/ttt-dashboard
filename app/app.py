import pandas as pd
import altair as alt
import streamlit as st
import pydeck as pdk
import numpy as np

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

    # ---- Trait coverage (counts) ----
    st.subheader("Trait Coverage")

    if "Trait" not in species_df.columns:
        st.info("No 'Trait' column available.")
    else:
        trait_counts = (
            species_df.dropna(subset=["Trait"])
            .groupby("Trait", as_index=False)
            .size()
            .rename(columns={"size": "n"})
            .sort_values("n", ascending=False)
        )

        if trait_counts.empty:
            st.info("No trait records available for this species.")
        else:
            bar = (
                alt.Chart(trait_counts)
                .mark_bar()
                .encode(
                    y=alt.Y("Trait:N", sort="-x", title=None, axis=alt.Axis(labelLimit=400)),
                    x=alt.X(
                        "n:Q",
                        title="Number of observations",
                        scale=alt.Scale(nice=False, zero=True),
                        axis=alt.Axis(tickMinStep=1.0)
                    ),
                    tooltip=["Trait:N", "n:Q"],
                )
                .properties(height=min(520, 18 * max(10, len(trait_counts))))
            )
            st.altair_chart(bar, use_container_width=True)

    st.divider()

    # ---- Trait value summary table (median/IQR) ----
    st.subheader("Trait Summary Statistics")

    if not {"Trait", "Value"}.issubset(species_df.columns):
        st.info("Columns 'Trait' and/or 'Value' are missing.")
    else:
        summary = (
            species_df.dropna(subset=["Trait", "Value"])
            .groupby(["Trait", "Units"], as_index=False)
            .agg(
                n=("Value", "count"),
                median=("Value", "median"),
                p25=("Value", lambda x: x.quantile(0.25)),
                p75=("Value", lambda x: x.quantile(0.75)),
                min=("Value", "min"),
                max=("Value", "max"),
            )
            .sort_values("n", ascending=False)
        )
        st.dataframe(summary, use_container_width=True)

    st.divider()

    # ---- Optional: choose a trait for a deeper look ----
    st.subheader("Explore the Distribution of Traits")

    if "Trait" in species_df.columns and "Value" in species_df.columns:
        available_traits = sorted(species_df["Trait"].dropna().unique())
        if available_traits:
            chosen_trait = st.selectbox("Trait (within selected species)", available_traits)

            trait_df = species_df[
                (species_df["Trait"] == chosen_trait) & (species_df["Value"].notna())
            ].copy()

            if trait_df.empty:
                st.info("No numeric values available for this trait under this species.")
            else:
                hist = (
                    alt.Chart(trait_df)
                    .mark_bar()
                    .encode(
                        x=alt.X("Value:Q", bin=alt.Bin(maxbins=50), title=f"{chosen_trait} (Value)"),
                        y=alt.Y("count()", title="Count"),
                        tooltip=[alt.Tooltip("count()", title="Count")],
                    )
                    .properties(height=300)
                )
                st.altair_chart(hist, use_container_width=True)

        else:
            st.info("No traits available for this species.")
    else:
        st.info("Trait exploration requires 'Trait' and 'Value' columns.")

    st.divider()


    # ---- Map view ----
    st.subheader("Measurement Locations")

    # 1) Clean coords
    map_df = species_df.dropna(subset=["Latitude", "Longitude"]).copy()
    map_df["Latitude"] = pd.to_numeric(map_df["Latitude"], errors="coerce")
    map_df["Longitude"] = pd.to_numeric(map_df["Longitude"], errors="coerce")
    map_df = map_df.dropna(subset=["Latitude", "Longitude"])

    if map_df.empty:
        st.info("No georeferenced observations available for this species.")
    else:
        # 2) Aggregate by location and keep helpful summary fields for tooltips
        agg = (
            map_df.groupby(["Latitude", "Longitude"], as_index=False)
            .agg(
                n_obs=("Latitude", "size"),
                site=("SiteName", lambda x: x.dropna().iloc[0] if len(x.dropna()) else ""),
                subsite=("SubsiteName", lambda x: x.dropna().iloc[0] if len(x.dropna()) else ""),
                year_min=("Year", "min") if "Year" in map_df.columns else ("Latitude", "size"),
                year_max=("Year", "max") if "Year" in map_df.columns else ("Latitude", "size"),
                n_traits=("Trait", "nunique") if "Trait" in map_df.columns else ("Latitude", "size"),
            )
        )

        if "Year" not in map_df.columns:
            agg["year_min"] = None
            agg["year_max"] = None

        st.caption(f"Raw rows: {len(map_df):,} | Unique locations: {len(agg):,}")

        # 3) Radius scaling (pixels)
        agg["radius_px"] = np.sqrt(agg["n_obs"].clip(lower=1)) * 3 + 2

        # 4) Center map
        center_lat = float(agg["Latitude"].mean())
        center_lon = float(agg["Longitude"].mean())

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=agg,
            get_position="[Longitude, Latitude]",
            radius_units="pixels",
            get_radius="radius_px",
            get_fill_color=[200, 30, 0, 120],
            get_line_color=[200, 30, 0, 200],
            line_width_min_pixels=1,
            pickable=True,           # ✅ required for tooltips
            auto_highlight=True,
        )

        tooltip = {
            "html": """
            <b>Site:</b> {site}<br/>
            <b>Subsite:</b> {subsite}<br/>
            <b>Observations:</b> {n_obs}<br/>
            <b>Traits:</b> {n_traits}<br/>
            <b>Year range:</b> {year_min} – {year_max}<br/>
            <b>Lat/Lon:</b> {Latitude}, {Longitude}
            """,
            "style": {"backgroundColor": "white", "color": "black"},
        }

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(
                latitude=center_lat,
                longitude=center_lon,
                zoom=1.8,
                pitch=0,
            ),
            map_style=None,  # keep simple; switch to a basemap later if you want
            tooltip=tooltip,
        )

        st.pydeck_chart(deck, use_container_width=True)


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

with tab_trait:
    st.header("Trait Overview")

    if "Trait" not in df.columns:
        st.error("Column 'Trait' not found.")
        st.stop()

    # --- Controls ---
    c1, c2 = st.columns([3, 1])
    with c1:
        trait_list = sorted(df["Trait"].dropna().unique())
        selected_trait = st.selectbox("Select a trait", trait_list)
    with c2:
        maxbins = st.slider("Histogram bins", 10, 100, 50, 5)

    trait_df = df[df["Trait"] == selected_trait].copy()

    # Numeric safety
    if "Value" in trait_df.columns:
        trait_df["Value"] = pd.to_numeric(trait_df["Value"], errors="coerce")

    # --- Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows", f"{len(trait_df):,}")
    m2.metric(
        "Species",
        trait_df["AccSpeciesName"].nunique()
        if "AccSpeciesName" in trait_df.columns else 0
    )
    m3.metric(
        "Sites",
        trait_df["SiteName"].nunique()
        if "SiteName" in trait_df.columns else 0
    )
    if "Year" in trait_df.columns and trait_df["Year"].notna().any():
        m4.metric(
            "Year range",
            f"{int(trait_df['Year'].min())} – {int(trait_df['Year'].max())}"
        )
    else:
        m4.metric("Year range", "N/A")

    st.divider()

    # --- Trait coverage across dataset ---
    st.subheader("Which traits are most measured?")
    trait_counts_all = (
        df.dropna(subset=["Trait"])
        .groupby("Trait", as_index=False)
        .size()
        .rename(columns={"size": "n"})
        .sort_values("n", ascending=False)
        .head(30)
    )

    chart_counts = (
        alt.Chart(trait_counts_all)
        .mark_bar()
        .encode(
            y=alt.Y("Trait:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=350)),
            x=alt.X("n:Q", title="Observations"),
            tooltip=["Trait:N", "n:Q"],
        )
        .properties(height=520)
    )
    st.altair_chart(chart_counts, use_container_width=True)

    st.divider()

    # --- Distribution for selected trait ---
    st.subheader("Distribution")

    values = trait_df.dropna(subset=["Value"]).copy()
    if values.empty:
        st.info("No numeric values available for this trait.")
    else:
        unit_label = ""
        if "Units" in values.columns and values["Units"].notna().any():
            unit_label = values["Units"].dropna().iloc[0]

        hist = (
            alt.Chart(values)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Value:Q",
                    bin=alt.Bin(maxbins=maxbins),
                    title=f"{selected_trait} ({unit_label})"
                ),
                y=alt.Y("count()", title="Count"),
                tooltip=[alt.Tooltip("count()", title="Count")],
            )
            .properties(height=320)
        )
        st.altair_chart(hist, use_container_width=True)

    st.divider()

    # --- Trait over time (median by year) ---
    if "Year" in trait_df.columns and "Value" in trait_df.columns:
        st.subheader("Trait over time (median by year)")

        yr = trait_df.dropna(subset=["Year", "Value"]).copy()
        if yr.empty:
            st.info("Not enough Year + Value records to show a time trend.")
        else:
            ts = (
                yr.groupby("Year", as_index=False)
                .agg(
                    n=("Value", "count"),
                    median=("Value", "median"),
                    p25=("Value", lambda x: x.quantile(0.25)),
                    p75=("Value", lambda x: x.quantile(0.75)),
                )
                .sort_values("Year")
            )

            band = (
                alt.Chart(ts)
                .mark_area(opacity=0.2)
                .encode(
                    x=alt.X("Year:Q", title="Year"),
                    y=alt.Y("p25:Q", title=None),
                    y2="p75:Q",
                )
            )

            line = (
                alt.Chart(ts)
                .mark_line()
                .encode(
                    x="Year:Q",
                    y=alt.Y("median:Q", title=f"Median {selected_trait}"),
                    tooltip=["Year:Q", "n:Q", "median:Q", "p25:Q", "p75:Q"],
                )
            )

            st.altair_chart(band + line, use_container_width=True)


with tab_spatial:
    st.header("Spatial Coverage")

    map_df = df.dropna(subset=["Latitude", "Longitude"]).copy()
    map_df["Latitude"] = pd.to_numeric(map_df["Latitude"], errors="coerce")
    map_df["Longitude"] = pd.to_numeric(map_df["Longitude"], errors="coerce")
    map_df = map_df.dropna(subset=["Latitude", "Longitude"])

    if map_df.empty:
        st.info("No georeferenced observations available.")
    else:
        # Round for stable grouping
        map_df["lat_r"] = map_df["Latitude"].round(4)
        map_df["lon_r"] = map_df["Longitude"].round(4)

        agg = (
            map_df.groupby(["lat_r", "lon_r"], as_index=False)
            .agg(
                Latitude=("Latitude", "mean"),
                Longitude=("Longitude", "mean"),
                n_obs=("Latitude", "size"),
                site=("SiteName", lambda x: x.dropna().iloc[0] if len(x.dropna()) else ""),
                subsite=("SubsiteName", lambda x: x.dropna().iloc[0] if len(x.dropna()) else ""),
            )
        )

        agg["radius_px"] = np.sqrt(agg["n_obs"].clip(lower=1)) * 1.2 + 1

        center_lat = float(agg["Latitude"].mean())
        center_lon = float(agg["Longitude"].mean())

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=agg,
            get_position="[Longitude, Latitude]",
            radius_units="pixels",
            get_radius="radius_px",
            get_fill_color=[30, 120, 200, 110],
            get_line_color=[30, 120, 200, 180],
            line_width_min_pixels=1,
            pickable=True,
            auto_highlight=True,
        )

        tooltip = {
            "html": """
            <b>Site:</b> {site}<br/>
            <b>Subsite:</b> {subsite}<br/>
            <b>Observations:</b> {n_obs}<br/>
            <b>Lat/Lon:</b> {Latitude}, {Longitude}
            """,
            "style": {"backgroundColor": "white", "color": "black"},
        }

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=1.2, pitch=0),
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip=tooltip,
        )

        st.pydeck_chart(deck, use_container_width=True)

