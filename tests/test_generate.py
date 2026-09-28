"""Geração: determinística, avisada, e cobrindo toda garantia declarada."""

from __future__ import annotations

from pathlib import Path

import pytest

from contract_agent.contract import load_all
from contract_agent.generate import (
    escrever,
    gerar_doc,
    gerar_schema_yml,
    gerar_testes_singulares,
)


@pytest.fixture(scope="module")
def contratos():
    return load_all()


@pytest.fixture(scope="module")
def fct(contratos):
    return next(c for c in contratos if c.dataset == "fct_pedidos")


# --- Princípio IV: arquivo gerado é avisado ---------------------------------


def test_schema_carrega_aviso(contratos):
    out = gerar_schema_yml(contratos)
    assert "NÃO EDITE À MÃO" in out
    assert "contracts/" in out


def test_teste_singular_carrega_aviso_e_regra(fct):
    for conteudo in gerar_testes_singulares(fct).values():
        assert "NÃO EDITE À MÃO" in conteudo
        assert "Regra de negócio:" in conteudo


def test_doc_carrega_aviso(fct):
    assert "NÃO EDITE À MÃO" in gerar_doc(fct)


# --- RNF1 / CA5: determinismo ----------------------------------------------


def test_schema_e_deterministico(contratos):
    assert gerar_schema_yml(contratos) == gerar_schema_yml(contratos)


def test_testes_singulares_sao_deterministicos(fct):
    assert gerar_testes_singulares(fct) == gerar_testes_singulares(fct)


def test_doc_e_deterministica(fct):
    assert gerar_doc(fct) == gerar_doc(fct)


def test_regerar_nao_muda_bytes(contratos, tmp_path):
    a = escrever(contratos, tmp_path / "dbt", tmp_path / "docs")
    bytes_a = {k: p.read_bytes() for k, p in a.items()}
    b = escrever(contratos, tmp_path / "dbt", tmp_path / "docs")
    bytes_b = {k: p.read_bytes() for k, p in b.items()}
    assert bytes_a == bytes_b


def test_regeracao_remove_teste_orfao(contratos, tmp_path):
    dbt_dir = tmp_path / "dbt"
    (dbt_dir / "tests").mkdir(parents=True)
    orfao = dbt_dir / "tests" / "assert_fct_pedidos_invariante_removida.sql"
    orfao.write_text("select 1", encoding="utf-8")
    escrever(contratos, dbt_dir, tmp_path / "docs")
    assert not orfao.exists()


# --- RF2/RF3: cobertura da geração ------------------------------------------


def test_toda_invariante_nativa_vira_teste_no_schema(contratos, fct):
    out = gerar_schema_yml(contratos)
    for inv in fct.native_invariants:
        if inv.type == "unique":
            assert "- unique" in out
        elif inv.type == "not_null":
            assert "- not_null" in out
        elif inv.type == "accepted_values":
            for v in inv.values:
                assert f"'{v}'" in out
        elif inv.type == "relationship":
            assert f"ref('{inv.references}')" in out


def test_toda_invariante_singular_vira_arquivo(fct):
    arquivos = gerar_testes_singulares(fct)
    assert len(arquivos) == len(fct.singular_invariants)
    for inv in fct.singular_invariants:
        assert f"assert_{fct.dataset}_{inv.slug}.sql" in arquivos


def test_teste_singular_reprova_devolvendo_linhas(fct):
    """Convenção do dbt: teste singular falha quando retorna linhas."""
    for conteudo in gerar_testes_singulares(fct).values():
        assert "select" in conteudo.lower()
        assert "ref('fct_pedidos')" in conteudo


def test_descricao_da_coluna_chega_no_schema(contratos, fct):
    out = gerar_schema_yml(contratos)
    for coluna in fct.columns:
        primeira = coluna.description.split()[0]
        assert primeira in out


# --- CA6: toda garantia documentada -----------------------------------------


def test_toda_garantia_aparece_na_doc(fct):
    doc = gerar_doc(fct)
    for inv in fct.invariants:
        assert inv.slug in doc, f"invariante '{inv.slug}' ausente da documentação"
        assert inv.business_rule.split()[0] in doc


def test_doc_declara_o_que_nao_garante(fct):
    assert "NÃO garante" in gerar_doc(fct)


def test_doc_lista_todas_as_colunas(fct):
    doc = gerar_doc(fct)
    for coluna in fct.columns:
        assert f"`{coluna.name}`" in doc


def test_doc_aponta_como_mudar(fct):
    assert "make build" in gerar_doc(fct)


# --- YAML gerado é válido ---------------------------------------------------


def test_schema_gerado_e_yaml_valido(contratos):
    import yaml

    dados = yaml.safe_load(gerar_schema_yml(contratos))
    assert dados["version"] == 2
    nomes = {m["name"] for m in dados["models"]}
    assert nomes == {c.dataset for c in contratos}


def test_arquivos_escritos_no_projeto_real():
    """O que está versionado bate com o que o gerador produz agora."""
    root = Path(__file__).resolve().parents[1]
    contratos = load_all()
    esperado = gerar_schema_yml(contratos)
    atual = (root / "dbt" / "models" / "marts" / "schema.yml").read_text(
        encoding="utf-8"
    )
    assert atual == esperado, "schema.yml versionado está fora de sincronia"
