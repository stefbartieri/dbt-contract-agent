"""Motor de mutação — injeta UMA violação mínima por invariante declarada.

Princípio II: um teste gerado que nunca falha é pior que nenhum teste. A única
forma de saber se ele consegue reprovar é fazê-lo reprovar.

As mutações são deliberadamente mínimas — uma linha, um centavo fora da borda.
Um teste com limite errado passa numa mutação grosseira e reprova nesta. É a
sensibilidade que se mede aqui, não a existência.

As mutações operam sobre os CSVs de origem, porque é assim que uma violação
real chega: pelo dado, não pela tabela materializada.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import Contract, Invariant

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

ARQUIVO_POR_DATASET = {
    "fct_pedidos": "pedidos.csv",
    "dim_clientes": "clientes.csv",
}


@dataclass(frozen=True)
class Mutation:
    """Uma violação injetada, e qual teste deveria pegá-la."""

    slug: str
    dataset: str
    descricao: str
    teste_esperado: str


def _ler(caminho: Path) -> tuple[list[str], list[dict]]:
    with caminho.open(encoding="utf-8") as fh:
        leitor = csv.DictReader(fh)
        return list(leitor.fieldnames or []), list(leitor)


def _escrever(caminho: Path, campos: list[str], linhas: list[dict]) -> None:
    with caminho.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def nome_do_teste(contrato: Contract, inv: Invariant) -> str:
    """Nome que o dbt dá ao teste desta invariante. Une contrato e resultado."""
    d = contrato.dataset
    if inv.type == "unique":
        return f"unique_{d}_{inv.column}"
    if inv.type == "not_null":
        return f"not_null_{d}_{inv.column}"
    if inv.type == "accepted_values":
        valores = "__".join(str(v).replace("-", "_") for v in inv.values or ())
        return f"accepted_values_{d}_{inv.column}__{valores}"
    if inv.type == "relationship":
        return (
            f"relationships_{d}_{inv.column}__{inv.references_column}"
            f"__ref_{inv.references}_"
        )
    return f"assert_{d}_{inv.slug}"


def mutacoes_para(contrato: Contract) -> list[tuple[Mutation, Callable[[], None]]]:
    """Uma mutação por invariante. Cada uma devolve a ação que a aplica."""
    arquivo = RAW / ARQUIVO_POR_DATASET[contrato.dataset]
    saida: list[tuple[Mutation, Callable[[], None]]] = []

    for inv in contrato.invariants:
        acao = _acao(contrato, inv, arquivo)
        if acao is None:
            continue
        descricao, funcao = acao
        saida.append(
            (
                Mutation(
                    slug=inv.slug,
                    dataset=contrato.dataset,
                    descricao=descricao,
                    teste_esperado=nome_do_teste(contrato, inv),
                ),
                funcao,
            )
        )
    return saida


def _acao(
    contrato: Contract, inv: Invariant, arquivo: Path
) -> tuple[str, Callable[[], None]] | None:
    coluna = inv.column

    if inv.type == "unique":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            linhas.append(dict(linhas[0]))  # exatamente uma duplicata
            _escrever(arquivo, campos, linhas)

        return f"duplica uma linha (chave {coluna})", aplicar

    if inv.type == "not_null":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            linhas[0][coluna] = ""  # exatamente uma célula nula
            _escrever(arquivo, campos, linhas)

        return f"anula uma célula de {coluna}", aplicar

    if inv.type == "accepted_values":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            linhas[0][coluna] = "__valor_fora_do_dominio__"
            _escrever(arquivo, campos, linhas)

        return f"um valor de {coluna} fora do domínio", aplicar

    if inv.type == "range":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            if inv.min is not None:
                # um centavo abaixo do mínimo: testa a borda, não a magnitude
                linhas[0][coluna] = _abaixo(inv.min, contrato, coluna)
            else:
                linhas[0][coluna] = str(float(inv.max) + 1)
            _escrever(arquivo, campos, linhas)

        borda = inv.min if inv.min is not None else inv.max
        return f"uma linha de {coluna} logo fora da borda {borda}", aplicar

    if inv.type == "relationship":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            linhas[0][coluna] = "99999999"  # FK que não existe na dimensão
            _escrever(arquivo, campos, linhas)

        return f"uma FK de {coluna} apontando para id inexistente", aplicar

    if inv.type == "expression":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            bruto = float(linhas[0]["valor_bruto"])
            # viola por 1 centavo acima do bruto
            linhas[0]["valor_liquido"] = f"{bruto + 0.01:.2f}"
            _escrever(arquivo, campos, linhas)

        return "valor_liquido um centavo acima do bruto", aplicar

    if inv.type == "row_count":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            alvo = int(inv.min) - 1 if inv.min is not None else int(inv.max) + 1
            if inv.min is not None:
                linhas = linhas[:alvo]
            else:
                linhas = linhas + [dict(linhas[0]) for _ in range(alvo - len(linhas))]
            _escrever(arquivo, campos, linhas)

        return f"reduz o volume para {int(inv.min) - 1} linhas", aplicar

    if inv.type == "grain":
        def aplicar() -> None:
            campos, linhas = _ler(arquivo)
            linhas.append(dict(linhas[0]))
            _escrever(arquivo, campos, linhas)

        return "duplica um par de chave composta", aplicar

    return None


def _abaixo(minimo: float, contrato: Contract, coluna: str) -> str:
    """Valor imediatamente abaixo do mínimo, respeitando o tipo declarado."""
    col = contrato.column(coluna)
    if col and col.type == "integer":
        return str(int(minimo) - 1)
    return f"{float(minimo) - 0.01:.2f}"


def snapshot() -> dict[Path, bytes]:
    """Guarda os CSVs íntegros para restaurar entre mutações."""
    return {p: p.read_bytes() for p in sorted(RAW.glob("*.csv"))}


def restaurar(estado: dict[Path, bytes]) -> None:
    for caminho, conteudo in estado.items():
        caminho.write_bytes(conteudo)


def contar_linhas(dataset: str) -> int:
    arquivo = RAW / ARQUIVO_POR_DATASET[dataset]
    return sum(1 for _ in arquivo.open(encoding="utf-8")) - 1


def valor_da_primeira_linha(dataset: str, coluna: str) -> Any:
    arquivo = RAW / ARQUIVO_POR_DATASET[dataset]
    _, linhas = _ler(arquivo)
    return linhas[0][coluna] if linhas else None
