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