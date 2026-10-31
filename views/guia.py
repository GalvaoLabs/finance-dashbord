import streamlit as st

import ui

GUIA = """
**1 · Carteira.** Cadastre ticker, categoria, quantidade e preço médio. *Salvar e processar* grava a carteira
no banco e busca cotações, dividendos dos últimos 12 meses e fundamentos.

**2 · Preço teto.** O *teto médio* é a média dos modelos aplicáveis:
- **Bazin:** dividendos de 12 meses ÷ DY alvo.
- **Graham (só ações):** √(22,5 × LPA × VPA).
- **Gordon:** dividendo × (1+g) ÷ (k−g), com g = 3% e k = 10%.

A **margem de segurança** é (teto − preço) ÷ teto. Positiva = preço abaixo do teto.

**3 · Comparador.** Vários tickers da mesma categoria lado a lado.

**4 · Aportes.** Distribui um valor entre os ativos abaixo do teto, proporcional à margem.

**5 · IA.** Relatório em Markdown sobre diversificação e pontos de atenção.

**Fontes:** Yahoo Finance (principal), brapi (reserva, só preço) e Banco Central (Selic, CDI, IPCA).
"""


def render():
    ui.cabecalho("Guia", "Como ler os números.")
    st.markdown(GUIA)
    st.caption(
        "Conteúdo educacional. Os tetos são modelos simplificados e não constituem recomendação de investimento; "
        "consulte um profissional habilitado."
    )
