import plotly.graph_objects as go
import streamlit as st

import ui
from core import carteira as cart
from core.valuation import analisar
from providers import market


@st.cache_data(ttl=900, show_spinner=False)
def _historico(ticker: str):
    return market.historico(ticker, "1y")  # erro não é cacheado


def render():
    ui.cabecalho("Valuation individual", "Preço teto por Bazin, Graham e Gordon para um ativo.")
    c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
    ticker = c1.text_input("Ticker", "BBAS3").upper().strip()
    tipo = c2.selectbox("Categoria", cart.TIPOS)
    dy = c3.number_input("DY alvo (%)", min_value=1.0, value=6.0, step=0.5) / 100

    if not st.button("Executar valuation", type="primary") or not ticker:
        return

    with st.spinner("Buscando dados..."):
        q = market.get_quotes([ticker])[ticker]
    if not q.ok:
        st.error(f"Não foi possível obter {ticker}: {q.erro}")
        return

    v = analisar(q.preco, q.div_12m, q.lpa, q.vpa, tipo, dy)
    st.subheader(f"{q.nome or ticker} · {v.status}")
    st.caption(f"Fonte: {q.fonte}" + (" — somente preço; sem dividendos, os tetos não podem ser calculados." if q.parcial else ""))

    brl = lambda x: ui.brl(x) if x > 0 else "N/A"  # noqa: E731
    ui.kpis(
        [
            ("Preço atual", ui.brl(q.preco), ""),
            (f"Teto Bazin ({ui.num(dy * 100, 1)}%)", brl(v.bazin), ""),
            ("Teto Graham", brl(v.graham), "só ações"),
            ("Teto Gordon", brl(v.gordon), "g=3%, k=10%"),
            ("Teto médio", brl(v.medio), f"Margem {ui.num(v.margem)}%", "pos" if v.margem >= 0 else "neg"),
        ]
    )

    m = st.columns(5)
    for col, (nome, valor) in zip(m, [("P/L", q.pl), ("P/VP", q.pvp), ("DY", q.dy_pct), ("LPA", q.lpa), ("ROE", q.roe)]):
        col.metric(nome, ui.num(valor) if valor else "N/A")

    try:
        hist = _historico(ticker)
    except Exception:
        st.info("Histórico indisponível para este ativo.")
        return
    fig = go.Figure(go.Scatter(x=hist.index, y=hist["Close"], name="Fechamento", line=dict(width=2)))
    for nome, teto, tracado in (("Bazin", v.bazin, "dash"), ("Graham", v.graham, "dot")):
        if teto > 0:
            fig.add_hline(y=teto, line_dash=tracado, annotation_text=f"Teto {nome}")
    fig.update_layout(title="Últimos 12 meses", margin=dict(t=50, l=0, r=0, b=0))
    st.plotly_chart(fig)
