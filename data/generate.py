"""Dataset determinístico íntegro. As violações são injetadas depois."""

from __future__ import annotations

import csv
import hashlib
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 3
RAW = Path(__file__).resolve().parent / "raw"

N_CLIENTES = 2_500
N_PEDIDOS = 12_000
INICIO = date(2026, 1, 1)
DIAS = 180

REGIOES = ["norte", "nordeste", "centro-oeste", "sudeste", "sul"]
REGIAO_PESO = [0.05, 0.18, 0.09, 0.48, 0.20]
SEGMENTOS = ["novo", "recorrente", "vip"]
SEGMENTO_PESO = [0.46, 0.41, 0.13]
CANAIS = ["app", "site", "marketplace", "loja"]
CANAL_PESO = [0.42, 0.28, 0.21, 0.09]
STATUS = ["aprovado", "pendente", "cancelado", "devolvido"]
STATUS_PESO = [0.84, 0.07, 0.06, 0.03]


def gerar() -> dict[str, Path]:
    rng = random.Random(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    clientes = [
        {
            "cliente_id": i,
            "regiao": rng.choices(REGIOES, REGIAO_PESO)[0],
            "segmento": rng.choices(SEGMENTOS, SEGMENTO_PESO)[0],
        }
        for i in range(1, N_CLIENTES + 1)
    ]

    pedidos = []
    for pedido_id in range(1, N_PEDIDOS + 1):
        itens = rng.choices([1, 2, 3, 4, 5, 6], [0.38, 0.26, 0.17, 0.10, 0.06, 0.03])[0]
        bruto = round(sum(rng.uniform(19.0, 780.0) for _ in range(itens)), 2)
        pct = rng.choices([0.0, 0.05, 0.10, 0.15], [0.58, 0.22, 0.14, 0.06])[0]
        desconto = round(bruto * pct, 2)
        pedidos.append(
            {
                "pedido_id": pedido_id,
                "cliente_id": rng.randint(1, N_CLIENTES),
                "data_pedido": (INICIO + timedelta(days=rng.randint(0, DIAS - 1))).isoformat(),
                "canal": rng.choices(CANAIS, CANAL_PESO)[0],
                "status": rng.choices(STATUS, STATUS_PESO)[0],
                "valor_bruto": bruto,
                "valor_desconto": desconto,
                "valor_liquido": round(bruto - desconto, 2),
                "itens": itens,
            }
        )

    return {
        "clientes": _escrever("clientes.csv", clientes),
        "pedidos": _escrever("pedidos.csv", pedidos),
    }


def _escrever(nome: str, linhas: list[dict]) -> Path:
    caminho = RAW / nome
    with caminho.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    return caminho


def fingerprint() -> str:
    h = hashlib.sha256()
    for caminho in sorted(RAW.glob("*.csv")):
        h.update(caminho.name.encode())
        h.update(caminho.read_bytes())
    return h.hexdigest()


if __name__ == "__main__":
    for nome, caminho in gerar().items():
        n = sum(1 for _ in caminho.open(encoding="utf-8")) - 1
        print(f"  {nome:<10} {n:>7,} linhas")
    print(f"\n  fingerprint: {fingerprint()[:16]}")
