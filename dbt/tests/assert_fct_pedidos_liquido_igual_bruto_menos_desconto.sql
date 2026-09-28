-- ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.
-- Origem: contracts/fct_pedidos.yml, invariante 'liquido_igual_bruto_menos_desconto'
--
-- Regra de negócio:
--   A aritmética do pedido fecha. Esta é a invariante que pega erro de
--   arredondamento acumulado e desconto aplicado duas vezes.

select *
from {{ ref('fct_pedidos') }}
where not (abs(valor_liquido - (valor_bruto - valor_desconto)) < 0.01)
order by 1
