# Tarefas — Spec 001

`[P]` = pode rodar em paralelo com a anterior.

## Fase 1 — Contrato e validação

- [ ] **T001** `contracts/fct_pedidos.yml` — contrato com os 8 tipos de
      invariante, descrições em linguagem de negócio.
- [ ] **T002** `src/contract_agent/contract.py` — carga e validação.
      *Pronto quando:* invariante sobre coluna inexistente falha na carga,
      apontando o campo.
- [ ] **T003** [P] `contracts/dim_clientes.yml` — alvo do `relationship`.

## Fase 2 — Dados e dbt

- [ ] **T004** `data/generate.py` — semente 3, 12.000 pedidos, 2.500 clientes.
      *Pronto quando:* duas execuções dão hash idêntico.
- [ ] **T005** Projeto dbt: `stg_pedidos`, `stg_clientes`, `fct_pedidos`,
      `dim_clientes`. *Pronto quando:* `dbt build` verde no dado íntegro. **CA4**

## Fase 3 — Geradores

- [ ] **T006** `generate.py` → `schema.yml` com testes nativos e descrições.
      Cabeçalho de aviso. Ordenação estável. **RF2**
- [ ] **T007** `generate.py` → testes singulares SQL para `range`, `expression`
      e `row_count`. Nomes previsíveis. **RF3**
- [ ] **T008** `generate.py` → documentação Markdown com garantias e
      não-garantias. **RF4 / CA6**
- [ ] **T009** Determinismo byte a byte. *Pronto quando:* gerar 2× dá diff
      vazio. **CA5 / RNF1**

## Fase 4 — Mutação

- [ ] **T010** `mutate.py` — uma mutação mínima por tipo de invariante.
- [ ] **T011** Cada mutação registra qual invariante viola e como.
      *Pronto quando:* `test_mutate.py` prova que cada mutação altera
      exatamente uma linha (exceto `row_count`, que é por construção volumétrica).

## Fase 5 — Avaliação

- [ ] **T012** `evals/runner.py` — roda dbt por mutação, captura falhas.
- [ ] **T013** Métricas: detecção, especificidade, testes decorativos.
- [ ] **T014** Código de saída diferente de 0 se CA2, CA3 ou CA4 quebram.

## Fase 6 — LLM e empacotamento

- [ ] **T015** `llm.py` — descrição em linguagem de negócio e sugestão de
      invariante, ambas como proposta marcada. **RF7**
- [ ] **T016** `README.md` com tese, números e limitações honestas.
- [ ] **T017** `Makefile`, CI com regeneração e diff vazio, `LICENSE`.
- [ ] **T018** [P] Topics do repositório.

## Critérios de saída

| ID | Critério | Como medir |
|---|---|---|
| CA1 | `make demo` do zero | clone limpo |
| CA2 | Detecção de mutação = 100% | `evals/runner.py` — **não negociável** |
| CA3 | Zero testes decorativos | `evals/runner.py` |
| CA4 | dbt verde no dado íntegro | `dbt build` |
| CA5 | Regenerar dá diff vazio | CI |
| CA6 | Toda garantia documentada | `test_generate.py` |
