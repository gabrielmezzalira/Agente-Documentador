"""Extração e persistência de commits compartilhada pelo App e hook legado."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from models.schemas import AvaliacaoQualidadeCommit, ConteudoEstruturado
from services.gemini_key import get_gemini_api_key
from services.sprints import ensure_sprint_row, get_current_sprint_number

_LOG = logging.getLogger("docudata.commit_extraction")


_COST_PER_INPUT_TOKEN = 0.30 / 1_000_000
_COST_PER_OUTPUT_TOKEN = 2.50 / 1_000_000
_SPRINT_RE = re.compile(r"\[sprint:(\d+)\]", re.IGNORECASE)
_TASK_TAG_RE = re.compile(r"\[task:([0-9a-fA-F-]{36})\]")

_COMMIT_SYSTEM_PROMPT = (
    "Você é um assistente especializado em extrair conhecimento estruturado de commits de código "
    "de projetos do CITi. Extraia resumo, tarefas implementadas, decisões técnicas, problemas ou "
    "bugs corrigidos, contexto do cliente explicitamente mencionado, próximos passos e tecnologias. "
    "Não infira informações ausentes. Em tecnologias_removidas, inclua somente remoções completas "
    "explicitamente demonstradas pelo diff; caso contrário, use uma lista vazia."
)

_COMMIT_QUALIDADE_PROMPT = (
    "Você avalia a qualidade técnica de uma entrega de código a partir do commit e do diff "
    "fornecidos. Pontue de 0 a 10 considerando complexidade, documentação, mensagem de commit "
    "e boas práticas. Retorne somente a nota e uma evidência curta, sem criar pendências."
)


@dataclass(frozen=True)
class DadosCommit:
    projeto_id: str
    sha: str
    mensagem: str
    autor: str
    data: str
    autor_email: str | None = None
    sprint_numero: int | None = None
    branch: str | None = None
    diff_stat: str | None = None
    diff: str | None = None
    repositorio_id: str | None = None
    repositorio_nome: str | None = None
    url: str | None = None
    autor_login: str | None = None
    committer: str | None = None
    committer_login: str | None = None
    pusher: str | None = None
    sender: str | None = None


def resolver_sprint_commit(client: Any, dados: DadosCommit) -> int:
    match = _SPRINT_RE.search(dados.mensagem)
    if match:
        return max(int(match.group(1)), 1)
    if dados.sprint_numero is not None:
        return max(dados.sprint_numero, 1)
    return get_current_sprint_number(client, dados.projeto_id)


def commit_ja_ingerido(client: Any, repositorio_id: str | None, sha: str) -> bool:
    if not repositorio_id:
        return False
    resposta = (
        client.table("ingestions")
        .select("id")
        .eq("source_repository_id", repositorio_id)
        .eq("source_commit_sha", sha)
        .limit(1)
        .execute()
    )
    return bool(resposta.data)


async def extrair_e_salvar_commit(client: Any, dados: DadosCommit) -> dict[str, Any]:
    if commit_ja_ingerido(client, dados.repositorio_id, dados.sha):
        return {"status": "duplicado", "ingestion_id": None, "sprint_number": None}

    projeto = client.table("projects").select("id, arquetipo").eq("id", dados.projeto_id).execute()
    if not projeto.data:
        raise HTTPException(status_code=404, detail="Project not found")

    sprint_numero = resolver_sprint_commit(client, dados)
    api_key = get_gemini_api_key()
    ensure_sprint_row(client, dados.projeto_id, sprint_numero)

    prompt = (
        f"Commit: {dados.sha[:120]}\nMensagem: {dados.mensagem[:2000]}\n"
        f"Autor: {dados.autor[:300]}\nData: {dados.data[:100]}\n"
        f"Repositório: {(dados.repositorio_nome or 'não informado')[:300]}\n"
        f"Branch: {(dados.branch or 'não informada')[:300]}\n"
        f"\nEstatísticas do diff:\n{(dados.diff_stat or 'não informadas')[:2000]}\n"
        f"\nDiff das mudanças:\n{(dados.diff or 'não informado')[:8000]}"
    )
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite", max_tokens=2048, google_api_key=api_key
    )
    structured_llm = llm.with_structured_output(
        ConteudoEstruturado, method="json_schema", include_raw=True
    )
    try:
        resultado = await structured_llm.ainvoke([
            SystemMessage(content=_COMMIT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        parsed: ConteudoEstruturado = resultado["parsed"]
        raw_msg = resultado["raw"]
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Falha ao processar o commit com Gemini") from exc

    uso = getattr(raw_msg, "usage_metadata", None) or {}
    tokens_entrada = uso.get("input_tokens", 0) or 0
    tokens_saida = uso.get("output_tokens", 0) or 0
    custo = tokens_entrada * _COST_PER_INPUT_TOKEN + tokens_saida * _COST_PER_OUTPUT_TOKEN

    conteudo = parsed.model_dump()
    conteudo.update({
        "_meta_autor": dados.autor,
        "_meta_data_commit": dados.data,
        "_meta_commit_msg": dados.mensagem,
    })
    metadados_opcionais = {
        "_meta_repository": dados.repositorio_nome,
        "_meta_branch": dados.branch,
        "_meta_commit_sha": dados.sha,
        "_meta_commit_url": dados.url,
        "_meta_autor_login": dados.autor_login,
        "_meta_autor_email": dados.autor_email,
        "_meta_committer": dados.committer,
        "_meta_committer_login": dados.committer_login,
        "_meta_pusher": dados.pusher,
        "_meta_sender": dados.sender,
    }
    conteudo.update({chave: valor for chave, valor in metadados_opcionais.items() if valor})

    registro = {
        "project_id": dados.projeto_id,
        "sprint_number": sprint_numero,
        "file_name": f"commit:{dados.sha[:7]}",
        "file_type": "commit",
        "tipo_documentacao": "commit",
        "extracted_content": conteudo,
        "input_tokens": tokens_entrada,
        "output_tokens": tokens_saida,
        "cost_usd": round(custo, 8),
    }
    origem = {
        "source_repository_id": dados.repositorio_id,
        "source_repository_full_name": dados.repositorio_nome,
        "source_commit_sha": dados.sha if dados.repositorio_id else None,
        "source_branch": dados.branch,
        "source_url": dados.url,
        "source_diff_stat": dados.diff_stat,
    }
    # O legado não toca nas colunas novas e continua funcionando antes da migration.
    if dados.repositorio_id:
        registro.update(origem)

    try:
        resposta = client.table("ingestions").insert(registro).execute()
        if not resposta.data:
            raise RuntimeError("Insert returned no data")
    except Exception as exc:
        # A constraint única cobre a corrida entre deliveries concorrentes.
        if dados.repositorio_id and commit_ja_ingerido(client, dados.repositorio_id, dados.sha):
            return {"status": "duplicado", "ingestion_id": None, "sprint_number": sprint_numero}
        raise HTTPException(status_code=500, detail="Supabase insert failed") from exc

    if (projeto.data[0].get("arquetipo") or "padrao") == "padrao":
        try:
            operacional_id = None
            filtros_identidade = [
                ("github_login", dados.autor_login),
                ("github_email", dados.autor_email),
                ("email", dados.autor_email),
            ]
            for coluna, valor in filtros_identidade:
                if not valor:
                    continue
                operacional = (
                    client.table("operacionais")
                    .select("id")
                    .eq("project_id", dados.projeto_id)
                    .eq(coluna, valor)
                    .execute()
                )
                if operacional.data:
                    operacional_id = operacional.data[0]["id"]
                    break

            avaliador = ChatGoogleGenerativeAI(
                model="gemini-3.5-flash-lite", max_tokens=512, google_api_key=api_key
            ).with_structured_output(AvaliacaoQualidadeCommit)
            avaliacao: AvaliacaoQualidadeCommit = await avaliador.ainvoke([
                SystemMessage(content=_COMMIT_QUALIDADE_PROMPT),
                HumanMessage(content=prompt),
            ])
            task_match = _TASK_TAG_RE.search(dados.mensagem)
            client.table("commit_qualidade").insert({
                "commit_hash": dados.sha,
                "task_id": task_match.group(1) if task_match else None,
                "operacional_id": operacional_id,
                "projeto_id": dados.projeto_id,
                "nota": avaliacao.nota,
                "evidencia": avaliacao.evidencia,
            }).execute()
        except Exception as exc:
            # A qualidade é complementar; o contexto do commit já persistido não deve ser perdido.
            _LOG.warning("qualidade_commit_ignorada exc=%s", type(exc).__name__)

    return {
        "status": "ok",
        "ingestion_id": resposta.data[0].get("id"),
        "sprint_number": sprint_numero,
    }
