select
    cast(pedido_id      as integer)       as pedido_id,
    cast(cliente_id     as integer)       as cliente_id,
    cast(data_pedido    as date)          as data_pedido,
    cast(canal          as varchar)       as canal,
    cast(status         as varchar)       as status,
    cast(valor_bruto    as decimal(12,2)) as valor_bruto,
    cast(valor_desconto as decimal(12,2)) as valor_desconto,
    cast(valor_liquido  as decimal(12,2)) as valor_liquido,
    cast(itens          as integer)       as itens
from {{ source('raw', 'pedidos') }}
