<!-- Gerado a partir de contracts/dim_clientes.yml. NÃO EDITE À MÃO. -->

# dim_clientes

Um cliente por linha. É a dimensão conformada de cliente, alvo do relacionamento declarado em fct_pedidos.

**Responsável:** analytics-engineering  
**Grão:** cliente_id

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `cliente_id` | integer | Identificador único do cliente no sistema de origem. |
| `regiao` | varchar | Macrorregião do endereço principal do cliente. |
| `segmento` | varchar | Classificação comercial do cliente por recorrência de compra. |

## O que este dataset garante

### Único — `cliente_id`

Cada cliente aparece uma única vez. Duplicata aqui causa fan-out em todo join com a dimensão, inflando receita sem erro aparente.

*Verificado por:* `unique_cliente_id`

### Sempre preenchido — `cliente_id`

A chave da dimensão nunca é nula. Nulo quebra o join e descarta pedidos.

*Verificado por:* `not_null_cliente_id`

### Valores aceitos — `regiao`

Região fora desta lista some dos relatórios geográficos, e a soma das regiões deixa de bater com o total.

*Verificado por:* `accepted_values_regiao` · valores: `norte`, `nordeste`, `centro-oeste`, `sudeste`, `sul`

### Valores aceitos — `segmento`

Segmento novo sem mapeamento quebra toda análise de coorte.

*Verificado por:* `accepted_values_segmento` · valores: `novo`, `recorrente`, `vip`

## O que este dataset NÃO garante

- Frescor: o contrato não declara janela máxima de atraso na carga.
- Completude da origem: garantimos o que chegou, não que tudo chegou.
- Estabilidade histórica: reprocessamento pode alterar linhas antigas.

---

Para mudar qualquer garantia acima, edite `contracts/dim_clientes.yml` e rode `make build`. Este arquivo é regenerado.
