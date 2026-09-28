-- Grão: um cliente. Garantias em contracts/dim_clientes.yml.
select * from {{ ref('stg_clientes') }}
