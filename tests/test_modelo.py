import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import dados
from src.modelo import DetectorQuedas


@pytest.fixture(scope="module")
def df():
    return dados.gerar_exemplo()


def test_detecta_quedas_injetadas(df):
    res = DetectorQuedas().treinar(df, 2025).analisar(df, 2026)
    alertas = set(map(tuple, res.loc[res.alerta_queda, ["sala", "tema"]].values))
    assert {("8B", "Geometria"), ("9A", "Funções"), ("7A", "Estatística")} <= alertas


def test_poucos_falsos_positivos(df):
    res = DetectorQuedas().treinar(df, 2025).analisar(df, 2026)
    assert res["alerta_queda"].sum() <= 6


def test_alerta_so_quando_desvio_negativo(df):
    res = DetectorQuedas().treinar(df, 2025).analisar(df, 2026)
    assert (res.loc[res.alerta_queda, "desvio"] < 0).all()


def test_ano_base_sem_dados_suficientes(df):
    with pytest.raises(ValueError):
        DetectorQuedas().treinar(df, 1999)


def test_csv_e_excel_roundtrip(df):
    for nome, dados_bytes in (("a.csv", dados.para_csv(df)), ("a.xlsx", dados.para_excel(df))):
        lido = dados.carregar(io.BytesIO(dados_bytes), nome)
        assert len(lido) == len(df)
        assert list(lido.columns) == dados.COLUNAS


def test_validacao_colunas_faltando():
    with pytest.raises(ValueError, match="ausentes"):
        dados.validar(pd.DataFrame({"ano": [2025], "sala": ["A"]}))


def test_virgula_decimal_e_alias():
    bruto = pd.DataFrame(
        {"Ano de Realização": [2025], "Tema da Prova": ["X"], "Turma": ["A"], "Aluno": ["a"], "Nota": ["7,5"]}
    )
    assert dados.validar(bruto).loc[0, "nota"] == 7.5


def test_gerar_aleatorio_reprodutivel_e_com_quedas():
    a = dados.gerar_aleatorio(seed=1, n_quedas=4)
    b = dados.gerar_aleatorio(seed=1, n_quedas=4)
    assert a.equals(b)
    res = DetectorQuedas().treinar(a, 2025).analisar(a, 2026)
    assert res["alerta_queda"].sum() >= 3
