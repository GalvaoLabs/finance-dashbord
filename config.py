"""Leitura de configuração: variável de ambiente primeiro, depois st.secrets."""
from __future__ import annotations

import os


def cfg(name: str, default: str | None = None) -> str | None:
    if value := os.getenv(name):
        return value
    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:  # sem secrets.toml, sem streamlit (testes) etc.
        return default
