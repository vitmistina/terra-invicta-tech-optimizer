from __future__ import annotations

import streamlit as st

from terra_invicta_tech_optimizer import (
    GraphExplorer,
    GraphValidator,
    InputLoader,
    build_flat_node_list,
    build_graph_data,
)

from .config import INPUT_DIR


def _load_inputs(reload_token: int):
    loader = InputLoader(INPUT_DIR)
    return loader.load()


@st.cache_data(show_spinner=False)
def load_inputs(reload_token: int):
    return _load_inputs(reload_token)


def validate_graph(nodes):
    return GraphValidator(nodes).validate()


def get_models(nodes):
    reload_token = st.session_state.get("reload_token", 0)
    models_state = st.session_state.get("models")

    if models_state and models_state.get("token") == reload_token:
        return models_state["graph_data"], models_state["flat_list"]

    graph_data = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph_data, nodes)
    st.session_state.models = {
        "token": reload_token,
        "graph_data": graph_data,
        "flat_list": flat_list,
    }
    return graph_data, flat_list


def get_explorer(nodes):
    reload_token = st.session_state.get("reload_token", 0)
    explorer_state = st.session_state.get("explorer")

    if explorer_state and explorer_state.get("token") == reload_token:
        return explorer_state["instance"]

    explorer = GraphExplorer(nodes)
    st.session_state.explorer = {"instance": explorer, "token": reload_token}
    return explorer
