-- ATENÇÃO: arquivo gerado por contract-agent. NÃO EDITE À MÃO.
-- Origem: contracts/fct_pedidos.yml, invariante 'row_count'
--
-- Regra de negócio:
--   O volume diário histórico fica nesta faixa. Fora dela, ou a carga
--   veio incompleta ou duplicou — em ambos os casos, não publique.

with contagem as (
    select count(*) as linhas from {{ ref('fct_pedidos') }}
)
select linhas from contagem
where linhas < 8000 or linhas > 20000
