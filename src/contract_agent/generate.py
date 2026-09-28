"""Geradores: contrato -> schema.yml, testes singulares, documentação.

Princípio IV: tudo aqui é reescrito por completo a cada execução e carrega
cabeçalho de aviso. Editar à mão é detectado pelo CI, não tolerado.

Princípio VI: saída determinística byte a byte. Ordenação estável, sem
timestamp, sem caminho absoluto.
"""

from __future__ import annotations

from pathlib import Path

from .contract import Contract, Invariant

AVISO = (
    "# ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.\n"
    "# Ele é reescrito por completo a cada `make build`, e o CI falha se houver\n"
    "# edição manual. Para mudar uma garantia, edite o data contract em\n"
    "# contracts/{fonte} e regenere.\n"
)

AVISO_SQL = (
    "-- ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.\n"
    "-- Origem: contracts/{fonte}, invariante '{slug}'\n"
    "--\n"
    "-- Regra de negócio:\n"
    "{regra}\n"
)


def _quebrar(texto: str, largura: int = 74, prefixo: str = "") -> list[str]:
    palavras = " ".join(texto.split()).split(" ")
    linhas: list[str] = []
    atual = prefixo
    for p in palavras:
        if len(atual) + len(p) + 1 > largura and atual.strip() != prefixo.strip():
            linhas.append(atual.rstrip())
            atual = prefixo + p + " "
        else:
            atual += p + " "
    if atual.strip():
        linhas.append(atual.rstrip())
    return linhas


# --- schema.yml -------------------------------------------------------------


def gerar_schema_yml(contratos: list[Contract]) -> str:
    fontes = ", ".join(c.source.name for c in contratos if c.source)
    out: list[str] = [AVISO.replace("{fonte}", fontes), "version: 2", "", "models:"]

    for contrato in contratos:
        out.append(f"  - name: {contrato.dataset}")
        if contrato.description:
            out.append("    description: >")
            out.extend(_quebrar(contrato.description, prefixo="      "))

        # testes de modelo (grão e combinações)
        testes_modelo = [
            i for i in contrato.native_invariants if i.type == "grain"
        ]
        if testes_modelo:
            out.append("    tests:")
            for inv in testes_modelo:
                cols = ", ".join(inv.columns or ())
                out.append("      - dbt_utils.unique_combination_of_columns:")
                out.append(f"          combination_of_columns: [{cols}]")

        out.append("    columns:")
        for coluna in contrato.columns:
            out.append(f"      - name: {coluna.name}")
            out.append("        description: >")
            out.extend(_quebrar(coluna.description, prefixo="          "))

            invs = [
                i
                for i in contrato.invariants_for(coluna.name)
                if i.is_native and i.type != "grain"
            ]
            if not invs:
                continue
            out.append("        tests:")
            for inv in sorted(invs, key=lambda i: i.type):
                out.extend(_teste_nativo(inv))
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _teste_nativo(inv: Invariant) -> list[str]:
    if inv.type == "unique":
        return ["          - unique"]
    if inv.type == "not_null":
        return ["          - not_null"]
    if inv.type == "accepted_values":
        valores = ", ".join(f"'{v}'" for v in inv.values or ())
        return [
            "          - accepted_values:",
            f"              values: [{valores}]",
        ]
    if inv.type == "relationship":
        return [
            "          - relationships:",
            f"              to: ref('{inv.references}')",
            f"              field: {inv.references_column}",
        ]
    raise ValueError(f"invariante nativa não mapeada: {inv.type}")


# --- testes singulares ------------------------------------------------------


def gerar_testes_singulares(contrato: Contract) -> dict[str, str]:
    """Um arquivo SQL por invariante não nativa. Nome previsível pelo slug."""
    fonte = contrato.source.name if contrato.source else "?"
    arquivos: dict[str, str] = {}

    for inv in contrato.singular_invariants:
        nome = f"assert_{contrato.dataset}_{inv.slug}.sql"
        cabecalho = AVISO_SQL.format(
            fonte=fonte,
            slug=inv.slug,
            regra="\n".join(_quebrar(inv.business_rule, prefixo="--   ")),
        )
        arquivos[nome] = cabecalho + "\n" + _sql_singular(contrato, inv) + "\n"

    return dict(sorted(arquivos.items()))


def _sql_singular(contrato: Contract, inv: Invariant) -> str:
    """Um teste dbt reprova quando devolve linhas. Todos seguem essa convenção."""
    modelo = "{{ ref('" + contrato.dataset + "') }}"

    if inv.type == "range":
        condicoes = []
        if inv.min is not None:
            condicoes.append(f"{inv.column} < {inv.min}")
        if inv.max is not None:
            condicoes.append(f"{inv.column} > {inv.max}")
        where = " or ".join(condicoes)
        return (
            f"select {inv.column}, count(*) as linhas\n"
            f"from {modelo}\n"
            f"where {where}\n"
            f"group by 1\n"
            f"order by 1"
        )

    if inv.type == "expression":
        return (
            f"select *\n"
            f"from {modelo}\n"
            f"where not ({inv.expression})\n"
            f"order by 1"
        )

    if inv.type == "row_count":
        condicoes = []
        if inv.min is not None:
            condicoes.append(f"linhas < {int(inv.min)}")
        if inv.max is not None:
            condicoes.append(f"linhas > {int(inv.max)}")
        where = " or ".join(condicoes)
        return (
            f"with contagem as (\n"
            f"    select count(*) as linhas from {modelo}\n"
            f")\n"
            f"select linhas from contagem\n"
            f"where {where}"
        )

    raise ValueError(f"invariante singular não mapeada: {inv.type}")


# --- documentação -----------------------------------------------------------

_ROTULO = {
    "unique": "Único",
    "not_null": "Sempre preenchido",
    "accepted_values": "Valores aceitos",
    "range": "Faixa",
    "relationship": "Referência íntegra",
    "expression": "Regra composta",
    "grain": "Grão",
    "row_count": "Volume",
}


def gerar_doc(contrato: Contract) -> str:
    fonte = contrato.source.name if contrato.source else "?"
    out: list[str] = [
        f"<!-- Gerado a partir de contracts/{fonte}. NÃO EDITE À MÃO. -->",
        "",
        f"# {contrato.dataset}",
        "",
    ]
    if contrato.description:
        out += [" ".join(contrato.description.split()), ""]

    out += [
        f"**Responsável:** {contrato.owner or 'não declarado'}  ",
        f"**Grão:** {', '.join(contrato.grain) or 'não declarado'}",
        "",
        "## Colunas",
        "",
        "| Coluna | Tipo | Descrição |",
        "|---|---|---|",
    ]
    for c in contrato.columns:
        out.append(f"| `{c.name}` | {c.type} | {' '.join(c.description.split())} |")

    out += ["", "## O que este dataset garante", ""]
    for inv in contrato.invariants:
        alvo = inv.column or (", ".join(inv.columns or ()) if inv.columns else "—")
        detalhe = _detalhe(inv)
        out += [
            f"### {_ROTULO.get(inv.type, inv.type)} — `{alvo}`",
            "",
            f"{' '.join(inv.business_rule.split())}",
            "",
            f"*Verificado por:* `{inv.slug}`{detalhe}",
            "",
        ]

    out += [
        "## O que este dataset NÃO garante",
        "",
        "- Frescor: o contrato não declara janela máxima de atraso na carga.",
        "- Completude da origem: garantimos o que chegou, não que tudo chegou.",
        "- Estabilidade histórica: reprocessamento pode alterar linhas antigas.",
        "",
        "---",
        "",
        f"Para mudar qualquer garantia acima, edite `contracts/{fonte}` e rode "
        "`make build`. Este arquivo é regenerado.",
        "",
    ]
    return "\n".join(out)


def _detalhe(inv: Invariant) -> str:
    if inv.type == "accepted_values":
        return " · valores: " + ", ".join(f"`{v}`" for v in inv.values or ())
    if inv.type in {"range", "row_count"}:
        partes = []
        if inv.min is not None:
            partes.append(f"mínimo {inv.min}")
        if inv.max is not None:
            partes.append(f"máximo {inv.max}")
        return " · " + ", ".join(partes)
    if inv.type == "relationship":
        return f" · referencia `{inv.references}.{inv.references_column}`"
    if inv.type == "expression":
        return f" · `{inv.expression}`"
    return ""


# --- escrita ----------------------------------------------------------------


def escrever(
    contratos: list[Contract], dbt_dir: Path, docs_dir: Path
) -> dict[str, Path]:
    """Escreve tudo. Retorna o mapa do que foi gerado, para o CI conferir."""
    escritos: dict[str, Path] = {}

    schema = dbt_dir / "models" / "marts" / "schema.yml"
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(gerar_schema_yml(contratos), encoding="utf-8", newline="\n")
    escritos["schema.yml"] = schema

    testes_dir = dbt_dir / "tests"
    testes_dir.mkdir(parents=True, exist_ok=True)
    for antigo in sorted(testes_dir.glob("assert_*.sql")):
        antigo.unlink()  # regeneração completa, sem resíduo

    docs_dir.mkdir(parents=True, exist_ok=True)
    for contrato in contratos:
        for nome, conteudo in gerar_testes_singulares(contrato).items():
            caminho = testes_dir / nome
            caminho.write_text(conteudo, encoding="utf-8", newline="\n")
            escritos[nome] = caminho

        doc = docs_dir / f"{contrato.dataset}.md"
        doc.write_text(gerar_doc(contrato), encoding="utf-8", newline="\n")
        escritos[doc.name] = doc

    return escritos
