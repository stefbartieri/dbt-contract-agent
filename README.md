<div align="center">

# dbt-contract-agent

### Data contracts como fonte única de testes e documentação dbt

**Com a pergunta que ninguém faz: o teste gerado consegue reprovar?**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.8-FF694B?logo=dbt&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-1.5-FFF000?logo=duckdb&logoColor=black)
![Testes](https://img.shields.io/badge/testes-42-success)
![Cobertura](https://img.shields.io/badge/cobertura-88%25-success)
![Mutação](https://img.shields.io/badge/detec%C3%A7%C3%A3o%20de%20muta%C3%A7%C3%A3o-100%25-success)
![Decorativos](https://img.shields.io/badge/testes%20decorativos-0-success)

[A tese](#a-tese) •
[Como rodar](#como-rodar) •
[Resultados](#resultados) •
[Arquitetura](#arquitetura) •
[SDD](#como-este-projeto-foi-especificado) •
[Limitações](#limitações)

</div>

---

## A tese

Um projeto dbt maduro tem centenas de blocos assim espalhados pelos `schema.yml`:

```yaml
- name: valor_liquido
  tests:
    - not_null
    - dbt_utils.accepted_range: {min_value: 0}
```

Três coisas dão errado com esse arranjo, sempre na mesma ordem.

**O `schema.yml` vira o contrato por omissão.** Ninguém escreveu em lugar nenhum
que `valor_liquido` não pode ser negativo — a regra existe apenas como efeito
colateral de um teste. Quando alguém pergunta "o que este dataset garante?", a
resposta honesta é "leia os testes".

**Documentação e testes divergem em silêncio.** A descrição diz uma coisa, o
teste verifica outra, e nada quebra quando as duas se separam — porque nada liga
uma à outra.

**O custo marginal de uma garantia nova é alto.** Adicionar uma invariante
significa editar YAML em vários lugares e lembrar de atualizar a descrição. O
resultado previsível é o observado: times declaram menos garantias do que
realmente têm.

E há um problema mais sutil, que este projeto trata como central:

> **Ninguém verifica se os testes conseguem falhar.**

Um `accepted_range` com limites errados passa sempre. Uma suíte verde é lida
como dado confiável, quando pode ser apenas uma suíte que não testa nada.

Aqui, o **data contract** é escrito por uma pessoa, e testes, documentação e
`schema.yml` são derivados dele. Mas a parte que importa não é gerar YAML — é
**provar que o YAML gerado serve para alguma coisa**, mutando os dados e
exigindo que cada teste pegue a violação que ele deveria pegar.

## Como rodar

```bash
git clone https://github.com/stefbartieri/dbt-contract-agent
cd dbt-contract-agent
pip install -r requirements.txt
make demo
```

`make demo` gera os dados, compila os contratos, roda o dbt e executa a
avaliação por mutação.

```bash
make build   # contrato -> schema.yml + testes + docs
make eval    # avaliação por mutação
```

## Resultados

```
  Avaliação por mutação — o teste gerado consegue reprovar?
  ----------------------------------------------------------------------
  Mutações               15/15  detectadas
  Específicas            11/15  sem falha colateral
  Testes no projeto       15
  ----------------------------------------------------------------------
  Detecção         100.0%   CA2 == 100%  [PASS]
  Especificidade    73.3%
  Decorativos            0   CA3 == 0     [PASS]
  Verde no íntegro         sim   CA4          [PASS]
```

**Detecção 100%** — toda invariante declarada é pega pelo teste que ela gerou.

**Zero testes decorativos** — nenhum dos 15 testes do projeto passou por todas
as mutações sem nunca falhar. Cada um verifica algo real.

### As mutações são mínimas, de propósito

| Invariante | Mutação | Por que mínima |
|---|---|---|
| `unique` | duplica **uma** linha | um `unique` mal escrito passa com 1 duplicata |
| `not_null` | anula **uma** célula | idem |
| `accepted_values` | **um** valor fora do domínio | idem |
| `range` | **um centavo** abaixo do mínimo | testa a borda, não a ordem de grandeza |
| `relationship` | **uma** FK para id inexistente | idem |
| `expression` | viola por **0,01** | idem |
| `row_count` | **uma linha** abaixo do mínimo | testa a borda declarada |

Corromper a tabela inteira faria qualquer teste passar na avaliação. Um teste
com limite errado por um centavo passa numa mutação grosseira e **reprova
nesta**. É sensibilidade que se mede aqui, não existência.

### Sobre a especificidade de 73,3%

Quatro mutações derrubaram mais de um teste. Isso **não é defeito** — é
acoplamento real entre garantias, e vale entender:

- anular `cliente_id` quebra também o teste de `relationship`, porque nulo não
  casa com a dimensão;
- `valor_liquido` negativo quebra a faixa **e** a aritmética do pedido, porque
  as duas invariantes falam do mesmo número por ângulos diferentes.

Medir especificidade expõe esse acoplamento em vez de escondê-lo. Um time que vê
isso sabe que, quando os dois testes acendem juntos, há uma causa só.

## Arquitetura

```
                       ESCRITO POR GENTE
                    ┌──────────────────────┐
                    │ contracts/*.yml      │   chave, grão, colunas,
                    │ o data contract      │   invariantes, descrições
                    └──────────┬───────────┘
                               │  validação estrutural
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────────┐ ┌────────────┐ ┌────────────────┐
     │ schema.yml     │ │ tests/*.sql│ │ docs/*.md      │   GERADO
     │ testes nativos │ │ singulares │ │ pra negócio    │   nunca editado
     └────────┬───────┘ └─────┬──────┘ └────────────────┘   à mão
              └───────┬───────┘
                      ▼
                 ┌─────────┐
                 │ dbt test│
                 └────┬────┘
    ═══════════════════════════════════════════════════
     A PARTE QUE IMPORTA: o teste consegue reprovar?
    ═══════════════════════════════════════════════════
                      ▼
        ┌───────────────────────────┐
        │ mutate.py                 │  UMA violação mínima
        │ uma mutação por invariante│  por invariante declarada
        └─────────────┬─────────────┘
                      ▼
              ┌───────────────┐
              │ evals/runner  │  detecção · especificidade ·
              └───────────────┘  testes decorativos
```

### Os 8 tipos de invariante

| Tipo | Vira |
|---|---|
| `unique`, `not_null`, `accepted_values`, `relationship` | teste nativo dbt |
| `grain` | `dbt_utils.unique_combination_of_columns` |
| `range`, `expression`, `row_count` | teste singular SQL gerado |

### O contrato é legível por quem não lê SQL

```yaml
- type: range
  column: valor_liquido
  min: 0
  business_rule: >
    Receita negativa não existe neste dataset. Devolução é registrada como
    status, não como valor negativo — se aparecer negativo, alguém mudou essa
    convenção sem atualizar as métricas.
```

`business_rule` é **campo obrigatório**: a carga do contrato falha sem ele. Uma
garantia sem a consequência de violá-la não documenta nada — e é essa prosa que
vai para a documentação gerada, sem ninguém transcrever.

O mesmo vale para `description` em cada coluna. O contrato existe para ser lido
por gente de negócio; sem descrição, ele volta a ser um schema técnico.

### O YAML gerado nunca é editado à mão

Todo arquivo gerado carrega cabeçalho de aviso e é reescrito por completo a cada
build. Testes órfãos de invariantes removidas são apagados. O CI regenera tudo e
**falha se o diff não for vazio** — edição manual é detectada, não tolerada.

## Como este projeto foi especificado

**Spec-Driven Development**: constituição → spec → plano → tarefas → código.

| Documento | O que fixa |
|---|---|
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | 7 princípios inegociáveis |
| [`specs/001-contract-gen/spec.md`](specs/001-contract-gen/spec.md) | Problema, hipótese, tipos de invariante, critérios, riscos |
| [`specs/001-contract-gen/plan.md`](specs/001-contract-gen/plan.md) | Arquitetura, decisões com alternativa descartada, rastreabilidade |
| [`specs/001-contract-gen/tasks.md`](specs/001-contract-gen/tasks.md) | 18 tarefas com critério de pronto |

O princípio que define o projeto:

> **Um teste gerado que nunca falha é pior que nenhum teste.** Cobertura aqui
> não é "quantos testes geramos", é "quantas violações reais os testes pegam".

## O papel do LLM

Estreito e verificável, por decisão de projeto (Princípio III). O modelo faz
duas coisas:

1. Reescreve descrição técnica em linguagem de negócio.
2. Sugere invariantes plausíveis não declaradas, a partir do perfil dos dados.

**Nunca decide chave, grão ou domínio.** Toda sugestão sai como proposta
marcada, com confiança e justificativa, pronta para colar no contrato — depois
de revisada. Aceitar é ato humano.

O motivo é direto: uma garantia estrutural aceita sem revisão é pior que a
ausência dela, porque alguém vai confiar. Uma prosa mal escrita só é feia.

## Limitações

Declaradas, não escondidas.

**A razão de linhas é modesta: 1,6x.** 177 linhas de contrato produzem 291
linhas de artefato. O ganho real não é volume — é ter **um lugar só** para a
garantia, e a prosa de negócio que o `schema.yml` nunca teve. Quem esperava
reduzir linhas de YAML vai se decepcionar; quem queria acabar com a divergência
entre teste e documentação, não.

**As mutações foram desenhadas junto com os geradores.** Há risco de
tautologia — eu escrevi o teste e escrevi a mutação. A mitigação foi derivar a
mutação da *invariante declarada no contrato*, não do SQL gerado, e medir
especificidade. Um avaliador externo escrevendo as mutações seria mais forte.

**15 invariantes em 2 datasets** é um projeto pequeno. Nada aqui foi exercitado
em escala de centenas de modelos, onde o custo de regenerar tudo a cada build
passa a importar.

**Sem propagação de contrato entre camadas.** Uma garantia em `fct_pedidos` não
se propaga para modelos que consomem dele.

**Frescor não é testado.** Exigiria dependência de relógio real, o que quebraria
o determinismo (Princípio VI).

**DuckDB não é um warehouse de produção.** O SQL gerado é ANSI, mas nada aqui
exercitou custo de query nem permissão.

## Estrutura

```
.specify/memory/constitution.md   princípios do projeto
specs/001-contract-gen/           spec, plano, tarefas
contracts/                        OS CONTRATOS — escritos por gente
dbt/
  models/marts/schema.yml         GERADO
  tests/assert_*.sql              GERADO
docs/                             GERADO
src/contract_agent/
  contract.py                     carga e validação
  generate.py                     contrato -> schema.yml, testes, docs
  mutate.py                       uma violação mínima por invariante
  llm.py                          descrições e sugestões (proposta marcada)
  cli.py                          make build
evals/runner.py                   detecção / especificidade / decorativos
tests/                            42 testes
```

## Licença

MIT — veja [LICENSE](LICENSE).
