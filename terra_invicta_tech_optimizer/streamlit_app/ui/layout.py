from __future__ import annotations

import streamlit as st


def render_global_styles() -> None:
    st.markdown(
        """
        <style>
        /* Reduce default padding */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        /* Hide Streamlit's default header */
        header[data-testid="stHeader"] {
            display: none;
        }

        /* Sticky left sidebar - target horizontal block children */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            position: sticky;
            top: 1rem;
            align-self: flex-start;
            height: fit-content;
            z-index: 100;
        }

        /* Hide the search hidden input container completely */
        .search-hidden-container {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            padding: 0 !important;
            margin: -1px !important;
            overflow: hidden !important;
            clip: rect(0, 0, 0, 0) !important;
            white-space: nowrap !important;
            border: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
