import pandas as pd
import plotly.express as px
import streamlit as st

import ui
from core import carteira as cart
from core.valuation import analisar
from providers import market


def render():
    ui.cabecalho("Comparador", "Múltiplos e preços teto de vários ativos lado a lado.")
    c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="bottom")
    texto = c1.text_input("Tickers (separados por vírgula)", "BBAS3, ITSA4, SANB11, CXSE3")
    tipo = c2.selectbox("Categoria", cart.TIPOS)
    dy = c3.number_input("DY alvo (%)", min_value=1.0, value=6.0, step=0.5) / 100

    if not st.button("Comparar", type="primary"):
        return

    tickers = [t.strip().upper() for t in texto.split(",") if t.strip()]
    with st.spinner("Buscando dados..."):
        cotacoes = market.get_quotes(tickers)

    linhas, falhas = [], []
    for t in tickers:
        q = cotacoes[t]
        if not q.ok:
            falhas.append(t)
            continue
        v = analisar(q.preco, q.div_12m, q.lpa, q.vpa, tipo, dy)
        linhas.append(
            {"Ticker": t, "Preço": q.preco, "DY (%)": q.dy_pct, "P/L": q.pl or None, "P/VP": q.pvp or None,
             "ROE (%)": q.roe, "Teto Bazin": v.bazin or None, "Teto Graham": v.graham or None,
             "Margem Seg. (%)": v.margem, "Status": v.status}
        )
    if falhas:
        st.warning("Sem dados para: " + ", ".join(falhas))
    if not linhas:
        return

    df = pd.DataFrame(linhas)
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "Preço": st.column_config.NumberColumn(format="R$ %.2f"),
            "Teto Bazin": st.column_config.NumberColumn(format="R$ %.2f"),
            "Teto Graham": st.column_config.NumberColumn(format="R$ %.2f"),
            "Margem Seg. (%)": st.column_config.ProgressColumn(min_value=-30, max_value=30, format="%.1f%%"),
        },
    )
    st.plotly_chart(px.bar(df, x="Ticker", y="DY (%)", title="Dividend Yield"))
