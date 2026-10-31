import streamlit as st

import ui
from views import aportes, ativo, carteira, comparador, guia, ia

st.set_page_config(page_title="Plataforma de Análise Financeira", page_icon="assets/logo.png", layout="wide")
ui.carregar_css()
st.logo("assets/logo.png")

if ui.autenticado():
    st.navigation(
        [
            st.Page(carteira.render, title="Carteira", url_path="carteira", icon=":material/account_balance_wallet:", default=True),
            st.Page(ativo.render, title="Valuation", url_path="valuation", icon=":material/query_stats:"),
            st.Page(comparador.render, title="Comparador", url_path="comparador", icon=":material/compare_arrows:"),
            st.Page(aportes.render, title="Aportes", url_path="aportes", icon=":material/savings:"),
            st.Page(ia.render, title="Análise com IA", url_path="ia", icon=":material/auto_awesome:"),
            st.Page(guia.render, title="Guia", url_path="guia", icon=":material/menu_book:"),
        ]
    ).run()
