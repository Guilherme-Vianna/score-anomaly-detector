# Detector de quedas de desempenho por sala

Streamlit + IsolationForest para apontar quedas bruscas nas notas médias das salas.

## Executar (requer [uv](https://docs.astral.sh/uv/))

```bash
uv run start.py                      # sync, testes e app em http://localhost:8501
uv run start.py --porta 9000 --sem-testes

# ou manualmente
uv sync
uv run pytest
uv run streamlit run app.py
```

O backend (`src/dados.py`, `src/modelo.py`) é importado pelo app Streamlit, então backend e frontend sobem juntos em um só processo.

## Gerar dados aleatórios

```bash
uv run scripts/gerar_dados.py                                  # dados/notas_sinteticas.csv
uv run scripts/gerar_dados.py --salas 12 --temas 8 --quedas 5 --formato xlsx --seed 7
```

## Formato dos dados (CSV ou Excel)

| ano | tema | sala | aluno | nota |
|-----|------|------|-------|------|
| 2025 | Álgebra | 6A | 6A-01 | 7.5 |

Também aceita nomes como `turma`, `tema da prova`, `ano de realização` e nota com vírgula decimal.

## Como o modelo funciona

1. Agrega as notas por **sala × tema** no ano base (padrão: ano anterior ao analisado).
2. Features: `media`, `esperado_tema` (média histórica do tema) e `desvio_tema` (media − esperado).
3. `IsolationForest` é treinado só com o ano base.
4. No ano analisado, um ponto vira **alerta de queda** se o modelo o considera anômalo **e** `desvio_tema < 0`
   (altas fora do padrão não são alertadas).
5. Severidade pela queda relativa ao esperado: Alta ≤ −15%, Média ≤ −8%, Baixa acima disso.

A sensibilidade (contaminação) é ajustável na barra lateral.
