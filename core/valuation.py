"""Modelos de preço teto (Bazin, Graham, Gordon). Funções puras, sem I/O."""
from __future__ import annotations

from dataclasses import dataclass

ABAIXO, PROXIMO, ACIMA, SEM_DADOS = "Abaixo do teto", "Próximo do teto", "Acima do teto", "Sem dados"


def bazin(div_12m: float, dy_alvo: float = 0.06) -> float:
    """Preço teto = dividendos dos últimos 12 meses ÷ DY desejado."""
    return div_12m / dy_alvo if dy_alvo > 0 and div_12m > 0 else 0.0


def graham(lpa: float, vpa: float) -> float:
    """Valor justo = √(22,5 × LPA × VPA). Só faz sentido com lucro e patrimônio positivos."""
    return (22.5 * lpa * vpa) ** 0.5 if lpa > 0 and vpa > 0 else 0.0


def gordon(div_12m: float, g: float = 0.03, k: float = 0.10) -> float:
    """Dividend Discount Model com crescimento constante."""
    return div_12m * (1 + g) / (k - g) if k > g and div_12m > 0 else 0.0


def media(*tetos: float) -> float:
    validos = [t for t in tetos if t and t > 0]
    return sum(validos) / len(validos) if validos else 0.0


def margem(preco: float, teto: float) -> float:
    """Margem de segurança clássica, em %: (teto − preço) ÷ teto."""
    return (teto - preco) / teto * 100 if preco > 0 and teto > 0 else 0.0


def classificar(preco: float, teto: float) -> str:
    if preco <= 0 or teto <= 0:
        return SEM_DADOS
    m = margem(preco, teto)
    return ABAIXO if m >= 0 else PROXIMO if m >= -10 else ACIMA


@dataclass(frozen=True)
class Valuation:
    bazin: float
    graham: float
    gordon: float
    medio: float
    margem: float
    status: str


def analisar(preco: float, div_12m: float, lpa: float, vpa: float, tipo: str, dy_alvo: float = 0.06) -> Valuation:
    """Aplica todos os modelos aplicáveis ao tipo de ativo (Graham só para ações)."""
    b = bazin(div_12m, dy_alvo)
    gr = graham(lpa, vpa) if tipo == "Ação" else 0.0
    gd = gordon(div_12m)
    m = media(b, gr, gd)
    return Valuation(b, gr, gd, m, margem(preco, m), classificar(preco, m))
