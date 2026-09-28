-- ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.
-- Origem: contracts/fct_pedidos.yml, invariante 'range_itens'
--
-- Regra de negócio:
--   Todo pedido tem ao menos um item. Acima de 200 é praticamente certo
--   que houve fan-out de join na origem, não um pedido real.

select itens, count(*) as linhas
from {{ ref('fct_pedidos') }}
where itens < 1 or itens > 200
group by 1
order by 1
