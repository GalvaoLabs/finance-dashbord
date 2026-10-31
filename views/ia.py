import streamlit as st

import ui
from config import cfg
from services import ai


def render():
    ui.cabecalho("Análise com IA", "Relatório de diversificação e oportunidades gerado pelo Gemini.")
    df = st.session_state.get("df_carteira")
    if df is None:
        st.info("Processe sua carteira na página **Carteira** primeiro.")
        return

    chave = cfg("GEMINI_API_KEY") or st.text_input(
        "Chave da API Gemini", type="password", help="Grátis em aistudio.google.com/app/apikey. Não é salva."
    )
    modelo = cfg("GEMINI_MODEL", ai.MODELO_PADRAO)
    st.caption(
        f"Modelo: `{modelo}`. Os dados da carteira são enviados ao Google; na camada gratuita, "
        "confira nos termos do Gemini API se o conteúdo pode ser usado para melhorar produtos."
    )
    st.dataframe(df[["Ticker", "Tipo", "Valor Atual", "Rentab. (%)", "DY (%)", "Status"]], hide_index=True)

    if st.button("Gerar relatório", type="primary"):
        if not chave:
            st.error("Informe a chave da API.")
        else:
            try:
                with st.spinner("Gerando análise..."):
                    st.session_state["relatorio_ia"] = ai.relatorio(df, chave, modelo)
            except Exception as e:
                st.error(f"Erro ao chamar o Gemini: {e}")

    if texto := st.session_state.get("relatorio_ia"):
        st.markdown(texto)
        st.download_button("Baixar (Markdown)", texto, "relatorio_ia.md", "text/markdown")
