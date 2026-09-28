-- ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.
-- Origem: contracts/fct_pedidos.yml, invariante 'liquido_nao_excede_bruto'
--
-- Regra de negócio:
--   O valor líquido nunca supera o bruto, porque desconto só subtrai.
--   Violação indica sinal trocado no cálculo de desconto.

select *
from {{ ref('fct_pedidos') }}
where not (valor_liquido <= valor_bruto)
order by 1
