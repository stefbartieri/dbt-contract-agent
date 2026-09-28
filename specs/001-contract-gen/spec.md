# Spec 001 — Data contracts como fonte de testes e documentação dbt

**Status:** aprovada · **Autoria:** Stefania Gualtieri Bartoli · **Data:** 2026-09-28
**Constituição aplicável:** v1.0.0

---

## 1. Problema

Um projeto dbt maduro tem centenas de blocos assim espalhados pelos `schema.yml`:

```yaml
- name: valor_liquido
  tests:
    - not_null
    - dbt_utils.accepted_range: {min_value: 0}
```

Três coisas dão errado com esse arranjo, sempre na mesma ordem.

**O `schema.yml` vira o contrato por omissão.** Ninguém escreveu em lugar nenhum
que `valor_liquido` não pode ser negativo — a regra existe apenas como efeito
colateral de um teste. Quando alguém pergunta "o que este dataset garante?", a
resposta é "leia os testes".

**A documentação e os testes divergem em silêncio.** A descrição diz uma coisa,
o teste verifica outra, e nada quebra quando as duas se separam — porque nada
liga uma à outra.

**O custo marginal de uma garantia nova é alto demais.** Adicionar uma
invariante significa editar YAML em vários lugares, lembrar de atualizar a
descrição e torcer para ninguém ter copiado o bloco antigo. O resultado previsto
é o que se observa: times declaram menos garantias do que realmente têm.

E há um problema mais sutil, que este projeto trata como central: **ninguém
verifica se os testes conseguem falhar.** Um `accepted_range` com limites
errados passa sempre, e uma suíte verde é interpretada como dado confiável.

## 2. Hipótese

Se o **data contract** for um artefato de primeira classe — escrito por uma
pessoa, versionado, legível por negócio — e os testes dbt, a documentação e o
`schema.yml` forem **derivados** dele, então:

- a garantia passa a ter um lugar único, e divergência vira impossível
- o custo marginal de uma invariante nova cai para uma linha de YAML
- a qualidade dos testes passa a ser **mensurável**, porque é possível mutar os
  dados e verificar se cada teste pega a violação que deveria pegar

A parte não-trivial não é gerar YAML. É provar que o YAML gerado **serve para
alguma coisa**.

## 3. Escopo

### Dentro

| # | Entrega |
|---|---|
| E1 | Esquema de data contract em YAML, com validação estrutural |
| E2 | Projeto dbt sobre DuckDB com um mart real |
| E3 | Compilador contrato → `schema.yml` (testes + descrições) |
| E4 | Compilador contrato → testes singulares SQL para invariantes compostas |
| E5 | Compilador contrato → documentação em Markdown |
| E6 | Motor de mutação: injeta uma violação por invariante |
| E7 | Avaliação por mutação: mede quais testes pegam o quê |
| E8 | Modo LLM opcional: descrições e sugestão de invariantes, como proposta |

### Fora

- Descoberta automática de contrato a partir dos dados. O contrato é decisão
  humana (Princípio I).
- Registro central de contratos, versionamento semântico, negociação entre times.
- Testes de frescor com dependência de relógio real.
- Propagação de contrato entre camadas (contract inheritance).

## 4. Usuários

**U1 — Analytics engineer.** Escreve o contrato, roda `make build`, recebe testes
e documentação. Nunca edita o YAML gerado.

**U2 — Pessoa de negócio / stewardship.** Lê o contrato e a documentação gerada
para saber o que o dataset garante, sem ler SQL.

**U3 — Revisor de PR.** Vê no diff que uma garantia mudou — uma linha no
contrato — em vez de sete blocos de YAML espalhados.

## 5. Tipos de invariante

| Tipo | Exemplo | Vira |
|---|---|---|
| `unique` | `pedido_id` é único | `unique` |
| `not_null` | `valor_liquido` sempre presente | `not_null` |
| `accepted_values` | `status` em [aprovado, cancelado] | `accepted_values` |
| `range` | `valor_liquido >= 0` | teste singular SQL |
| `relationship` | `cliente_id` existe em `dim_clientes` | `relationships` |
| `expression` | `valor_liquido <= valor_bruto` | teste singular SQL |
| `grain` | único por (pedido_id, item_id) | `dbt_utils.unique_combination_of_columns` |
| `row_count` | entre 500 e 50.000 linhas | teste singular SQL |

## 6. Requisitos funcionais

### RF1 — Validação do contrato

Contrato malformado falha na carga com mensagem que aponta o campo. Coluna
referenciada por invariante deve existir na lista de colunas; tipo de invariante
deve ser conhecido; `grain` deve ser subconjunto das colunas.

### RF2 — Geração de `schema.yml`

Cada invariante mapeável para teste nativo dbt vira teste nativo. Cada coluna
recebe a descrição do contrato. Arquivo carrega cabeçalho de aviso e é
determinístico byte a byte.

### RF3 — Geração de testes singulares

Invariantes que o dbt não expressa nativamente (`range`, `expression`,
`row_count`) viram arquivos SQL em `tests/`, um por invariante, nomeados de
forma previsível a partir do contrato.

### RF4 — Geração de documentação

Markdown por dataset: grão, chave, colunas com tipo e descrição, tabela de
garantias em linguagem de negócio, e o que **não** é garantido.

### RF5 — Motor de mutação

Para cada invariante declarada, uma mutação correspondente que a viola de forma
mínima — uma linha, não a tabela inteira. Mutação mínima é deliberada: testa se
o teste é sensível, não se é grosseiro.

### RF6 — Avaliação por mutação

Para cada mutação: roda o dbt, observa quais testes falharam. Mede:

- **Detecção** — o teste esperado falhou?
- **Especificidade** — apenas ele falhou, ou houve falha colateral?
- **Testes decorativos** — algum teste nunca falhou em mutação nenhuma?

### RF7 — Modo LLM opcional

Duas funções, ambas como proposta marcada:
1. Reescrever descrições técnicas em linguagem de negócio.
2. Sugerir invariantes plausíveis não declaradas, a partir do perfil dos dados.

Nunca decide chave, grão ou domínio (Princípio III).

## 7. Requisitos não-funcionais

| # | Requisito | Verificação |
|---|---|---|
| RNF1 | Geração determinística byte a byte | CI gera 2× e compara |
| RNF2 | Regenerar não produz diff | CI falha se `git diff` não for vazio |
| RNF3 | `make demo` em menos de 90s | medido no CI |
| RNF4 | Zero dependência de rede no caminho padrão | CI sem egress |
| RNF5 | Cobertura ≥ 85% em `contract` e `generate` | `pytest --cov` |

## 8. Critérios de aceitação

- [ ] **CA1** — `make demo` roda em repositório recém-clonado.
- [ ] **CA2** — Taxa de detecção de mutação = **100%**. Toda invariante
      declarada é pega pelo teste que ela gerou. Não negociável: é a tese.
- [ ] **CA3** — **Zero testes decorativos.** Nenhum teste gerado pode passar por
      todas as mutações sem nunca falhar.
- [ ] **CA4** — Zero falsos positivos: o dbt fica verde no dataset íntegro.
- [ ] **CA5** — Regenerar duas vezes produz diff vazio.
- [ ] **CA6** — Toda garantia do contrato aparece na documentação gerada.

## 9. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Mutações desenhadas junto com os testes viram tautologia | Alto | Mutação é mínima (1 linha) e derivada da invariante, não do teste; especificidade é medida |
| Contrato vira YAML tão verboso quanto o `schema.yml` que substitui | Médio | Medido: o README compara linhas de contrato com linhas geradas |
| DuckDB não representa warehouse real | Médio | Testes gerados usam SQL ANSI; declarado em Limitações |
| Sugestões do LLM criam falsa sensação de cobertura | Alto | Proposta marcada, nunca aplicada; Princípio III |

## 10. Perguntas em aberto

- Invariantes entre datasets (soma de `fct_itens` = total de `fct_pedidos`)
  pertencem a qual contrato?
- O contrato deveria declarar severidade por invariante, para distinguir o que
  quebra o pipeline do que só alerta?
