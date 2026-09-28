# Constituição do projeto — dbt-contract-agent

Princípios inegociáveis. Requisito que conflita com um princípio perde — ou o
princípio é emendado com justificativa registrada.

**Versão:** 1.0.0 · **Ratificada em:** 2026-09-28

---

## Princípio I — O contrato é escrito por gente; os testes são derivados dele

Um data contract declara o que o negócio garante sobre um dataset: chave, grão,
colunas obrigatórias, domínios, invariantes, frescor. Isso é decisão humana.

Testes dbt, documentação e `schema.yml` são **consequência mecânica** dessa
decisão, e não devem ser escritos à mão.

**Motivo:** o trabalho de valor está em decidir que `valor_liquido` nunca pode
ser negativo. Transcrever isso em YAML sete vezes não é trabalho, é atrito — e
é onde o contrato e os testes silenciosamente divergem.

## Princípio II — Um teste gerado que nunca falha é pior que nenhum teste

Todo teste gerado precisa ser **capaz de reprovar**. A suíte de avaliação prova
isso mutando os dados: se um teste não pega a mutação que ele deveria pegar, o
teste é decorativo e conta como defeito.

**Como verificamos:** `evals/runner.py` injeta uma violação por invariante
declarada e exige que exatamente o teste correspondente falhe.

**Consequência:** cobertura aqui não é "quantos testes geramos", é "quantas
violações reais os testes pegam".

## Princípio III — Geração é determinística; o LLM é opcional e auditado

O gerador padrão é determinístico: mesmo contrato, mesmos arquivos, byte a byte.

O LLM entra em um papel estreito e verificável: **escrever a descrição em
linguagem de negócio** e **sugerir invariantes que o humano não declarou**. Ele
nunca decide a chave, o grão ou o domínio.

**Motivo:** o que o modelo produz de melhor é prosa e hipótese. O que ele produz
de pior é uma garantia estrutural que alguém vai confiar sem conferir.

**Regra:** toda sugestão do LLM entra como proposta marcada, nunca aplicada
direto. Aceitar é ato humano.

## Princípio IV — O YAML gerado nunca é editado à mão

Arquivo gerado carrega cabeçalho de aviso e é reescrito por completo a cada
execução. Se alguém precisa mudar um teste, muda o contrato.

**Como verificamos:** o CI regenera tudo e falha se o diff não for vazio. Edição
manual é detectada, não tolerada.

## Princípio V — Roda offline, em um comando, de graça

`make demo` gera os dados, compila o contrato, roda o dbt, executa a avaliação
de mutação. Sem chave de API, sem nuvem.

O modo LLM é explicitamente opcional e não afeta os números reproduzíveis.

## Princípio VI — Determinismo em tudo que alimenta um número

Semente fixa na geração e na mutação. Ordenação estável na serialização do YAML.
Sem `now()`, sem `random()` não semeado.

## Princípio VII — Uma violação silenciosa é o pior resultado possível

Entre um teste que falha demais e um que deixa passar, o projeto prefere o
primeiro. Falso positivo custa uma investigação; falso negativo custa uma
decisão de negócio tomada sobre número errado.

**Consequência:** a avaliação mede as duas taxas, e a de falso negativo é
critério de aceitação não negociável.

---

## Emendas

| Versão | Data | Mudança |
|---|---|---|
| 1.0.0 | 2026-09-28 | Ratificação inicial. |
