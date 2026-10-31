"""Cotações e fundamentos: Yahoo Finance (principal) com brapi como reserva (só preço)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import pandas as pd
import requests

from config import cfg
from storage import get_store

TTL_COTACAO = 15 * 60  # segundos


@dataclass
class Quote:
    ticker: str
    nome: str = ""
    preco: float = 0.0
    div_12m: float = 0.0
    pl: float = 0.0
    pvp: float = 0.0
    lpa: float = 0.0
    vpa: float = 0.0
    roe: float = 0.0
    fonte: str = ""
    parcial: bool = False  # True quando veio só preço (sem dividendos/fundamentos)
    erro: str | None = None

    @property
    def ok(self) -> bool:
        return self.preco > 0

    @property
    def dy_pct(self) -> float:
        return self.div_12m / self.preco * 100 if self.preco > 0 else 0.0


def simbolo(ticker: str) -> str:
    """Todos os tipos suportados (Ação, FII, BDR, ETF) negociam na B3 → sufixo .SA no Yahoo."""
    t = ticker.upper().strip()
    return t if "." in t else f"{t}.SA"


def _div_12m(div: pd.Series | None) -> float:
    """Soma dos proventos dos últimos 12 meses corridos (não dos 12 últimos pagamentos)."""
    if div is None or len(div) == 0:
        return 0.0
    corte = pd.Timestamp.now(tz=div.index.tz) - pd.DateOffset(years=1)
    return float(div[div.index >= corte].sum())


def _fetch_yf(ticker: str) -> Quote:
    import yfinance as yf

    t = yf.Ticker(simbolo(ticker))
    info = t.info or {}
    preco = info.get("currentPrice") or info.get("regularMarketPrice")
    if not preco:
        raise ValueError("preço não encontrado no Yahoo Finance")
    return Quote(
        ticker=ticker,
        nome=info.get("longName") or info.get("shortName") or ticker,
        preco=float(preco),
        div_12m=_div_12m(t.dividends),
        pl=float(info.get("trailingPE") or 0),
        pvp=float(info.get("priceToBook") or 0),
        lpa=float(info.get("trailingEps") or 0),
        vpa=float(info.get("bookValue") or 0),
        roe=float(info.get("returnOnEquity") or 0) * 100,
        fonte="yfinance",
    )


def _fetch_brapi(ticker: str) -> Quote:
    token = cfg("BRAPI_TOKEN")
    r = requests.get(
        f"https://brapi.dev/api/quote/{ticker.upper().replace('.SA', '')}",
        params={"token": token} if token else {},
        timeout=6,
    )
    r.raise_for_status()
    resultados = r.json().get("results") or []
    if not resultados:
        raise ValueError("ativo não encontrado na brapi")
    item = resultados[0]
    preco = float(item.get("regularMarketPrice") or 0)
    if preco <= 0:
        raise ValueError("preço indisponível na brapi")
    return Quote(ticker=ticker, nome=item.get("shortName") or ticker, preco=preco, fonte="brapi", parcial=True)


def _fetch(ticker: str) -> Quote:
    try:
        return _fetch_yf(ticker)
    except Exception as e_yf:
        try:
            return _fetch_brapi(ticker)
        except Exception as e_brapi:
            return Quote(ticker=ticker, erro=f"yfinance: {e_yf} | brapi: {e_brapi}")


def _from_payload(payload: dict) -> Quote | None:
    try:
        return Quote(**payload)
    except TypeError:  # formato antigo no cache
        return None


def get_quotes(tickers, force: bool = False) -> dict[str, Quote]:
    """Busca várias cotações em paralelo. Usa o cache do banco; falhas nunca são cacheadas."""
    unicos = list(dict.fromkeys(t.upper().strip() for t in tickers if t and str(t).strip()))
    store = get_store()
    cache = {} if force else store.cache_fresh(TTL_COTACAO)

    saida: dict[str, Quote] = {}
    faltam: list[str] = []
    for t in unicos:
        q = _from_payload(cache[simbolo(t)]) if simbolo(t) in cache else None
        if q:
            saida[t] = q
        else:
            faltam.append(t)

    if faltam:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for t, q in zip(faltam, ex.map(_fetch, faltam)):
                saida[t] = q
                if q.ok and not q.parcial:
                    store.cache_put(simbolo(t), asdict(q))
    return saida


def historico(ticker: str, periodo: str = "1y") -> pd.DataFrame:
    """Fechamentos diários. Levanta ValueError se vier vazio (para o cache da tela não guardar falhas)."""
    import yfinance as yf

    h = yf.Ticker(simbolo(ticker)).history(period=periodo)
    if h.empty:
        raise ValueError("histórico indisponível")
    return h[["Close"]]
