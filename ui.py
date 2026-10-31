"""Componentes visuais compartilhados pelas telas."""
from __future__ import annotations

import hmac
from html import escape
from pathlib import Path

import streamlit as st

from config import cfg

RAIZ = Path(__file__).parent


def num(x: float, casas: int = 2) -> str:
    """Formato brasileiro: 1.234,56."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl(x: float) -> str:
    return f"R$ {num(x)}"


def carregar_css() -> None:
    css = (RAIZ / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def cabecalho(titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f'<div class="cabecalho"><h1>{escape(titulo)}</h1><p>{escape(subtitulo)}</p></div>', unsafe_allow_html=True
    )


def kpis(itens: list[tuple]) -> None:
    """Cada item: (rótulo, valor, subtexto) ou (rótulo, valor, subtexto, 'pos'|'neg')."""
    cartoes = ""
    for rotulo, valor, sub, *tom in itens:
        cartoes += (
            f'<div class="kpi {tom[0] if tom else ""}"><div class="l">{escape(rotulo)}</div>'
            f'<div class="v">{escape(valor)}</div><div class="s">{escape(sub)}</div></div>'
        )
    st.markdown(f'<div class="kpis">{cartoes}</div>', unsafe_allow_html=True)


def chips(indicadores: dict[str, float]) -> None:
    html = "".join(f'<span class="chip">{escape(k)}<b>{num(v)}%</b></span>' for k, v in indicadores.items())
    st.markdown(f'<div class="chips">{html}</div>', unsafe_allow_html=True)


def autenticado() -> bool:
    """Se APP_PASSWORD estiver definida, exige senha. Sem ela, o app fica aberto."""
    senha = cfg("APP_PASSWORD")
    if not senha or st.session_state.get("_auth"):
        return True
    cabecalho("Plataforma de Análise Financeira", "Acesso restrito.")
    with st.form("login"):
        tentativa = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            if hmac.compare_digest(tentativa.encode(), str(senha).encode()):
                st.session_state["_auth"] = True
                st.rerun()
            st.error("Senha incorreta.")
    return False
