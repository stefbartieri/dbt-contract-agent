-- Grão: um pedido. As garantias deste modelo vivem em contracts/fct_pedidos.yml.
select * from {{ ref('stg_pedidos') }}
