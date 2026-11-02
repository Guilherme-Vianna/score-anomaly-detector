"""Importação, validação, exportação e geração de dados escolares."""
from __future__ import annotations

import io
from typing import BinaryIO

import numpy as np
import pandas as pd

COLUNAS = ["ano", "tema", "sala", "aluno", "nota"]

# Nomes alternativos aceitos na importação (normalizados para minúsculas, sem acento)
_ALIASES = {
    "ano": "ano",
    "ano_realizacao": "ano",
    "ano de realizacao": "ano",
    "tema": "tema",
    "tema_prova": "tema",
    "tema da prova": "tema",
    "sala": "sala",
    "turma": "sala",
    "aluno": "aluno",
    "nome": "aluno",
    "nota": "nota",
    "media": "nota",
}


def _normalizar_nome(col: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(col)).encode("ascii", "ignore").decode()
    return s.strip().lower()


def validar(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas e tipos. Levanta ValueError com mensagem amigável."""
    renomear = {c: _ALIASES[_normalizar_nome(c)] for c in df.columns if _normalizar_nome(c) in _ALIASES}
    df = df.rename(columns=renomear)

    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {', '.join(faltando)}. "
            f"Esperado: {', '.join(COLUNAS)}."
        )

    df = df[COLUNAS].copy()
    n_inicial = len(df)

    df["nota"] = pd.to_numeric(df["nota"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df = df.dropna(subset=COLUNAS)
    df["ano"] = df["ano"].astype(int)
    for c in ("tema", "sala", "aluno"):
        df[c] = df[c].astype(str).str.strip()

    if df.empty:
        raise ValueError("Nenhuma linha válida encontrada após a limpeza dos dados.")
    if (df["nota"] < 0).any():
        raise ValueError("Existem notas negativas no arquivo.")

    df.attrs["linhas_descartadas"] = n_inicial - len(df)
    return df.reset_index(drop=True)


def carregar(arquivo: BinaryIO | str, nome: str | None = None) -> pd.DataFrame:
    """Lê CSV (separador `,` ou `;`) ou Excel e devolve o DataFrame validado."""
    nome = (nome or getattr(arquivo, "name", str(arquivo))).lower()
    if nome.endswith((".xlsx", ".xls")):
        bruto = pd.read_excel(arquivo)
    elif nome.endswith(".csv"):
        bruto = pd.read_csv(arquivo, sep=None, engine="python", encoding_errors="replace")
    else:
        raise ValueError("Formato não suportado. Use .csv ou .xlsx.")
    return validar(bruto)


def para_csv(df: pd.DataFrame) -> bytes:
    # utf-8-sig para abrir corretamente acentos no Excel
    return df.to_csv(index=False).encode("utf-8-sig")


def para_excel(df: pd.DataFrame, aba: str = "dados") -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=aba)
    return buf.getvalue()


def _simular(ano_atual, salas, temas, efeito_tema, quedas, alunos_por_sala, rng) -> pd.DataFrame:
    """Gera notas do ano passado (normal) e do atual (com as quedas informadas)."""
    efeito_sala = dict(zip(salas, rng.normal(0, 0.35, len(salas))))

    linhas = []
    for ano in (ano_atual - 1, ano_atual):
        for sala in salas:
            for tema in temas:
                base = 6.8 + efeito_tema[tema] + efeito_sala[sala]
                if ano == ano_atual:
                    # queda injetada + pequena variação natural entre os anos
                    base += quedas.get((sala, tema), 0.0) + rng.normal(0, 0.15)
                notas = np.clip(rng.normal(base, 1.3, alunos_por_sala), 0, 10).round(1)
                for i, n in enumerate(notas, 1):
                    linhas.append((ano, tema, sala, f"{sala}-{i:02d}", n))
    return pd.DataFrame(linhas, columns=COLUNAS)


def gerar_exemplo(ano_atual: int = 2026, alunos_por_sala: int = 28, seed: int = 42) -> pd.DataFrame:
    """Conjunto fixo e reprodutível, com 3 quedas conhecidas (usado nos testes)."""
    rng = np.random.default_rng(seed)
    salas = ["6A", "6B", "7A", "7B", "8A", "8B", "9A", "9B"]
    temas = ["Álgebra", "Geometria", "Funções", "Estatística", "Probabilidade", "Trigonometria"]
    efeito_tema = dict(zip(temas, [0.0, -0.4, -0.7, 0.5, 0.2, -1.0]))
    quedas = {("8B", "Geometria"): -2.4, ("9A", "Funções"): -1.9, ("7A", "Estatística"): -1.5}
    return _simular(ano_atual, salas, temas, efeito_tema, quedas, alunos_por_sala, rng)


TEMAS_PADRAO = [
    "Álgebra", "Geometria", "Funções", "Estatística", "Probabilidade", "Trigonometria",
    "Aritmética", "Logaritmos", "Matrizes", "Análise Combinatória",
]


def gerar_aleatorio(
    ano_atual: int = 2026,
    n_salas: int = 8,
    n_temas: int = 6,
    alunos_por_sala: int = 28,
    n_quedas: int = 3,
    seed: int | None = None,
) -> pd.DataFrame:
    """Dados sintéticos com salas, temas e quedas sorteados (seed=None gera algo novo a cada vez)."""
    if n_temas > len(TEMAS_PADRAO):
        raise ValueError(f"No máximo {len(TEMAS_PADRAO)} temas.")
    rng = np.random.default_rng(seed)

    # salas no padrão série+letra: 6A, 6B, 7A...
    salas = [f"{6 + i // 2}{'AB'[i % 2]}" for i in range(n_salas)]
    temas = TEMAS_PADRAO[:n_temas]
    efeito_tema = dict(zip(temas, rng.normal(0, 0.6, n_temas)))

    # sorteia as combinações (sala, tema) que vão cair no ano atual
    n_quedas = min(n_quedas, n_salas * n_temas)
    idx = rng.choice(n_salas * n_temas, size=n_quedas, replace=False)
    quedas = {(salas[i // n_temas], temas[i % n_temas]): -rng.uniform(1.2, 3.0) for i in idx}

    return _simular(ano_atual, salas, temas, efeito_tema, quedas, alunos_por_sala, rng)
