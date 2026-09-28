"""CLI: compila o contrato em schema.yml, testes singulares e documentação."""

from __future__ import annotations

import argparse
from pathlib import Path

from .contract import load_all
from .generate import escrever

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    p = argparse.ArgumentParser(description="Compila data contracts em artefatos dbt")
    p.add_argument("--contracts", default=str(ROOT / "contracts"))
    p.add_argument("--dbt", default=str(ROOT / "dbt"))
    p.add_argument("--docs", default=str(ROOT / "docs"))
    args = p.parse_args()

    contratos = load_all(args.contracts)
    escritos = escrever(contratos, Path(args.dbt), Path(args.docs))

    nativas = sum(len(c.native_invariants) for c in contratos)
    singulares = sum(len(c.singular_invariants) for c in contratos)
    linhas_contrato = sum(
        len(c.source.read_text(encoding="utf-8").splitlines()) for c in contratos if c.source
    )
    linhas_geradas = sum(
        len(p.read_text(encoding="utf-8").splitlines()) for p in escritos.values()
    )

    print(f"  contratos      {len(contratos)}  ({linhas_contrato} linhas escritas à mão)")
    print(f"  invariantes    {nativas + singulares}  ({nativas} nativas, {singulares} singulares)")
    print(f"  arquivos       {len(escritos)}  ({linhas_geradas} linhas geradas)")
    print(f"  razão          {linhas_geradas / linhas_contrato:.1f}x")
    for nome in sorted(escritos):
        print(f"    {nome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
