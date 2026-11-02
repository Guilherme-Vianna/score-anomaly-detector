"""Detecção de quedas bruscas de nota por sala usando IsolationForest.

Treino: médias por (sala, tema) do ano base (ano passado).
Features por (sala, tema):
  - media          : média da sala na prova
  - esperado_tema  : média histórica do tema no ano base (codifica o "tema da prova")
  - desvio_tema    : media - esperado_tema
Alerta de queda = o IsolationForest considera o ponto anômalo E desvio_tema < 0
(IsolationForest sozinho também sinalizaria saltos para cima, que não são o foco).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ["media", "esperado_tema", "desvio_tema"]


def agregar(df: pd.DataFrame) -> pd.DataFrame:
    """Média, desvio-padrão e nº de alunos por ano/tema/sala."""
    return (
        df.groupby(["ano", "tema", "sala"], as_index=False)
        .agg(media=("nota", "mean"), desvio_padrao=("nota", "std"), n_alunos=("aluno", "nunique"))
        .fillna({"desvio_padrao": 0.0})
    )


def _severidade(queda_pct: float) -> str:
    if queda_pct <= -0.15:
        return "Alta"
    if queda_pct <= -0.08:
        return "Média"
    return "Baixa"


@dataclass
class DetectorQuedas:
    contaminacao: float = 0.05
    n_estimators: int = 300
    seed: int = 42
    ano_base: int | None = None
    esperado_por_tema: pd.Series = field(default_factory=pd.Series)
    media_geral_base: float = 0.0
    media_base_sala_tema: pd.DataFrame = field(default_factory=pd.DataFrame)
    modelo: IsolationForest | None = None

    # ---------- features ----------
    def _features(self, agg: pd.DataFrame) -> pd.DataFrame:
        esperado = agg["tema"].map(self.esperado_por_tema).fillna(self.media_geral_base)
        return pd.DataFrame(
            {"media": agg["media"], "esperado_tema": esperado, "desvio_tema": agg["media"] - esperado},
            index=agg.index,
        )

    # ---------- treino ----------
    def treinar(self, df: pd.DataFrame, ano_base: int) -> "DetectorQuedas":
        base = agregar(df[df["ano"] == ano_base])
        if len(base) < 10:
            raise ValueError(
                f"Poucos dados no ano base {ano_base}: {len(base)} combinações sala×tema (mínimo 10)."
            )
        self.ano_base = ano_base
        # referência por tema: média das salas no ano base
        self.esperado_por_tema = base.groupby("tema")["media"].mean()
        self.media_geral_base = float(base["media"].mean())
        self.media_base_sala_tema = base.set_index(["sala", "tema"])["media"].rename("media_base")

        # o corte do alerta é o percentil (1 - contaminacao) dos scores do treino
        self.modelo = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contaminacao,
            random_state=self.seed,
        ).fit(self._features(base)[FEATURES])
        return self

    # ---------- inferência ----------
    def analisar(self, df: pd.DataFrame, ano: int) -> pd.DataFrame:
        """Resultado por sala×tema do `ano`, ordenado do mais para o menos crítico."""
        if self.modelo is None:
            raise RuntimeError("Treine o modelo antes de analisar.")
        agg = agregar(df[df["ano"] == ano]).reset_index(drop=True)
        if agg.empty:
            raise ValueError(f"Não há dados para o ano {ano}.")

        X = self._features(agg)
        agg["esperado"] = X["esperado_tema"]
        agg["desvio"] = X["desvio_tema"]
        agg["queda_pct"] = agg["desvio"] / agg["esperado"].replace(0, np.nan)
        agg["tema_novo"] = ~agg["tema"].isin(self.esperado_por_tema.index)

        # score maior = mais anômalo (0,5 ~ normal; perto de 1 = muito isolável)
        agg["score_anomalia"] = -self.modelo.score_samples(X[FEATURES])
        agg["anomalia"] = self.modelo.predict(X[FEATURES]) == -1
        agg["alerta_queda"] = agg["anomalia"] & (agg["desvio"] < 0)

        agg = agg.merge(self.media_base_sala_tema.reset_index(), on=["sala", "tema"], how="left")
        agg["variacao_vs_base"] = agg["media"] - agg["media_base"]
        agg["severidade"] = np.where(
            agg["alerta_queda"], agg["queda_pct"].fillna(0).map(_severidade), "—"
        )
        return agg.sort_values(
            ["alerta_queda", "score_anomalia"], ascending=[False, False]
        ).reset_index(drop=True)
