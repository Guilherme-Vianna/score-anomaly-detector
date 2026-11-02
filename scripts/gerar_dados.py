"""Gera um arquivo de notas aleatórias para testar o app.

Exemplos:
    uv run scripts/gerar_dados.py
    uv run scripts/gerar_dados.py --salas 12 --temas 8 --quedas 5 --formato xlsx
    uv run scripts/gerar_dados.py --seed 7 --saida dados/teste.csv
"""
import argparse
import sys
from pathlib import Path

# permite importar `src` ao rodar o script de qualquer pasta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import dados  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=2026, help="ano atual (o ano base é ano-1)")
    p.add_argument("--salas", type=int, default=8)
    p.add_argument("--temas", type=int, default=6)
    p.add_argument("--alunos", type=int, default=28, help="alunos por sala")
    p.add_argument("--quedas", type=int, default=3, help="quedas injetadas no ano atual")
    p.add_argument("--seed", type=int, default=None, help="fixa o sorteio (reprodutível)")
    p.add_argument("--formato", choices=["csv", "xlsx"], default="csv")
    p.add_argument("--saida", type=Path, default=None, help="caminho do arquivo (padrão: dados/notas_sinteticas.<formato>)")
    a = p.parse_args()

    df = dados.gerar_aleatorio(a.ano, a.salas, a.temas, a.alunos, a.quedas, a.seed)
    saida = a.saida or Path("dados") / f"notas_sinteticas.{a.formato}"
    saida.parent.mkdir(parents=True, exist_ok=True)
    conteudo = dados.para_csv(df) if saida.suffix == ".csv" else dados.para_excel(df)
    saida.write_bytes(conteudo)
    print(f"{len(df)} linhas salvas em {saida}")


if __name__ == "__main__":
    main()
