"""Inicia tudo com um comando: uv run start.py [--porta 8501] [--sem-testes]

Sincroniza o ambiente com `uv sync`, roda os testes do backend (src/) e sobe o frontend Streamlit.
O backend (dados + modelo) é importado pelo app, então os dois sobem juntos no mesmo processo.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def uv(*args: str) -> int:
    return subprocess.call(["uv", *args], cwd=RAIZ)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--porta", type=int, default=8501)
    p.add_argument("--sem-testes", action="store_true", help="pula os testes ao iniciar")
    args = p.parse_args()

    if shutil.which("uv") is None:
        print("uv não encontrado. Instale: https://docs.astral.sh/uv/getting-started/installation/")
        return 1

    if uv("sync") != 0:
        return 1

    if not args.sem_testes and uv("run", "pytest", "-q") != 0:
        print("Testes falharam; abortando. Use --sem-testes para ignorar.")
        return 1

    print(f"Iniciando em http://localhost:{args.porta}")
    return uv("run", "streamlit", "run", "app.py", "--server.port", str(args.porta))


if __name__ == "__main__":
    sys.exit(main())
