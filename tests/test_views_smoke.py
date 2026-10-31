"""Teste de fumaça das telas com Streamlit/Plotly *simulados*.

Pega erros de nome, importação e fluxo (ex.: coluna inexistente, variável não definida).
NÃO valida a API real do Streamlit: para isso, rode `streamlit run app.py` de verdade.
"""
import importlib
import sys
import types

import pytest

from core import carteira as cart
from providers.market import Quote


class Dummy:
    def __call__(self, *a, **k): return Dummy()
    def __getattr__(self, n): return Dummy()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter(())
    def __bool__(self): return True


class Coluna(Dummy):
    """Coluna simulada: widgets delegam às funções simuladas do módulo."""
    def __init__(self, widgets): self._w = widgets
    def __getattr__(self, n): return self._w.get(n, Dummy())


def fake_streamlit(state):
    st = types.ModuleType("streamlit")
    st.session_state = state
    st.secrets = {}
    st.column_config = Dummy()
    st.cache_data = lambda *a, **k: (lambda f: f)
    st.data_editor = lambda df, **k: df
    st.button = lambda *a, **k: True
    st.toggle = lambda *a, **k: False
    st.slider = lambda *a, **k: 6.0
    st.number_input = lambda *a, value=1000.0, **k: value
    st.text_input = lambda label, value="", **k: value or "chave"
    st.selectbox = lambda label, opts, **k: opts[0]
    st.spinner = lambda *a, **k: Dummy()
    widgets = {n: getattr(st, n) for n in
               ("button", "toggle", "slider", "number_input", "text_input", "selectbox")}
    st.columns = lambda spec, **k: [Coluna(widgets) for _ in range(spec if isinstance(spec, int) else len(spec))]
    st.__getattr__ = lambda n: Dummy()  # demais chamadas (markdown, dataframe, caption...)
    return st


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    state = {}
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit(state))
    for nome in ("plotly", "plotly.express", "plotly.graph_objects"):
        monkeypatch.setitem(sys.modules, nome, Dummy())
    sys.modules["plotly"].express = sys.modules["plotly.express"]
    sys.modules["plotly"].graph_objects = sys.modules["plotly.graph_objects"]
    for m in [m for m in sys.modules if m == "ui" or m.startswith("views")]:
        monkeypatch.delitem(sys.modules, m)

    import storage
    from providers import market, macro

    loja = storage.Store(f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setattr(storage, "get_store", lambda: loja)
    monkeypatch.setattr(market, "get_store", lambda: loja)
    monkeypatch.setattr(macro, "indicadores", lambda: {"Selic meta": 14.5})
    monkeypatch.setattr(
        market, "_fetch",
        lambda t: Quote(t, nome=t, preco=20.0, div_12m=2.0, lpa=3.0, vpa=25.0, pl=7, pvp=0.8, roe=15, fonte="yfinance"),
    )
    monkeypatch.setattr(market, "historico", lambda *a, **k: (_ for _ in ()).throw(ValueError("offline")))
    return state, loja


def test_fluxo_completo_das_telas(ambiente):
    state, loja = ambiente
    rodar = lambda mod: importlib.import_module(f"views.{mod}").render()  # noqa: E731

    rodar("carteira")
    df = state["df_carteira"]
    assert len(df) == 5 and len(loja.load_posicoes()) == 5  # processou e persistiu
    assert {"Teto Médio", "Margem Seg. (%)", "Status", "Parcial"} <= set(df.columns)

    for tela in ("ativo", "comparador", "aportes", "ia", "guia"):
        rodar(tela)


def test_ui_formatacao_brasileira(ambiente):
    ui = importlib.import_module("ui")
    assert ui.num(1234567.891) == "1.234.567,89"
    assert ui.brl(10) == "R$ 10,00"
    assert cart.TIPOS[0] == "Ação"
