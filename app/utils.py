import os
import json
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import requests
import streamlit as st

RAW_URL = (
    "https://raw.githubusercontent.com/TundraTraitTeam/TraitHub/master/"
    "data_clean/TTT_cleaned_dataset.csv"
)

DATA_DIR = Path("data/raw")
LOCAL_CSV = DATA_DIR / "TTT_cleaned_dataset.csv"
META_FILE = DATA_DIR / "TTT_cleaned_dataset.meta.json"


def _load_meta() -> Dict[str, str]:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_meta(meta: Dict[str, str]) -> None:
    META_FILE.write_text(json.dumps(meta, indent=2))


def fetch_csv_if_needed(url: str, local_path: Path) -> Path:
    """
    Download CSV from `url` to `local_path` if missing or if remote changed.
    Uses ETag / Last-Modified conditional requests when available.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    meta = _load_meta()
    headers = {}

    # Conditional GET headers
    if "etag" in meta:
        headers["If-None-Match"] = meta["etag"]
    if "last_modified" in meta:
        headers["If-Modified-Since"] = meta["last_modified"]

    # If file doesn't exist, force fetch
    must_fetch = not local_path.exists()

    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)

        if resp.status_code == 304 and not must_fetch:
            # Not modified; keep local copy
            return local_path

        resp.raise_for_status()

        # Save content
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        # Update meta
        new_meta = {}
        if "ETag" in resp.headers:
            new_meta["etag"] = resp.headers["ETag"]
        if "Last-Modified" in resp.headers:
            new_meta["last_modified"] = resp.headers["Last-Modified"]
        new_meta["source_url"] = url
        _save_meta(new_meta)

        return local_path

    except Exception as e:
        # Fallback: if download fails but local exists, proceed with local
        if local_path.exists():
            st.warning(
                f"Could not refresh dataset from source ({e}). "
                "Using the last cached local copy."
            )
            return local_path
        raise RuntimeError(f"Failed to download dataset and no local cache exists: {e}")
