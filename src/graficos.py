"""Gráficos Plotly (tema escuro). Cores seguem a paleta de referência do skill dataviz."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

SUPERFICIE = "#1a1a19"
TEXTO = "#f0efec"
TEXTO_SEC = "#c3c2b7"
GRADE = "rgba(240,239,236,0.10)"
AZUL = "#3987e5"      # categórico 1: ano analisado / normal
LARANJA = "#d95926"   # categórico 2: ano base
VERMELHO = "#e66767"  # status: alerta
# Divergente: queda (laranja) ← cinza neutro → alta (azul)
DIVERGENTE = [[0, "#d95926"], [0.5, "#3a3a38"], [1, "#3987e5"]]


def _layout(fig: go.Figure, titulo: str, altura: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15, color=TEXTO), x=0.0),
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXTO_SEC, size=12),
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(color=TEXTO_SEC)),
        hoverlabel=dict(bgcolor=SUPERFICIE, font_color=TEXTO, bordercolor=GRADE),
    )
    fig.update_xaxes(gridcolor=GRADE, zeroline=False, linecolor=GRADE)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, linecolor=GRADE)
    return fig


def heatmap_desvio(res: pd.DataFrame) -> go.Figure:
    """Sala × tema: desvio da média vs. o esperado. Alertas ganham contorno."""
    z = res.pivot(index="sala", columns="tema", values="desvio")
    alert = res.pivot(index="sala", columns="tema", values="alerta_queda").reindex_like(z).fillna(False)
    lim = max(abs(z.values[~pd.isna(z.values)]).max(), 0.5)
    texto = z.map(lambda v: "" if pd.isna(v) else f"{v:+.1f}")
    fig = go.Figure(
        go.Heatmap(
            z=z.values, x=z.columns, y=z.index, zmid=0, zmin=-lim, zmax=lim,
            colorscale=DIVERGENTE, xgap=3, ygap=3,
            text=texto.values, texttemplate="%{text}", textfont=dict(color=TEXTO, size=12),
            hovertemplate="Sala %{y} · %{x}<br>Desvio: %{z:+.2f}<extra></extra>",
            colorbar=dict(title="Desvio", thickness=10, outlinewidth=0, tickfont=dict(color=TEXTO_SEC)),
        )
    )
    for i, sala in enumerate(z.index):
        for j, tema in enumerate(z.columns):
            if alert.loc[sala, tema]:
                fig.add_shape(
                    type="rect", x0=j - 0.5, x1=j + 0.5, y0=i - 0.5, y1=i + 0.5,
                    line=dict(color=VERMELHO, width=3),
                )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False, side="top")
    return _layout(fig, "Desvio da média vs. esperado (contorno vermelho = alerta de queda)", 420)


def media_por_sala(res: pd.DataFrame, ano: int, ano_base: int) -> go.Figure:
    g = res.groupby("sala").agg(atual=("media", "mean"), base=("media_base", "mean")).reset_index()
    fig = go.Figure()
    fig.add_bar(x=g["sala"], y=g["base"], name=str(ano_base), marker_color=LARANJA, marker_cornerradius=4)
    fig.add_bar(x=g["sala"], y=g["atual"], name=str(ano), marker_color=AZUL, marker_cornerradius=4)
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    fig.update_yaxes(title="Média", rangemode="tozero")
    return _layout(fig, "Média geral por sala")


def dispersao_anomalia(res: pd.DataFrame) -> go.Figure:
    """Esperado × observado; pontos abaixo da diagonal caíram."""
    normal = res[~res["alerta_queda"]]
    alerta = res[res["alerta_queda"]]
    lo = min(res["media"].min(), res["esperado"].min()) - 0.3
    hi = max(res["media"].max(), res["esperado"].max()) + 0.3
    fig = go.Figure()
    fig.add_scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color=GRADE, dash="dot"),
                    hoverinfo="skip", showlegend=False)
    for df_, nome, cor, simb in ((normal, "Normal", AZUL, "circle"), (alerta, "Queda detectada", VERMELHO, "diamond")):
        fig.add_scatter(
            x=df_["esperado"], y=df_["media"], mode="markers", name=nome,
            marker=dict(color=cor, size=11, symbol=simb, line=dict(color=SUPERFICIE, width=2)),
            customdata=df_[["sala", "tema", "score_anomalia"]],
            hovertemplate="Sala %{customdata[0]} · %{customdata[1]}<br>Esperado %{x:.2f} → Atual %{y:.2f}"
                          "<br>Score %{customdata[2]:.3f}<extra></extra>",
        )
    fig.update_xaxes(title="Média esperada do tema (ano base)", range=[lo, hi])
    fig.update_yaxes(title="Média observada", range=[lo, hi])
    return _layout(fig, "Esperado × observado (abaixo da linha = queda)")


def ranking_alertas(res: pd.DataFrame) -> go.Figure:
    a = res[res["alerta_queda"]].sort_values("desvio", ascending=False)
    rotulo = a["sala"] + " · " + a["tema"]
    fig = go.Figure(
        go.Bar(
            x=a["desvio"], y=rotulo, orientation="h", marker_color=VERMELHO, marker_cornerradius=4,
            text=a["desvio"].map("{:+.2f}".format), textposition="outside", textfont=dict(color=TEXTO),
            hovertemplate="%{y}<br>Desvio %{x:+.2f}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Desvio vs. esperado", zeroline=True, zerolinecolor=TEXTO_SEC)
    return _layout(fig, "Maiores quedas detectadas", max(260, 60 + 44 * len(a)))


def evolucao_sala(res: pd.DataFrame, sala: str, ano: int, ano_base: int) -> go.Figure:
    d = res[res["sala"] == sala].sort_values("tema")
    fig = go.Figure()
    fig.add_scatter(x=d["tema"], y=d["media_base"], name=str(ano_base), mode="lines+markers",
                    line=dict(color=LARANJA, width=2), marker=dict(size=8, line=dict(color=SUPERFICIE, width=2)))
    fig.add_scatter(x=d["tema"], y=d["media"], name=str(ano), mode="lines+markers",
                    line=dict(color=AZUL, width=2), marker=dict(size=8, line=dict(color=SUPERFICIE, width=2)))
    a = d[d["alerta_queda"]]
    fig.add_scatter(x=a["tema"], y=a["media"], name="Alerta", mode="markers",
                    marker=dict(color=VERMELHO, size=14, symbol="diamond", line=dict(color=SUPERFICIE, width=2)))
    fig.update_yaxes(title="Média", rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return _layout(fig, f"Sala {sala}: média por tema")


def distribuicao_notas(df: pd.DataFrame, sala: str, tema: str, ano: int, ano_base: int) -> go.Figure:
    d = df[(df["sala"] == sala) & (df["tema"] == tema)]
    fig = go.Figure()
    for a, cor in ((ano_base, LARANJA), (ano, AZUL)):
        fig.add_histogram(x=d.loc[d["ano"] == a, "nota"], name=str(a), marker_color=cor,
                          opacity=0.75, xbins=dict(start=0, end=10.5, size=1))
    fig.update_layout(barmode="overlay", bargap=0.08)
    fig.update_xaxes(title="Nota")
    fig.update_yaxes(title="Alunos")
    return _layout(fig, f"Distribuição das notas · {sala} · {tema}")
