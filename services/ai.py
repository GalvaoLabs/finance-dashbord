"""Relatório de carteira via Gemini (SDK atual: google-genai)."""
from __future__ import annotations

import pandas as pd

MODELO_PADRAO = "gemini-2.5-flash"  # troque pela variável GEMINI_MODEL sem mexer no código

PROMPT = """Você é um analista financeiro sênior do mercado brasileiro.
Avalie a carteira abaixo (valores em R$; "Margem Seg." é a folga em relação ao preço teto médio).

{tabela}

Responda em Markdown, com estas seções:
1. Risco e diversificação
2. Onde há folga em relação ao preço teto
3. Ativos que pedem acompanhamento
4. Pontos a considerar nos próximos aportes

Termine dizendo que este texto foi gerado por IA, é educacional e não é recomendação de investimento."""


def relatorio(df: pd.DataFrame, api_key: str, modelo: str = MODELO_PADRAO) -> str:
    from google import genai

    colunas = ["Ticker", "Tipo", "Valor Atual", "Rentab. (%)", "DY (%)", "Margem Seg. (%)", "Status"]
    tabela = df[colunas].round(2).to_string(index=False)
    resposta = genai.Client(api_key=api_key).models.generate_content(model=modelo, contents=PROMPT.format(tabela=tabela))
    return resposta.text
