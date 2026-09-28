"""Modo LLM — papel estreito e verificável.

Princípio III: o LLM nunca decide chave, grão ou domínio. Ele faz duas coisas
em que é genuinamente melhor que uma regra:

1. Reescrever descrição técnica em linguagem de negócio.
2. Sugerir invariantes plausíveis que ninguém declarou, a partir do perfil dos
   dados.

As duas saem como **proposta marcada**, nunca aplicadas. Aceitar é ato humano,
que se materializa editando o contrato à mão.

O motivo é simples: uma garantia estrutural aceita sem revisão é pior que a
ausência dela, porque alguém vai confiar. Uma prosa mal escrita só é feia.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .contract import Contract

MODELO_PADRAO = "claude-opus-5"

_SISTEMA_DESCRICAO = """Você reescreve descrições de colunas de um data contract.

O leitor é uma pessoa de negócio que não lê SQL. A descrição precisa dizer o que \
a coluna significa e, quando relevante, o que ela NÃO inclui.

Regras:
- Não invente semântica que não esteja na descrição original.
- Não mencione tipo de dado nem detalhe de implementação.
- Uma a duas frases. Português do Brasil.
- Se a descrição original já está boa, devolva-a sem mudança.

Responda SOMENTE com JSON: {"colunas": {"<nome>": "<descrição>"}}"""

_SISTEMA_INVARIANTE = """Você sugere invariantes de qualidade para um data contract.

Recebe o contrato atual e um perfil estatístico dos dados. Sugira garantias \
PLAUSÍVEIS que ainda não foram declaradas.

Regras:
- Nunca sugira chave primária, grão ou domínio fechado: isso é decisão humana.
- Sugira apenas: range, expression e relationship.
- Toda sugestão precisa de uma business_rule explicando a consequência de \
violar, não só o que ela verifica.
- Prefira poucas sugestões fortes a muitas fracas.
- Se o contrato já está completo, devolva lista vazia.

Responda SOMENTE com JSON:
{"sugestoes": [{"type": "...", "column": "...", "min": n, "max": n,
                "expression": "...", "business_rule": "...",
                "confianca": 0.0-1.0, "por_que": "..."}]}"""


@dataclass(frozen=True)
class Proposta:
    """Sugestão do modelo. Marcada, nunca aplicada (Princípio III)."""

    tipo: str
    conteudo: dict[str, Any]
    confianca: float
    justificativa: str

    def como_yaml(self) -> str:
        """Bloco pronto para colar no contrato — depois de revisar."""
        linhas = ["  # PROPOSTA DO MODELO — revise antes de aceitar.",
                  f"  # confiança declarada: {self.confianca:.0%}",
                  f"  # motivo: {self.justificativa}"]
        item = {k: v for k, v in self.conteudo.items() if v is not None}
        primeiro = True
        for chave, valor in item.items():
            prefixo = "  - " if primeiro else "    "
            primeiro = False
            if isinstance(valor, str) and "\n" in valor.strip():
                valor = " ".join(valor.split())
            linhas.append(f"{prefixo}{chave}: {json.dumps(valor, ensure_ascii=False)}")
        return "\n".join(linhas)


class LlmAssistant:
    def __init__(self, model: str = MODELO_PADRAO) -> None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "modo llm exige ANTHROPIC_API_KEY. O caminho padrão "
                "(make build) roda offline e sem chave."
            )
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "modo llm exige o pacote 'anthropic': pip install anthropic"
            ) from exc
        self.model = model
        self._client = Anthropic()

    def _perguntar(self, sistema: str, conteudo: dict) -> dict:
        resposta = self._client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=sistema,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(conteudo, ensure_ascii=False, indent=1),
                }
            ],
        )
        bruto = "".join(b.text for b in resposta.content if b.type == "text").strip()
        return _extrair_json(bruto)

    def melhorar_descricoes(self, contrato: Contract) -> dict[str, str]:
        """Devolve o mapa coluna -> descrição proposta. Não altera nada."""
        dados = self._perguntar(
            _SISTEMA_DESCRICAO,
            {
                "dataset": contrato.dataset,
                "contexto": contrato.description,
                "colunas": {c.name: c.description for c in contrato.columns},
            },
        )
        propostas = dados.get("colunas", {})
        atuais = {c.name: c.description for c in contrato.columns}
        # só devolve o que realmente mudou
        return {
            nome: texto
            for nome, texto in propostas.items()
            if nome in atuais and " ".join(texto.split()) != " ".join(atuais[nome].split())
        }

    def sugerir_invariantes(
        self, contrato: Contract, perfil: dict[str, Any]
    ) -> list[Proposta]:
        dados = self._perguntar(
            _SISTEMA_INVARIANTE,
            {
                "dataset": contrato.dataset,
                "colunas": [
                    {"name": c.name, "type": c.type, "description": c.description}
                    for c in contrato.columns
                ],
                "invariantes_ja_declaradas": [
                    {"type": i.type, "column": i.column, "name": i.name}
                    for i in contrato.invariants
                ],
                "perfil_dos_dados": perfil,
            },
        )
        saida: list[Proposta] = []
        for s in dados.get("sugestoes", []):
            tipo = s.get("type")
            if tipo not in {"range", "expression", "relationship"}:
                continue  # Princípio III: o modelo não propõe chave nem domínio
            conteudo = {
                k: s.get(k)
                for k in ("type", "column", "min", "max", "expression",
                          "references", "references_column", "name",
                          "business_rule")
            }
            saida.append(
                Proposta(
                    tipo=tipo,
                    conteudo=conteudo,
                    confianca=float(s.get("confianca", 0.0)),
                    justificativa=s.get("por_que", ""),
                )
            )
        return sorted(saida, key=lambda p: -p.confianca)


def perfilar(con, dataset: str, contrato: Contract) -> dict[str, Any]:
    """Perfil estatístico que alimenta a sugestão. Roda offline."""
    perfil: dict[str, Any] = {
        "linhas": con.execute(f"SELECT COUNT(*) FROM {dataset}").fetchone()[0]
    }
    for coluna in contrato.columns:
        if coluna.type in {"integer", "decimal"}:
            row = con.execute(
                f"SELECT MIN({coluna.name}), MAX({coluna.name}), "
                f"AVG({coluna.name}) FROM {dataset}"
            ).fetchone()
            perfil[coluna.name] = {
                "min": _num(row[0]), "max": _num(row[1]), "media": _num(row[2])
            }
        else:
            distintos = con.execute(
                f"SELECT COUNT(DISTINCT {coluna.name}) FROM {dataset}"
            ).fetchone()[0]
            perfil[coluna.name] = {"distintos": distintos}
    return perfil


def _num(v: Any) -> float | None:
    return None if v is None else round(float(v), 4)


def _extrair_json(texto: str) -> dict:
    if texto.startswith("```"):
        texto = texto.split("```")[1].removeprefix("json").strip()
    i, j = texto.find("{"), texto.rfind("}")
    if i == -1 or j == -1:
        return {}
    try:
        return json.loads(texto[i : j + 1])
    except json.JSONDecodeError:
        return {}
