select
    cast(cliente_id as integer) as cliente_id,
    cast(regiao     as varchar) as regiao,
    cast(segmento   as varchar) as segmento
from {{ source('raw', 'clientes') }}
