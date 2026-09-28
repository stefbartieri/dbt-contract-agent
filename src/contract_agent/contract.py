"""Carga e validação do data contract.

Princípio I: este arquivo é escrito por gente. Tudo o mais é derivado dele.

A validação é estrutural e falha alto: contrato malformado nunca chega ao
gerador, porque um gerador rodando sobre entrada inválida produz YAML que
parece certo e testa a coisa errada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

TIPOS_INVARIANTE = {
    "unique",
    "not_null",
    "accepted_values",
    "range",
    "relationship",
    "expression",
    "grain",
    "row_count",
}

# Invariantes que o dbt expressa nativamente; o resto vira teste singular SQL.
NATIVAS = {"unique", "not_null", "accepted_values", "relationship", "grain"}


class ContractError(Exception):
    """O contrato está malformado. Falha na carga, nunca em runtime."""


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    description: str


@dataclass(frozen=True)
class Invariant:
    type: str
    business_rule: str
    column: str | None = None
    name: str | None = None
    values: tuple[str, ...] | None = None
    min: float | None = None
    max: float | None = None
    references: str | None = None
    references_column: str | None = None
    expression: str | None = None
    columns: tuple[str, ...] | None = None

    @property
    def is_native(self) -> bool:
        return self.type in NATIVAS

    @property
    def slug(self) -> str:
        """Nome estável e previsível. Alimenta o nome do arquivo de teste."""
        if self.name:
            return self.name
        if self.type == "row_count":
            return "row_count"
        if self.type == "grain":
            return "grain_" + "_".join(self.columns or ())
        return f"{self.type}_{self.column}"


@dataclass
class Contract:
    dataset: str
    owner: str
    description: str
    grain: tuple[str, ...]
    columns: tuple[Column, ...]
    invariants: tuple[Invariant, ...]
    source: Path | None = field(default=None, repr=False)

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)

    @property
    def native_invariants(self) -> list[Invariant]:
        return [i for i in self.invariants if i.is_native]

    @property
    def singular_invariants(self) -> list[Invariant]:
        return [i for i in self.invariants if not i.is_native]

    def invariants_for(self, column: str) -> list[Invariant]:
        return [i for i in self.invariants if i.column == column]


def _exigir(node: dict, chave: str, onde: str) -> Any:
    if chave not in node or node[chave] in (None, ""):
        raise ContractError(f"{onde}: campo obrigatório ausente: '{chave}'")
    return node[chave]


def load_contract(path: Path | str) -> Contract:
    path = Path(path)
    if not path.exists():
        raise ContractError(f"contrato não encontrado: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ContractError(f"{path.name}: a raiz do contrato deve ser um mapeamento")

    dataset = str(_exigir(raw, "dataset", path.name))

    colunas: list[Column] = []
    vistos: set[str] = set()
    for node in raw.get("columns") or []:
        nome = _exigir(node, "name", f"{dataset}.columns[]")
        if nome in vistos:
            raise ContractError(f"{dataset}: coluna duplicada '{nome}'")
        vistos.add(nome)
        descricao = (node.get("description") or "").strip()
        if not descricao:
            # Princípio I: o contrato é lido por gente de negócio. Coluna sem
            # descrição transforma o contrato de volta em schema técnico.
            raise ContractError(
                f"{dataset}.{nome}: 'description' é obrigatório — o contrato "
                "precisa ser legível por quem não lê SQL"
            )
        colunas.append(
            Column(nome, str(node.get("type", "varchar")), descricao)
        )

    if not colunas:
        raise ContractError(f"{dataset}: nenhuma coluna declarada")

    grao = tuple(raw.get("grain") or ())
    for g in grao:
        if g not in vistos:
            raise ContractError(f"{dataset}: grain referencia coluna inexistente '{g}'")

    invariantes: list[Invariant] = []
    slugs: set[str] = set()
    for node in raw.get("invariants") or []:
        tipo = _exigir(node, "type", f"{dataset}.invariants[]")
        if tipo not in TIPOS_INVARIANTE:
            raise ContractError(
                f"{dataset}: tipo de invariante desconhecido '{tipo}'; "
                f"válidos: {sorted(TIPOS_INVARIANTE)}"
            )

        regra = (node.get("business_rule") or "").strip()
        if not regra:
            raise ContractError(
                f"{dataset}: invariante '{tipo}' sem 'business_rule' — uma "
                "garantia sem explicação de negócio não documenta nada"
            )

        coluna = node.get("column")
        if coluna is not None and coluna not in vistos:
            raise ContractError(
                f"{dataset}: invariante '{tipo}' referencia coluna inexistente "
                f"'{coluna}'"
            )

        if tipo in {"unique", "not_null"} and not coluna:
            raise ContractError(f"{dataset}: invariante '{tipo}' exige 'column'")
        if tipo == "accepted_values" and not node.get("values"):
            raise ContractError(f"{dataset}: 'accepted_values' exige 'values'")
        if tipo == "range" and node.get("min") is None and node.get("max") is None:
            raise ContractError(f"{dataset}: 'range' exige 'min' e/ou 'max'")
        if tipo == "relationship" and not (
            node.get("references") and node.get("references_column")
        ):
            raise ContractError(
                f"{dataset}: 'relationship' exige 'references' e 'references_column'"
            )
        if tipo == "expression" and not (node.get("expression") and node.get("name")):
            raise ContractError(f"{dataset}: 'expression' exige 'name' e 'expression'")
        if tipo == "row_count" and node.get("min") is None and node.get("max") is None:
            raise ContractError(f"{dataset}: 'row_count' exige 'min' e/ou 'max'")

        colunas_compostas = node.get("columns")
        if tipo == "grain":
            if not colunas_compostas:
                raise ContractError(f"{dataset}: 'grain' exige 'columns'")
            for c in colunas_compostas:
                if c not in vistos:
                    raise ContractError(
                        f"{dataset}: grain referencia coluna inexistente '{c}'"
                    )

        inv = Invariant(
            type=tipo,
            business_rule=regra,
            column=coluna,
            name=node.get("name"),
            values=tuple(node["values"]) if node.get("values") else None,
            min=node.get("min"),
            max=node.get("max"),
            references=node.get("references"),
            references_column=node.get("references_column"),
            expression=node.get("expression"),
            columns=tuple(colunas_compostas) if colunas_compostas else None,
        )
        if inv.slug in slugs:
            raise ContractError(
                f"{dataset}: duas invariantes geram o mesmo nome '{inv.slug}'; "
                "use 'name' para desambiguar"
            )
        slugs.add(inv.slug)
        invariantes.append(inv)

    if not invariantes:
        raise ContractError(f"{dataset}: nenhuma invariante declarada")

    return Contract(
        dataset=dataset,
        owner=str(raw.get("owner", "")),
        description=(raw.get("description") or "").strip(),
        grain=grao,
        columns=tuple(colunas),
        invariants=tuple(invariantes),
        source=path,
    )


def load_all(directory: Path | str | None = None) -> list[Contract]:
    directory = Path(directory) if directory else CONTRACTS_DIR
    return [load_contract(p) for p in sorted(directory.glob("*.yml"))]
