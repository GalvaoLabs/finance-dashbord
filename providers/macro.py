"""Indicadores macro do Banco Central (SGS): API oficial, gratuita e sem chave."""
from __future__ import annotations

import time

import requests

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados/ultimos/1?formato=json"
SERIES = {"Selic meta": 432, "CDI": 4389, "IPCA 12m": 13522}  # códigos do SGS
TTL = 6 * 3600

_cache: dict[int, tuple[float, float]] = {}  # código → (instante, valor); só guarda sucessos


def _serie(codigo: int) -> float:
    hit = _cache.get(codigo)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    r = requests.get(URL.format(codigo), timeout=6)
    r.raise_for_status()
    valor = float(r.json()[-1]["valor"])
    _cache[codigo] = (time.time(), valor)
    return valor


def indicadores() -> dict[str, float]:
    """Retorna o que conseguir buscar; séries que falharem são omitidas (a tela se adapta)."""
    saida = {}
    for nome, codigo in SERIES.items():
        try:
            saida[nome] = _serie(codigo)
        except Exception:
            pass
    return saida
