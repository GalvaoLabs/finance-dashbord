import plotly.express as px
import streamlit as st

import ui
from core import carteira as cart


def render():
    ui.cabecalho("Simulador de aportes", "Divide um novo aporte entre os ativos da carteira que estão abaixo do teto.")
    df = st.session_state.get("df_carteira")
    if df is None:
        st.info("Processe sua carteira na página **Carteira** primeiro.")
        return

    valor = st.number_input("Valor do aporte (R$)", min_value=0.0, value=1000.0, step=100.0)
    sugestao = cart.simular_aporte(df, valor)
    if sugestao.empty:
        st.warning("Nenhum ativo está abaixo do preço teto no momento.")
        return

    st.dataframe(
        sugestao[["Ticker", "Tipo", "P. Atual", "Margem Seg. (%)", "Peso (%)", "Valor Sugerido (R$)", "Qtd. Sugerida"]],
        hide_index=True,
        column_config={
            "P. Atual": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor Sugerido (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Peso (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
        },
    )
    st.caption("Simulação simplificada: usa só a margem atual, sem diversificação-alvo, correlação nem perfil de risco.")
    st.plotly_chart(px.pie(sugestao, values="Valor Sugerido (R$)", names="Ticker", hole=0.5, title="Distribuição sugerida"))
