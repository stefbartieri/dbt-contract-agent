"""Avaliação por mutação.

Mede a única coisa que importa sobre um teste gerado: ele consegue reprovar?

  1. DETECÇÃO       a mutação da invariante X faz falhar o teste de X?
  2. ESPECIFICIDADE apenas ele falhou, ou houve falha colateral?
  3. DECORATIVOS    algum teste nunca falhou em mutação nenhuma?

Contar testes é a métrica que criou o problema que este projeto ataca. Aqui a
métrica é quantas violações reais os testes pegam.

Uso:
    python evals/runner.py
    python evals/runner.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contract_agent.contract import load_all  # noqa: E402
from contract_agent.mutate import (  # noqa: E402
    mutacoes_para,
    restaurar,
    snapshot,
)

DBT_DIR = ROOT / "dbt"
_LINHA_TESTE = re.compile(r"\d+ of \d+ (PASS|FAIL|ERROR) (?:\d+ )?(\S+)")


def _rodar_dbt(comando: str) -> tuple[set[str], set[str]]:
    """Roda dbt e devolve (testes que passaram, testes que falharam)."""
    proc = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", *comando.split(), "--project-dir", "."],
        cwd=DBT_DIR,
        env={**_env(), "DBT_PROFILES_DIR": "."},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    passou: set[str] = set()
    falhou: set[str] = set()
    for linha in proc.stdout.splitlines():
        m = _LINHA_TESTE.search(linha)
        if not m:
            continue
        status, nome = m.group(1), m.group(2).strip(".")
        (passou if status == "PASS" else falhou).add(nome)
    return passou, falhou


def _env() -> dict[str, str]:
    import os

    return dict(os.environ)


def avaliar() -> dict:
    contratos = load_all()
    estado = snapshot()

    # Linha de base: o dado íntegro precisa ficar verde (CA4).
    _rodar_dbt("build")
    base_pass, base_fail = _rodar_dbt("test")
    todos_os_testes = base_pass | base_fail

    resultados = []
    testes_que_ja_falharam: set[str] = set()

    try:
        for contrato in contratos:
            for mutacao, aplicar in mutacoes_para(contrato):
                restaurar(estado)
                aplicar()
                _rodar_dbt("run")
                _, falhou = _rodar_dbt("test")
                testes_que_ja_falharam |= falhou

                esperado = mutacao.teste_esperado
                pegou = esperado in falhou
                colaterais = sorted(falhou - {esperado})

                resultados.append(
                    {
                        "invariante": mutacao.slug,
                        "dataset": mutacao.dataset,
                        "mutacao": mutacao.descricao,
                        "teste_esperado": esperado,
                        "detectou": pegou,
                        "falhas_colaterais": colaterais,
                        "especifico": pegou and not colaterais,
                    }
                )
    finally:
        restaurar(estado)
        _rodar_dbt("build")

    decorativos = sorted(todos_os_testes - testes_que_ja_falharam)
    total = len(resultados)
    detectados = sum(1 for r in resultados if r["detectou"])
    especificos = sum(1 for r in resultados if r["especifico"])

    criterios = {
        "CA2_deteccao_100": total > 0 and detectados == total,
        "CA3_zero_decorativos": len(decorativos) == 0,
        "CA4_verde_no_integro": len(base_fail) == 0,
    }

    return {
        "totais": {
            "mutacoes": total,
            "detectadas": detectados,
            "especificas": especificos,
            "testes_no_projeto": len(todos_os_testes),
            "testes_decorativos": len(decorativos),
            "falhas_no_integro": len(base_fail),
        },
        "taxas": {
            "deteccao": round(detectados / total, 3) if total else 0.0,
            "especificidade": round(especificos / total, 3) if total else 0.0,
        },
        "decorativos": decorativos,
        "resultados": resultados,
        "criterios": criterios,
    }


def imprimir(rel: dict) -> None:
    ok = lambda f: "PASS" if f else "FAIL"  # noqa: E731
    t, x, c = rel["totais"], rel["taxas"], rel["criterios"]
    linha = "-" * 70

    print()
    print("  Avaliação por mutação — o teste gerado consegue reprovar?")
    print(f"  {linha}")
    print(f"  Mutações              {t['detectadas']:>3}/{t['mutacoes']:<3} detectadas")
    print(f"  Específicas           {t['especificas']:>3}/{t['mutacoes']:<3} sem falha colateral")
    print(f"  Testes no projeto     {t['testes_no_projeto']:>3}")
    print(f"  {linha}")
    print(f"  Detecção         {x['deteccao']:6.1%}   CA2 == 100%  [{ok(c['CA2_deteccao_100'])}]")
    print(f"  Especificidade   {x['especificidade']:6.1%}")
    print(
        f"  Decorativos          {t['testes_decorativos']:>3}   CA3 == 0     "
        f"[{ok(c['CA3_zero_decorativos'])}]"
    )
    verde = "sim" if c["CA4_verde_no_integro"] else "NAO"
    print(
        f"  Verde no integro         {verde:>5}   CA4          "
        f"[{ok(c['CA4_verde_no_integro'])}]"
    )
    print(f"  {linha}")

    print("\n  Por invariante:")
    for r in rel["resultados"]:
        marca = "ok " if r["detectou"] else "XX "
        extra = "" if r["especifico"] else f"  (+{len(r['falhas_colaterais'])} colateral)"
        print(f"    {marca}{r['invariante']:<40}{extra}")
        print(f"        mutação: {r['mutacao']}")

    if rel["decorativos"]:
        print("\n  TESTES DECORATIVOS (nunca falharam — CA3):")
        for nome in rel["decorativos"]:
            print(f"    {nome}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Avaliação por mutação")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rel = avaliar()
    if args.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        imprimir(rel)

    return 0 if all(rel["criterios"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
