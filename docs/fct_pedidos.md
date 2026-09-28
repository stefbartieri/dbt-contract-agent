<!-- Gerado a partir de contracts/fct_pedidos.yml. NÃO EDITE À MÃO. -->

# fct_pedidos

Um pedido por linha, já consolidado. É a base de todas as métricas de venda. Inclui pedidos cancelados, identificados pelo status — quem quiser só venda efetiva precisa filtrar.

**Responsável:** analytics-engineering  
**Grão:** pedido_id

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `pedido_id` | integer | Identificador único do pedido no sistema de origem. |
| `cliente_id` | integer | Cliente que fez o pedido. Referencia dim_clientes. |
| `data_pedido` | date | Data em que o pedido foi criado, no fuso de São Paulo. |
| `canal` | varchar | Canal de origem da venda. |
| `status` | varchar | Situação atual do pedido no ciclo de vida. |
| `valor_bruto` | decimal | Soma dos itens antes de qualquer desconto, sem frete. |
| `valor_desconto` | decimal | Total de descontos aplicados ao pedido. |
| `valor_liquido` | decimal | Valor bruto menos descontos. É o que entra em receita. |
| `itens` | integer | Quantidade de itens distintos no pedido. |

## O que este dataset garante

### Único — `pedido_id`

Cada pedido aparece uma única vez. Se aparecer duas, alguma ingestão reprocessou o lote e toda métrica de volume está inflada.

*Verificado por:* `unique_pedido_id`

### Sempre preenchido — `valor_liquido`

Todo pedido tem valor líquido, mesmo que zero. Nulo aqui significa que o cálculo falhou, e a soma de receita fica silenciosamente menor.

*Verificado por:* `not_null_valor_liquido`

### Sempre preenchido — `cliente_id`

Todo pedido pertence a um cliente. Nulo impede qualquer recorte por segmento ou região.

*Verificado por:* `not_null_cliente_id`

### Valores aceitos — `status`

Status fora desta lista significa que o sistema de origem criou um estado novo sem avisar. Métricas que filtram por status passam a ignorar esses pedidos em silêncio.

*Verificado por:* `accepted_values_status` · valores: `aprovado`, `pendente`, `cancelado`, `devolvido`

### Valores aceitos — `canal`

Canal novo sem mapeamento some dos relatórios por canal, e o total deixa de bater com o total geral.

*Verificado por:* `accepted_values_canal` · valores: `app`, `site`, `marketplace`, `loja`

### Faixa — `valor_liquido`

Receita negativa não existe neste dataset. Devolução é registrada como status, não como valor negativo — se aparecer negativo, alguém mudou essa convenção sem atualizar as métricas.

*Verificado por:* `range_valor_liquido` · mínimo 0

### Faixa — `itens`

Todo pedido tem ao menos um item. Acima de 200 é praticamente certo que houve fan-out de join na origem, não um pedido real.

*Verificado por:* `range_itens` · mínimo 1, máximo 200

### Referência íntegra — `cliente_id`

Todo cliente_id existe na dimensão. Quebra aqui faz o inner join descartar pedidos silenciosamente, e a receita some sem erro nenhum.

*Verificado por:* `relationship_cliente_id` · referencia `dim_clientes.cliente_id`

### Regra composta — `—`

O valor líquido nunca supera o bruto, porque desconto só subtrai. Violação indica sinal trocado no cálculo de desconto.

*Verificado por:* `liquido_nao_excede_bruto` · `valor_liquido <= valor_bruto`

### Regra composta — `—`

A aritmética do pedido fecha. Esta é a invariante que pega erro de arredondamento acumulado e desconto aplicado duas vezes.

*Verificado por:* `liquido_igual_bruto_menos_desconto` · `abs(valor_liquido - (valor_bruto - valor_desconto)) < 0.01`

### Volume — `—`

O volume diário histórico fica nesta faixa. Fora dela, ou a carga veio incompleta ou duplicou — em ambos os casos, não publique.

*Verificado por:* `row_count` · mínimo 8000, máximo 20000

## O que este dataset NÃO garante

- Frescor: o contrato não declara janela máxima de atraso na carga.
- Completude da origem: garantimos o que chegou, não que tudo chegou.
- Estabilidade histórica: reprocessamento pode alterar linhas antigas.

---

Para mudar qualquer garantia acima, edite `contracts/fct_pedidos.yml` e rode `make build`. Este arquivo é regenerado.
