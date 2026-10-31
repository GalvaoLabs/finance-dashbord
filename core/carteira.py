"""Processamento da carteira e simulação de aportes. Sem I/O: recebe dados prontos."""
from __future__ import annotations

import math

import pandas as pd

from core.valuation import analisar

TIPOS = ["Ação", "FII", "BDR", "ETF"]
COLUNAS = ["Ticker", "Tipo", "Quantidade", "Preço Médio"]

EXEMPLO = pd.DataFrame(
    [
        ("BBAS3", "Ação", 100, 24.50),
        ("VALE3", "Ação", 50, 62.00),
        ("MXRF11", "FII", 300, 10.15),
        ("HGLG11", "FII", 20, 160.00),
        ("AAPL34", "BDR", 30, 42.00),
    ],
    columns=COLUNAS,
)


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a tabela digitada: tickers em maiúsculas, sem vazios nem duplicados, números válidos."""
    d = df.copy()
    for c in COLUNAS:
        if c not in d:
            d[c] = None
    d["Ticker"] = d["Ticker"].fillna("").astype(str).str.upper().str.strip()
    d = d[d["Ticker"] != ""].copy()
    d["Tipo"] = d["Tipo"].where(d["Tipo"].isin(TIPOS), "Ação")
    for c in ("Quantidade", "Preço Médio"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    return d.drop_duplicates("Ticker", keep="last")[COLUNAS].reset_index(drop=True)


def processar(posicoes: pd.DataFrame, cotacoes: dict, dy_alvo: float = 0.06) -> tuple[pd.DataFrame, list[str]]:
    """Cruza posições com cotações. Retorna (tabela, lista de erros por ticker)."""
    linhas, erros = [], []
    for p in limpar(posicoes).to_dict("records"):
        t, tipo, qtd, pm = p["Ticker"], p["Tipo"], p["Quantidade"], p["Preço Médio"]
        q = cotacoes.get(t)
        if q is None or not q.ok:
            erros.append(f"{t}: {getattr(q, 'erro', None) or 'sem dados'}")
            continue
        v = analisar(q.preco, q.div_12m, q.lpa, q.vpa, tipo, dy_alvo)
        investido, atual = qtd * pm, qtd * q.preco
        linhas.append(
            {
                "Ticker": t,
                "Tipo": tipo,
                "Qtd": qtd,
                "P. Médio": pm,
                "P. Atual": q.preco,
                "Investido": investido,
                "Valor Atual": atual,
                "Resultado (R$)": atual - investido,
                "Rentab. (%)": (atual - investido) / investido * 100 if investido > 0 else 0.0,
                "Div. 12M": q.div_12m,
                "DY (%)": q.dy_pct,
                "Teto Bazin": v.bazin or None,
                "Teto Graham": v.graham or None,
                "Teto Médio": v.medio or None,
                "Margem Seg. (%)": v.margem,
                "Status": v.status,
                "Parcial": q.parcial,
            }
        )
    return pd.DataFrame(linhas), erros


def resumo(df: pd.DataFrame) -> dict[str, float]:
    investido, atual = df["Investido"].sum(), df["Valor Atual"].sum()
    return {
        "patrimonio": atual,
        "investido": investido,
        "resultado": atual - investido,
        "rentabilidade": (atual - investido) / investido * 100 if investido > 0 else 0.0,
        "renda_anual": (df["Qtd"] * df["Div. 12M"]).sum(),
    }


def simular_aporte(df: pd.DataFrame, valor: float) -> pd.DataFrame:
    """Distribui o aporte entre ativos abaixo do teto, proporcional à margem de segurança."""
    el = df[df["Margem Seg. (%)"] > 0].sort_values("Margem Seg. (%)", ascending=False).copy()
    if el.empty:
        return el
    el["Peso (%)"] = el["Margem Seg. (%)"] / el["Margem Seg. (%)"].sum() * 100
    el["Valor Sugerido (R$)"] = (el["Peso (%)"] / 100 * valor).round(2)
    el["Qtd. Sugerida"] = el.apply(lambda r: math.floor(r["Valor Sugerido (R$)"] / r["P. Atual"]), axis=1)
    return el
