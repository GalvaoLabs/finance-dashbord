import time
from dataclasses import asdict

import pandas as pd
import pytest

import storage
from core import carteira as cart
from providers import macro, market
from providers.market import Quote


@pytest.fixture
def store(tmp_path, monkeypatch):
    s = storage.Store(f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setattr(market, "get_store", lambda: s)
    return s


def test_posicoes_ida_e_volta(store):
    assert store.load_posicoes().empty
    store.save_posicoes(cart.EXEMPLO)
    assert len(store.load_posicoes()) == 5
    store.save_posicoes(pd.DataFrame([("PETR4", "Ação", 10, 30.0)], columns=cart.COLUNAS))  # substitui tudo
    d = store.load_posicoes()
    assert list(d["Ticker"]) == ["PETR4"] and d.loc[0, "Preço Médio"] == 30.0


def test_cache_respeita_ttl(store):
    store.cache_put("X.SA", {"a": 1})
    assert store.cache_fresh(60) == {"X.SA": {"a": 1}}
    time.sleep(0.05)
    assert store.cache_fresh(0.01) == {}
    store.cache_put("X.SA", {"a": 2})  # sobrescreve
    assert store.cache_fresh(60)["X.SA"] == {"a": 2}


def test_div_12m_conta_por_data_e_nao_por_pagamentos():
    hoje = pd.Timestamp.now(tz="America/Sao_Paulo")
    idx = [hoje - pd.DateOffset(months=m) for m in (1, 3, 5, 7, 9, 11, 14, 20)]
    serie = pd.Series([1.0] * 8, index=pd.DatetimeIndex(idx))
    assert market._div_12m(serie) == 6.0  # 6 dentro de 12 meses (tail(12) daria 8)
    assert market._div_12m(None) == 0.0 and market._div_12m(pd.Series([], dtype=float)) == 0.0
    sem_tz = pd.Series([2.0], index=pd.DatetimeIndex([pd.Timestamp.now() - pd.DateOffset(months=2)]))
    assert market._div_12m(sem_tz) == 2.0


def test_get_quotes_cache_falha_e_paralelo(store, monkeypatch):
    chamadas = []

    def fake(t):
        chamadas.append(t)
        if t == "RUIM3":
            return Quote(t, erro="x")
        return Quote(t, preco=10.0, div_12m=1.0, fonte="yfinance")

    monkeypatch.setattr(market, "_fetch", fake)
    r1 = market.get_quotes(["bbas3", "RUIM3", "bbas3", ""])
    assert set(r1) == {"BBAS3", "RUIM3"} and r1["BBAS3"].ok and not r1["RUIM3"].ok

    market.get_quotes(["BBAS3", "RUIM3"])
    assert chamadas.count("BBAS3") == 1  # sucesso veio do cache
    assert chamadas.count("RUIM3") == 2  # falha NÃO foi cacheada (bug do original)

    market.get_quotes(["BBAS3"], force=True)
    assert chamadas.count("BBAS3") == 2


def test_parcial_nao_vai_para_cache(store, monkeypatch):
    monkeypatch.setattr(market, "_fetch", lambda t: Quote(t, preco=5.0, fonte="brapi", parcial=True))
    market.get_quotes(["ABCD3"])
    assert store.cache_fresh(60) == {}


def test_fallback_brapi(monkeypatch):
    def yf_falha(t):
        raise RuntimeError("429")

    class R:
        def raise_for_status(self): pass
        def json(self): return {"results": [{"regularMarketPrice": 12.5, "shortName": "Foo"}]}

    monkeypatch.setattr(market, "_fetch_yf", yf_falha)
    monkeypatch.setattr(market.requests, "get", lambda *a, **k: R())
    q = market._fetch("FOO3")
    assert q.ok and q.preco == 12.5 and q.fonte == "brapi" and q.parcial

    monkeypatch.setattr(market.requests, "get", lambda *a, **k: (_ for _ in ()).throw(OSError("rede")))
    q = market._fetch("FOO3")
    assert not q.ok and "yfinance" in q.erro and "brapi" in q.erro


def test_payload_antigo_e_ignorado():
    assert market._from_payload({"campo_inexistente": 1}) is None
    assert market._from_payload(asdict(Quote("A", preco=1.0))).preco == 1.0


def test_macro_tolera_falhas_e_cacheia_sucesso(monkeypatch):
    macro._cache.clear()
    n = {"c": 0}

    def get(url, timeout):
        n["c"] += 1
        if "sgs.4389" in url:
            raise OSError("fora")

        class R:
            def raise_for_status(self): pass
            def json(self): return [{"data": "01/01/2026", "valor": "10,5".replace(",", ".")}]

        return R()

    monkeypatch.setattr(macro.requests, "get", get)
    r = macro.indicadores()
    assert set(r) == {"Selic meta", "IPCA 12m"} and r["Selic meta"] == 10.5
    macro.indicadores()
    assert n["c"] == 3 + 1  # 2 sucessos cacheados; só o CDI (falha) é tentado de novo
