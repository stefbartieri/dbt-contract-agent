# Plano de implementação — Spec 001

**Spec:** [spec.md](spec.md) · **Constituição:** v1.0.0

---

## Arquitetura

```
                       ESCRITO POR GENTE
                    ┌──────────────────────┐
                    │ contracts/*.yml      │   chave, grão, colunas,
                    │ o data contract      │   invariantes, descrições
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ contract.py          │   validação estrutural
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────────┐ ┌────────────┐ ┌────────────────┐
     │ schema.yml     │ │ tests/*.sql│ │ docs/*.md      │   GERADO
     │ testes nativos │ │ singulares │ │ pra negócio    │   nunca editado
     └────────┬───────┘ └─────┬──────┘ └────────────────┘   à mão
              └───────┬───────┘
                      ▼
                 ┌─────────┐
                 │ dbt test│
                 └────┬────┘
                      │
    ═══════════════════════════════════════════════════
     A PARTE QUE IMPORTA: o teste consegue reprovar?
    ═══════════════════════════════════════════════════
                      │
        ┌─────────────▼─────────────┐
        │ mutate.py                 │  injeta UMA violação mínima
        │ uma mutação por invariante│  por invariante declarada
        └─────────────┬─────────────┘
                      ▼
              ┌───────────────┐
              │ evals/runner  │  detecção · especificidade ·
              └───────────────┘  testes decorativos
```

O eixo do projeto não é a geração — é a coluna de baixo. Gerar YAML é
transformação de dados. Provar que o YAML gerado **pega violação real** é o que
transforma uma suíte verde em evidência.

## Decisões técnicas

| Decisão | Escolha | Por quê | Alternativa descartada |
|---|---|---|---|
| Warehouse | DuckDB + dbt-duckdb | Roda offline em segundos, com dbt de verdade | Postgres — exige daemon |
| Formato do contrato | YAML próprio | Controle sobre o vocabulário de invariantes | dbt `contract:` nativo — só cobre tipo e nulidade |
| Testes compostos | Testes singulares SQL | O dbt não expressa `a <= b` nativamente | macro custom — mais indireção, mesmo resultado |
| Avaliação | Mutação | Mede se o teste pega violação, não se existe | contar testes — é a métrica que criou o problema |
| Mutação | Mínima, 1 linha | Testa sensibilidade | corromper a tabela — qualquer teste pegaria |
| LLM | Proposta marcada | Princípio III | gerar direto — garantia sem revisão |

## Modelo de dados

```
stg_pedidos ─┐
             ├──▶ fct_pedidos   (grão: pedido)      contrato principal
stg_clientes ┘
                  dim_clientes  (grão: cliente)     alvo de relationship
```

`fct_pedidos` carrega invariantes dos oito tipos de uma vez — é o caso que
exercita o compilador inteiro.

## As mutações, e por que cada uma é mínima

| Invariante | Mutação | Por que mínima |
|---|---|---|
| `unique` | duplica **uma** linha | um `unique` mal escrito passa com 1 duplicata |
| `not_null` | anula **uma** célula | idem |
| `accepted_values` | troca **um** valor por um fora do domínio | idem |
| `range` | põe **uma** linha 1 centavo abaixo do mínimo | testa a borda, não a ordem de grandeza |
| `relationship` | aponta **uma** FK para id inexistente | idem |
| `expression` | viola `liquido <= bruto` em **uma** linha, por 0,01 | idem |
| `grain` | duplica **um** par de chave composta | testa a combinação, não a coluna |
| `row_count` | apaga linhas até 1 abaixo do mínimo | testa a borda declarada |

Mutação na borda é decisão de projeto: um teste com limite errado por um
centavo passa numa mutação grosseira e reprova nesta.

## Fases

### Fase 1 — Contrato e validação
Esquema, carga, validação estrutural, mensagens que apontam o campo.

### Fase 2 — Dados e dbt
Gerador determinístico; projeto dbt com staging e marts.

### Fase 3 — Geradores
`schema.yml`, testes singulares, documentação. Cabeçalho de aviso, saída
determinística, ordenação estável.

### Fase 4 — Mutação
Uma mutação por tipo de invariante, mínima, derivada do contrato.

### Fase 5 — Avaliação
Runner que roda dbt por mutação, mede detecção, especificidade e testes
decorativos.

### Fase 6 — LLM e empacotamento
Proposta de descrição e de invariante. README, Makefile, CI, LICENSE.

## Rastreabilidade

| Requisito | Fase | Artefato | Teste |
|---|---|---|---|
| RF1 validação | 1 | `contract.py` | `test_contract.py` |
| RF2 schema.yml | 3 | `generate.py` | `test_generate.py` |
| RF3 singulares | 3 | `generate.py` | `test_generate.py` |
| RF4 docs | 3 | `generate.py` | `test_generate.py::test_doc_*` |
| RF5 mutação | 4 | `mutate.py` | `test_mutate.py` |
| RF6 avaliação | 5 | `evals/runner.py` | relatório |
| CA2 detecção 100% | 4,5 | `evals/runner.py` | **não negociável** |
| CA3 zero decorativo | 5 | `evals/runner.py` | relatório |
| CA5 diff vazio | 3 | CI | workflow |

## Como sei que falhei

- Alguma invariante não é pega pela sua mutação → o teste gerado é decorativo, e
  a tese do projeto cai (CA2).
- Um teste nunca falha em mutação nenhuma → ele não verifica nada (CA3).
- A mutação precisa ser grosseira para o teste pegar → o teste é insensível, e
  passaria numa violação real de borda.
- O contrato fica mais longo que o YAML que ele gera → o projeto adicionou
  cerimônia sem reduzir atrito.
