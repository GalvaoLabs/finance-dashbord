import plotly.express as px
import streamlit as st

import ui
from core import carteira as cart
from providers import macro, market
from storage import get_store


def render():
    ui.cabecalho("Carteira", "Posições, resultado, renda passiva e folga em relação ao preço teto.")
    if indicadores := macro.indicadores():
        ui.chips(indicadores)

    base = get_store().load_posicoes()
    editada = st.data_editor(
        base if not base.empty else cart.EXEMPLO,
        num_rows="dynamic",
        hide_index=True,
        key="editor_carteira",
        column_config={
            "Tipo": st.column_config.SelectboxColumn(options=cart.TIPOS, required=True),
            "Quantidade": st.column_config.NumberColumn(min_value=0, step=1),
            "Preço Médio": st.column_config.NumberColumn(min_value=0.0, format="R$ %.2f"),
        },
    )

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    dy = c1.slider("DY alvo (Bazin)", 2.0, 15.0, 6.0, 0.5, format="%.1f%%") / 100
    force = c2.toggle("Ignorar cache", help="Busca cotações novas mesmo que haja dados recentes salvos.")

    if st.button("Salvar e processar", type="primary"):
        with st.spinner("Buscando cotações..."):
            posicoes = cart.limpar(editada)
            get_store().save_posicoes(posicoes)
            cotacoes = market.get_quotes(posicoes["Ticker"], force)
            df, erros = cart.processar(posicoes, cotacoes, dy)
        if erros:
            st.warning("Sem dados para: " + "; ".join(erros))
        st.session_state["df_carteira"] = df if not df.empty else None

    df = st.session_state.get("df_carteira")
    if df is None:
        st.info("Edite a tabela e clique em **Salvar e processar**.")
        return

    r = cart.resumo(df)
    sinal = "pos" if r["resultado"] >= 0 else "neg"
    ui.kpis(
        [
            ("Patrimônio atual", ui.brl(r["patrimonio"]), f"Rentabilidade {ui.num(r['rentabilidade'])}%", sinal),
            ("Total investido", ui.brl(r["investido"]), "Custo histórico"),
            ("Resultado", ui.brl(r["resultado"]), "Ganho de capital", sinal),
            ("Renda passiva anual", ui.brl(r["renda_anual"]), f"≈ {ui.brl(r['renda_anual'] / 12)} por mês"),
        ]
    )
    if df["Parcial"].any():
        parciais = ", ".join(df.loc[df["Parcial"], "Ticker"])
        st.caption(f"⚠️ {parciais}: só o preço foi obtido (fonte reserva, sem dividendos). Tetos e renda ficam subestimados.")

    st.dataframe(
        df.drop(columns="Parcial"),
        hide_index=True,
        column_config={
            "Margem Seg. (%)": st.column_config.ProgressColumn(min_value=-30, max_value=30, format="%.1f%%"),
            "Rentab. (%)": st.column_config.NumberColumn(format="%.2f%%"),
            **{c: st.column_config.NumberColumn(format="R$ %.2f") for c in
               ("P. Médio", "P. Atual", "Investido", "Valor Atual", "Resultado (R$)", "Div. 12M", "Teto Bazin", "Teto Graham", "Teto Médio")},
        },
    )
    st.download_button(
        "Exportar CSV", df.to_csv(index=False, sep=";", decimal=","), "carteira.csv", "text/csv"
    )

    g1, g2 = st.columns(2)
    g1.plotly_chart(px.pie(df, values="Valor Atual", names="Tipo", hole=0.5, title="Patrimônio por categoria"))
    g2.plotly_chart(
        px.bar(df, x="Ticker", y=["P. Atual", "Teto Médio"], barmode="group", title="Preço atual × teto médio")
    )
    st.plotly_chart(
        px.treemap(df, path=["Tipo", "Ticker"], values="Valor Atual", color="Rentab. (%)",
                   color_continuous_scale="RdYlGn", color_continuous_midpoint=0, title="Composição por ativo")
    )
