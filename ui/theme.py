"""Shared Streamlit visual theme helpers."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


def apply_space_background() -> None:
    """Apply a scrolling star field that reveals an Earth cutaway lower down."""
    project_root = Path(__file__).resolve().parents[1]
    asset_candidates = (
        project_root / "assets" / "scrolling_earth_cutaway.jpg",
        Path.cwd() / "assets" / "scrolling_earth_cutaway.jpg",
        project_root / "assets" / "deep_space_background.jpg",
        Path.cwd() / "assets" / "deep_space_background.jpg",
    )
    image_path = next((path for path in asset_candidates if path.is_file()), None)
    if image_path is None:
        st.warning(
            "Hintergrundbild nicht gefunden. Erwartet wurde "
            f"{asset_candidates[0]} oder {asset_candidates[1]}."
        )
        return
    try:
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    except OSError as exc:
        st.warning(f"Hintergrundbild {image_path} konnte nicht gelesen werden: {exc}")
        return

    # st.html injects style tags into the page DOM; markdown may sanitize or
    # isolate them depending on the Streamlit version.
    st.html(
        f"""
        <style>
        .stApp {{
            background: #03050c !important;
            min-height: 100vh;
            position: relative;
            overflow: visible;
        }}
        .stApp::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            min-height: 300vh;
            z-index: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(3, 5, 12, 0.28), rgba(3, 5, 12, 0.32)),
                url("data:image/jpeg;base64,{image_data}");
            background-size: cover, cover;
            background-position: center top;
            background-repeat: no-repeat;
        }}
        .stAppViewContainer,
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {{
            background: transparent !important;
        }}
        .stAppViewContainer {{
            position: relative;
            z-index: 1;
        }}
        header[data-testid="stHeader"] {{
            background: rgba(3, 5, 12, 0.20) !important;
            position: relative;
            z-index: 2;
        }}
        </style>
        """
    )
