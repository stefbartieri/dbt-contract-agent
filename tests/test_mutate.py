"""Mutação: mínima, derivada do contrato, e ligada ao teste que deve pegá-la."""

from __future__ import annotations

import pytest

from contract_agent.contract import load_all
from contract_agent.mutate import (
    ARQUIVO_POR_DATASET,
    RAW,
    contar_linhas,
    mutacoes_para,
    nome_do_teste,
    restaurar,
    snapshot,
)


@pytest.fixture(scope="module")
def contratos():
    return {c.dataset: c for c in load_all()}


@pytest.fixture(autouse=True)
def preservar_dados():
    """Nenhum teste aqui pode deixar o CSV corrompido para o próximo."""
    estado = snapshot()
    yield
    restaurar(estado)


def test_toda_invariante_tem_mutacao(contratos):
    for nome, contrato in contratos.items():
        muts = mutacoes_para(contrato)
        assert len(muts) == len(contrato.invariants), (
            f"{nome}: invariante sem mutação correspondente"
        )


def test_mutacao_aponta_para_o_teste_esperado(contratos):
    for contrato in contratos.values():
        for mutacao, _ in mutacoes_para(contrato):
            assert mutacao.teste_esperado
            assert mutacao.dataset == contrato.dataset


@pytest.mark.parametrize("dataset", ["fct_pedidos", "dim_clientes"])
def test_mutacao_de_unicidade_adiciona_exatamente_uma_linha(contratos, dataset):
    contrato = contratos[dataset]
    antes = contar_linhas(dataset)
    mutacao, aplicar = next(
        (m, f) for m, f in mutacoes_para(contrato) if m.slug.startswith("unique")
    )
    aplicar()
    assert contar_linhas(dataset) == antes + 1, "mutação deve ser mínima"
    assert "duplica" in mutacao.descricao


def test_mutacao_de_nulo_nao_muda_o_volume(contratos):
    antes = contar_linhas("fct_pedidos")
    _, aplicar = next(
        (m, f)
        for m, f in mutacoes_para(contratos["fct_pedidos"])
        if m.slug == "not_null_valor_liquido"
    )
    aplicar()
    assert contar_linhas("fct_pedidos") == antes


def test_mutacao_de_faixa_fica_logo_fora_da_borda(contratos):
    """Mutação grosseira passaria mesmo com o limite errado. Esta não."""
    _, aplicar = next(
        (m, f)
        for m, f in mutacoes_para(contratos["fct_pedidos"])
        if m.slug == "range_valor_liquido"
    )
    aplicar()
    import csv

    with (RAW / ARQUIVO_POR_DATASET["fct_pedidos"]).open(encoding="utf-8") as fh:
        primeira = next(csv.DictReader(fh))
    assert float(primeira["valor_liquido"]) == pytest.approx(-0.01)


def test_mutacao_de_volume_cruza_o_minimo_por_uma_linha(contratos):
    contrato = contratos["fct_pedidos"]
    inv = next(i for i in contrato.invariants if i.type == "row_count")
    _, aplicar = next(
        (m, f) for m, f in mutacoes_para(contrato) if m.slug == "row_count"
    )
    aplicar()
    assert contar_linhas("fct_pedidos") == int(inv.min) - 1


def test_nome_do_teste_bate_com_a_convencao_do_dbt(contratos):
    contrato = contratos["fct_pedidos"]
    inv_unique = next(i for i in contrato.invariants if i.type == "unique")
    assert nome_do_teste(contrato, inv_unique) == "unique_fct_pedidos_pedido_id"

    inv_singular = next(i for i in contrato.invariants if i.type == "row_count")
    assert nome_do_teste(contrato, inv_singular) == "assert_fct_pedidos_row_count"


def test_restaurar_devolve_os_bytes_originais(contratos):
    original = (RAW / "pedidos.csv").read_bytes()
    estado = snapshot()
    _, aplicar = next(
        (m, f)
        for m, f in mutacoes_para(contratos["fct_pedidos"])
        if m.slug == "unique_pedido_id"
    )
    aplicar()
    assert (RAW / "pedidos.csv").read_bytes() != original
    restaurar(estado)
    assert (RAW / "pedidos.csv").read_bytes() == original
