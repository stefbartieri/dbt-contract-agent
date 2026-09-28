-- ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.
-- Origem: contracts/fct_pedidos.yml, invariante 'range_valor_liquido'
--
-- Regra de negócio:
--   Receita negativa não existe neste dataset. Devolução é registrada
--   como status, não como valor negativo — se aparecer negativo, alguém
--   mudou essa convenção sem atualizar as métricas.

select valor_liquido, count(*) as linhas
from {{ ref('fct_pedidos') }}
where valor_liquido < 0
group by 1
order by 1
