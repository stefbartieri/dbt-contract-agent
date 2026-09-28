"""Validação do contrato: falha alto e cedo, com o campo apontado."""

from __future__ import annotations

import pytest
import yaml

from contract_agent.contract import ContractError, load_all, load_contract

BASE = {
    "dataset": "t",
    "owner": "ae",
    "grain": ["id"],
    "description": "d",
    "columns": [{"name": "id", "type": "integer", "description": "chave"}],
    "invariants": [{"type": "unique", "column": "id", "business_rule": "r"}],
}


def _escrever(tmp_path, dados):
    p = tmp_path / "c.yml"
    p.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture(scope="module")
def contratos():
    return {c.dataset: c for c in load_all()}


def test_contratos_reais_carregam(contratos):
    assert set(contratos) == {"fct_pedidos", "dim_clientes"}


def test_fct_pedidos_cobre_todos_os_tipos(contratos):
    tipos = {i.type for i in contratos["fct_pedidos"].invariants}
    assert tipos >= {
        "unique", "not_null", "accepted_values", "range",
        "relationship", "expression", "row_count",
    }


def test_separa_nativas_de_singulares(contratos):
    c = contratos["fct_pedidos"]
    assert {i.type for i in c.singular_invariants} == {"range", "expression", "row_count"}
    assert all(i.is_native for i in c.native_invariants)


def test_toda_coluna_tem_descricao_de_negocio(contratos):
    for c in contratos.values():
        for col in c.columns:
            assert col.description.strip()


def test_toda_invariante_tem_regra_de_negocio(contratos):
    for c in contratos.values():
        for inv in c.invariants:
            assert inv.business_rule.strip()


# --- validação --------------------------------------------------------------


def test_coluna_sem_descricao_falha(tmp_path):
    d = {**BASE, "columns": [{"name": "id", "type": "integer", "description": ""}]}
    with pytest.raises(ContractError, match="description"):
        load_contract(_escrever(tmp_path, d))


def test_invariante_sem_regra_de_negocio_falha(tmp_path):
    d = {**BASE, "invariants": [{"type": "unique", "column": "id"}]}
    with pytest.raises(ContractError, match="business_rule"):
        load_contract(_escrever(tmp_path, d))


def test_invariante_sobre_coluna_inexistente_falha(tmp_path):
    d = {**BASE, "invariants": [
        {"type": "unique", "column": "fantasma", "business_rule": "r"}]}
    with pytest.raises(ContractError, match="fantasma"):
        load_contract(_escrever(tmp_path, d))


def test_tipo_de_invariante_desconhecido_falha(tmp_path):
    d = {**BASE, "invariants": [
        {"type": "telepatia", "column": "id", "business_rule": "r"}]}
    with pytest.raises(ContractError, match="desconhecido"):
        load_contract(_escrever(tmp_path, d))


def test_grain_sobre_coluna_inexistente_falha(tmp_path):
    with pytest.raises(ContractError, match="grain"):
        load_contract(_escrever(tmp_path, {**BASE, "grain": ["fantasma"]}))


def test_range_sem_limite_falha(tmp_path):
    d = {**BASE, "invariants": [
        {"type": "range", "column": "id", "business_rule": "r"}]}
    with pytest.raises(ContractError, match="range"):
        load_contract(_escrever(tmp_path, d))


def test_relationship_incompleto_falha(tmp_path):
    d = {**BASE, "invariants": [
        {"type": "relationship", "column": "id", "references": "x",
         "business_rule": "r"}]}
    with pytest.raises(ContractError, match="relationship"):
        load_contract(_escrever(tmp_path, d))


def test_expression_sem_nome_falha(tmp_path):
    d = {**BASE, "invariants": [
        {"type": "expression", "expression": "id > 0", "business_rule": "r"}]}
    with pytest.raises(ContractError, match="expression"):
        load_contract(_escrever(tmp_path, d))


def test_invariantes_com_mesmo_slug_falham(tmp_path):
    d = {**BASE, "invariants": [
        {"type": "unique", "column": "id", "business_rule": "r"},
        {"type": "unique", "column": "id", "business_rule": "r2"}]}
    with pytest.raises(ContractError, match="mesmo nome"):
        load_contract(_escrever(tmp_path, d))


def test_contrato_sem_invariante_falha(tmp_path):
    with pytest.raises(ContractError, match="nenhuma invariante"):
        load_contract(_escrever(tmp_path, {**BASE, "invariants": []}))
