"""Detector de quedas de desempenho por sala — Streamlit + IsolationForest."""
import streamlit as st

from src import dados, graficos
from src.modelo import DetectorQuedas

st.set_page_config(page_title="Detector de Quedas", page_icon="📉", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; max-width: 1300px;}
    .hero h1 {font-size: 2rem; margin-bottom: .1rem;}
    .hero p {color: #c3c2b7; margin-top: 0;}
    div[data-testid="stMetric"] {
        background: #1a1a19; border: 1px solid rgba(240,239,236,.10);
        border-radius: 14px; padding: 16px 18px;
    }
    div[data-testid="stMetricLabel"] {color: #c3c2b7;}
    .stTabs [data-baseweb="tab-list"] {gap: 6px;}
    .stTabs [data-baseweb="tab"] {border-radius: 10px; padding: 8px 16px;}
    </style>
    <div class="hero"><h1>📉 Detector de quedas de desempenho</h1>
    <p>IsolationForest treinado com as médias por sala e tema do ano base para apontar quedas bruscas.</p></div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Sidebar: dados ----------------
with st.sidebar:
    st.header("Dados")
    arq = st.file_uploader("Importar CSV ou Excel", type=["csv", "xlsx", "xls"])
    st.caption("Colunas: ano, tema, sala, aluno, nota")
    usar_exemplo = st.toggle("Usar dados de exemplo", value=arq is None)

try:
    if arq is not None and not usar_exemplo:
        df = dados.carregar(arq, arq.name)
        if df.attrs.get("linhas_descartadas"):
            st.sidebar.warning(f"{df.attrs['linhas_descartadas']} linhas inválidas descartadas.")
    else:
        df = dados.gerar_exemplo()
except ValueError as e:
    st.error(str(e))
    st.stop()

anos = sorted(df["ano"].unique())
if len(anos) < 2:
    st.error("São necessários pelo menos dois anos: um base (treino) e um para analisar.")
    st.stop()

with st.sidebar:
    st.header("Modelo")
    ano = st.selectbox("Ano a analisar", anos, index=len(anos) - 1)
    candidatos = [a for a in anos if a != ano]
    padrao = max([a for a in candidatos if a < ano], default=candidatos[-1])
    ano_base = st.selectbox("Ano base (treino)", candidatos, index=candidatos.index(padrao))
    contaminacao = st.slider(
        "Sensibilidade (contaminação)", 0.01, 0.30, 0.05, 0.01,
        help="Fração esperada de anomalias no treino. Maior = mais alertas.",
    )

try:
    detector = DetectorQuedas(contaminacao=contaminacao).treinar(df, ano_base)
    res = detector.analisar(df, ano)
except ValueError as e:
    st.error(str(e))
    st.stop()

alertas = res[res["alerta_queda"]]

# ---------------- Métricas ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Alunos avaliados", f"{df[df['ano'] == ano]['aluno'].nunique():,}".replace(",", "."))
c2.metric("Combinações sala × tema", len(res))
c3.metric("Alertas de queda", len(alertas))
delta = res["media"].mean() - res["media_base"].mean()
c4.metric(f"Média geral {ano}", f"{res['media'].mean():.2f}", f"{delta:+.2f} vs {ano_base}" if delta == delta else None)

if res["tema_novo"].any():
    st.info("Alguns temas não existiam no ano base; foi usada a média geral como referência para eles.")

tab_geral, tab_alertas, tab_sala, tab_dados = st.tabs(["Visão geral", "Alertas", "Detalhe da sala", "Dados"])

with tab_geral:
    st.plotly_chart(graficos.heatmap_desvio(res), width="stretch")
    a, b = st.columns(2)
    a.plotly_chart(graficos.media_por_sala(res, ano, ano_base), width="stretch")
    b.plotly_chart(graficos.dispersao_anomalia(res), width="stretch")

with tab_alertas:
    if alertas.empty:
        st.success("Nenhuma queda brusca detectada com a sensibilidade atual.")
    else:
        st.warning(f"{len(alertas)} possível(is) problema(s) detectado(s) em {ano}.")
        st.plotly_chart(graficos.ranking_alertas(res), width="stretch")
        tabela = alertas[
            ["sala", "tema", "severidade", "media", "esperado", "desvio", "queda_pct", "variacao_vs_base", "score_anomalia", "n_alunos"]
        ].rename(columns={
            "media": "média", "esperado": "esperado", "queda_pct": "queda %",
            "variacao_vs_base": f"var. vs {ano_base}", "score_anomalia": "score", "n_alunos": "alunos",
        })
        st.dataframe(
            tabela, hide_index=True, width="stretch",
            column_config={
                "média": st.column_config.NumberColumn(format="%.2f"),
                "esperado": st.column_config.NumberColumn(format="%.2f"),
                "desvio": st.column_config.NumberColumn(format="%+.2f"),
                "queda %": st.column_config.NumberColumn(format="percent"),
                f"var. vs {ano_base}": st.column_config.NumberColumn(format="%+.2f"),
                "score": st.column_config.ProgressColumn(min_value=0.4, max_value=0.8, format="%.3f"),
            },
        )
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Alertas (CSV)", dados.para_csv(tabela), f"alertas_{ano}.csv", "text/csv")
        d2.download_button("⬇️ Alertas (Excel)", dados.para_excel(tabela, "alertas"), f"alertas_{ano}.xlsx")

with tab_sala:
    sala = st.selectbox("Sala", sorted(res["sala"].unique()))
    st.plotly_chart(graficos.evolucao_sala(res, sala, ano, ano_base), width="stretch")
    temas_sala = sorted(res.loc[res["sala"] == sala, "tema"].unique())
    padrao_tema = res[(res["sala"] == sala)].sort_values("desvio").iloc[0]["tema"]
    tema = st.selectbox("Tema", temas_sala, index=temas_sala.index(padrao_tema))
    st.plotly_chart(graficos.distribuicao_notas(df, sala, tema, ano, ano_base), width="stretch")

with tab_dados:
    st.caption(f"{len(df):,} linhas · anos: {', '.join(map(str, anos))}".replace(",", "."))
    st.dataframe(df, hide_index=True, width="stretch", height=380)
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ Dados (CSV)", dados.para_csv(df), "notas.csv", "text/csv")
    d2.download_button("⬇️ Dados (Excel)", dados.para_excel(df), "notas.xlsx")
    d3.download_button(
        "⬇️ Resultado completo (CSV)", dados.para_csv(res), f"analise_{ano}.csv", "text/csv"
    )
