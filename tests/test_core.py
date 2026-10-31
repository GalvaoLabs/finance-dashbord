import pandas as pd
import pytest

from core import carteira as cart
from core import valuation as v
from providers.market import Quote


def test_modelos_basicos():
    assert v.bazin(6, 0.06) == pytest.approx(100)
    assert v.bazin(0, 0.06) == 0 and v.bazin(6, 0) == 0
    assert v.graham(2, 20) == pytest.approx((22.5 * 40) ** 0.5)
    assert v.graham(-1, 20) == 0
    assert v.gordon(1, 0.03, 0.10) == pytest.approx(1.03 / 0.07)
    assert v.gordon(1, 0.10, 0.10) == 0


def test_media_ignora_zeros_e_margem_classica():
    assert v.media(10, 0, 20) == 15
    assert v.media(0, 0) == 0
    assert v.margem(80, 100) == pytest.approx(20)  # (100-80)/100
    assert v.margem(0, 100) == 0


@pytest.mark.parametrize(
    "preco,teto,esperado",
    [(80, 100, v.ABAIXO), (100, 100, v.ABAIXO), (105, 100, v.PROXIMO), (120, 100, v.ACIMA), (0, 100, v.SEM_DADOS), (50, 0, v.SEM_DADOS)],
)
def test_classificar(preco, teto, esperado):
    assert v.classificar(preco, teto) == esperado


def test_graham_so_para_acao():
    acao = v.analisar(30, 2, 3, 20, "Ação")
    fii = v.analisar(30, 2, 3, 20, "FII")
    assert acao.graham > 0 and fii.graham == 0


def test_limpar_normaliza():
    sujo = pd.DataFrame(
        {"Ticker": [" bbas3", "BBAS3", None, "", "mxrf11"], "Tipo": ["Ação", "Ação", "Ação", "Ação", "xxx"],
         "Quantidade": [1, 5, 1, 1, "abc"], "Preço Médio": [10, 12, 1, 1, None]}
    )
    d = cart.limpar(sujo)
    assert list(d["Ticker"]) == ["BBAS3", "MXRF11"]
    assert d.loc[0, "Quantidade"] == 5  # duplicado: vale o último
    assert d.loc[1, "Tipo"] == "Ação" and d.loc[1, "Quantidade"] == 0


def _cot():
    return {
        "AAA3": Quote("AAA3", preco=50, div_12m=6, lpa=5, vpa=40, fonte="yfinance"),
        "BBB11": Quote("BBB11", preco=100, div_12m=9, fonte="yfinance"),
        "CCC4": Quote("CCC4", erro="falhou"),
    }


def test_processar_e_resumo():
    pos = pd.DataFrame(
        [("AAA3", "Ação", 10, 40.0), ("BBB11", "FII", 5, 90.0), ("CCC4", "Ação", 1, 1.0)], columns=cart.COLUNAS
    )
    df, erros = cart.processar(pos, _cot(), 0.06)
    assert list(df["Ticker"]) == ["AAA3", "BBB11"]
    assert len(erros) == 1 and "CCC4" in erros[0]
    aaa = df.set_index("Ticker").loc["AAA3"]
    assert aaa["Valor Atual"] == 500 and aaa["Investido"] == 400 and aaa["Resultado (R$)"] == 100
    assert aaa["Rentab. (%)"] == pytest.approx(25)
    assert pd.isna(df.set_index("Ticker").loc["BBB11", "Teto Graham"])  # FII não tem Graham
    r = cart.resumo(df)
    assert r["patrimonio"] == 1000 and r["investido"] == 850
    assert r["renda_anual"] == pytest.approx(10 * 6 + 5 * 9)


def test_simular_aporte_soma_e_ignora_acima_do_teto():
    df = pd.DataFrame(
        {"Ticker": ["A", "B", "C"], "P. Atual": [10.0, 20.0, 5.0], "Margem Seg. (%)": [30.0, 10.0, -5.0]}
    )
    s = cart.simular_aporte(df, 1000)
    assert list(s["Ticker"]) == ["A", "B"]
    assert s["Valor Sugerido (R$)"].sum() == pytest.approx(1000, abs=0.02)
    assert s.loc[s.Ticker == "A", "Qtd. Sugerida"].iloc[0] == 75  # 750 / 10
    assert cart.simular_aporte(df.assign(**{"Margem Seg. (%)": [-1.0, -2.0, -3.0]}), 1000).empty
