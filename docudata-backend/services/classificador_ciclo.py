"""Ciclo de vida do nível da task (spec A2 §5): classificação na criação,
provisória, trava do nível, reclassificação e revisão."""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from graphs.classificacao_graph import classificar
from services.classificador_busca import salvar_embedding
from services.classificador_regua import (
    NIVEL_PROVISORIO_PADRAO,
    TIMEOUT_CLASSIFICACAO_S,
    VERSAO_REGUA,
    texto_da_task,
)
from services.gemini_key import get_gemini_api_key
from services.supabase_client import get_client

_LOG = logging.getLogger("docudata.classificador")

MODELO_CLASSIFICADOR = "gemini-3.5-flash-lite"
MOTIVO_TEXTO_EDITADO = "texto editado após a classificação"
MOTIVO_TEXTO_INSUFICIENTE = "texto insuficiente para classificar"
_COLUNAS_EM_TRABALHO = ("em_andamento", "pendente_aprovacao", "concluida")
_COLUNAS_CLASSIFICACAO = (
    "sinais", "nivel_sinais", "parecidas", "nivel_parecidas", "nivel_geral",
    "justificativa_geral", "opiniao_gerente", "nivel_combinado", "nivel_final",
    "motivo_revisao", "parametros",
)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resultado_provisorio(opiniao_gerente: int | None) -> dict:
    r = {c: None for c in _COLUNAS_CLASSIFICACAO}
    r.update({
        "status": "provisoria", "faltando": [], "ajuste_tempo": 0, "vetor": None,
        "opiniao_gerente": opiniao_gerente,
        "nivel_final": opiniao_gerente or NIVEL_PROVISORIO_PADRAO,
    })
    return r


async def _rodar_classificador(client, *, titulo, descricao, checklist, opiniao_gerente, gerente_id) -> dict:
    """Roda o agente com timeout. Propaga qualquer falha (chave, modelo, embedding)."""
    api_key = get_gemini_api_key()
    resultado = await asyncio.wait_for(
        classificar(
            titulo=titulo, descricao=descricao, checklist=checklist,
            opiniao_gerente=opiniao_gerente, gerente_id=gerente_id,
            api_key=api_key, client=client,
        ),
        TIMEOUT_CLASSIFICACAO_S,
    )
    resultado["opiniao_gerente"] = opiniao_gerente
    return resultado


def _levantar_se_faltando(resultado: dict) -> None:
    if resultado.get("status") == "faltando":
        raise HTTPException(status_code=422, detail={"faltando": list(resultado.get("faltando") or [])})


async def classificar_para_criacao(client, *, titulo, descricao, checklist, opiniao_gerente, gerente_id) -> dict:
    try:
        resultado = await _rodar_classificador(
            client, titulo=titulo, descricao=descricao, checklist=checklist,
            opiniao_gerente=opiniao_gerente, gerente_id=gerente_id,
        )
    except Exception as exc:
        _LOG.warning("classificador_indisponivel exc=%s", type(exc).__name__)
        return _resultado_provisorio(opiniao_gerente)
    _levantar_se_faltando(resultado)
    return resultado


def gravar_classificacao(client, task_id: str, resultado: dict, *, tipo: str, criado_por: str | None, texto: str) -> dict:
    linha = {
        "task_id": task_id,
        "tipo": tipo,
        "criado_por": criado_por,
        "criado_em": _agora(),
        "versao_regua": VERSAO_REGUA,
        "modelo": None if resultado["status"] == "provisoria" else MODELO_CLASSIFICADOR,
        "ajuste_tempo": resultado.get("ajuste_tempo") or 0,
        "status": resultado["status"],
    }
    for c in _COLUNAS_CLASSIFICACAO:
        linha[c] = resultado.get(c)
    if resultado["status"] == "resolvida":
        linha["resolvido_por"] = criado_por
        linha["resolvido_em"] = linha["criado_em"]
    inserida = client.table("task_classificacoes").insert(linha).execute().data[0]
    if resultado.get("vetor"):
        try:
            salvar_embedding(client, task_id, texto, resultado["vetor"])
        except Exception as exc:
            _LOG.warning("embedding_nao_salvo exc=%s", type(exc).__name__)
    client.table("tasks").update({"pontos": resultado["nivel_final"]}).eq("id", task_id).execute()
    return inserida


def classificacao_atual(client, task_id: str) -> dict | None:
    rows = (
        client.table("task_classificacoes").select("*").eq("task_id", task_id)
        .order("criado_em", desc=True).limit(1).execute().data
    )
    return rows[0] if rows else None


def travar_nivel(client, task_ids: list[str]) -> None:
    """Fixa o nível quando o trabalho começa. Provisória e em revisão ficam
    destravadas até alguém resolver; task legada (sem classificação) trava."""
    for task_id in task_ids:
        rows = client.table("tasks").select("id, nivel_travado_em").eq("id", task_id).execute().data
        if not rows or rows[0].get("nivel_travado_em"):
            continue
        atual = classificacao_atual(client, task_id)
        if atual is None or atual["status"] in ("aplicada", "resolvida"):
            client.table("tasks").update({"nivel_travado_em": _agora()}).eq("id", task_id).execute()


def _travar_se_em_trabalho(client, task: dict) -> None:
    if task.get("coluna_kanban") in _COLUNAS_EM_TRABALHO:
        travar_nivel(client, [task["id"]])


class ReclassificacaoObsoleta(Exception):
    """A task mudou (trava ou outra classificação) enquanto o modelo respondia."""


async def _reclassificar_task(client, task: dict, pessoa_id: str | None) -> dict:
    """Roda e grava uma reclassificação. Propaga exceções do classificador.

    O modelo demora até TIMEOUT_CLASSIFICACAO_S; ao voltar, a task é relida e
    nada é gravado se ela foi travada ou se a classificação atual já não é a
    que existia antes (compare-and-set). A trava usa a coluna fresca."""
    atual = classificacao_atual(client, task["id"])
    id_antes = atual["id"] if atual else None
    opiniao = atual.get("opiniao_gerente") if atual else None
    resultado = await _rodar_classificador(
        client, titulo=task["titulo"], descricao=task.get("descricao"),
        checklist=task.get("checklist") or [], opiniao_gerente=opiniao, gerente_id=pessoa_id,
    )
    _levantar_se_faltando(resultado)
    rows = client.table("tasks").select("*").eq("id", task["id"]).execute().data
    if not rows or rows[0].get("nivel_travado_em"):
        raise ReclassificacaoObsoleta()
    depois = classificacao_atual(client, task["id"])
    if (depois["id"] if depois else None) != id_antes:
        raise ReclassificacaoObsoleta()
    fresca = rows[0]
    texto = texto_da_task(fresca["titulo"], fresca.get("descricao"), fresca.get("checklist"))
    gravar_classificacao(client, task["id"], resultado, tipo="reclassificacao", criado_por=pessoa_id, texto=texto)
    _travar_se_em_trabalho(client, fresca)
    return resultado


async def reclassificar(client, task_id: str, pessoa_id: str) -> dict:
    rows = client.table("tasks").select("*").eq("id", task_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    if task.get("nivel_travado_em"):
        raise HTTPException(status_code=409, detail="O nível desta task já está travado.")
    try:
        resultado = await _reclassificar_task(client, task, pessoa_id)
    except HTTPException:
        raise
    except ReclassificacaoObsoleta:
        raise HTTPException(status_code=409, detail="A task mudou durante a classificação. Tente de novo.")
    except Exception as exc:
        _LOG.warning("reclassificacao_falhou exc=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Classificador indisponível. Tente novamente em instantes.")
    return resultado


def resolver_revisao(client, task_id: str, nivel: int, motivo: str, pessoa_id: str) -> dict:
    rows = client.table("tasks").select("*").eq("id", task_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    atual = classificacao_atual(client, task_id)
    if not atual or atual["status"] not in ("em_revisao", "provisoria"):
        raise HTTPException(status_code=409, detail="Esta task não está aguardando revisão de nível.")
    resultado = {
        "status": "resolvida", "ajuste_tempo": 0, "vetor": None,
        "nivel_final": nivel, "motivo_revisao": motivo,
        **{c: atual.get(c) for c in ("sinais", "nivel_sinais", "parecidas", "nivel_parecidas",
                                     "nivel_geral", "justificativa_geral", "opiniao_gerente",
                                     "nivel_combinado", "parametros")},
    }
    gravar_classificacao(client, task_id, resultado, tipo="reclassificacao", criado_por=pessoa_id, texto="")
    _travar_se_em_trabalho(client, task)
    return resultado


async def reclassificar_provisorias() -> None:
    """Job de 10 min: tenta de novo as tasks cuja classificação atual é provisória."""
    try:
        client = get_client()
        candidatas = client.table("task_classificacoes").select("task_id").eq("status", "provisoria").execute().data or []
        for task_id in sorted({c["task_id"] for c in candidatas}):
            atual = classificacao_atual(client, task_id)
            if not atual or atual["status"] != "provisoria":
                continue
            rows = client.table("tasks").select("*").eq("id", task_id).execute().data
            if not rows or rows[0].get("nivel_travado_em"):
                continue
            try:
                await _reclassificar_task(client, rows[0], atual.get("criado_por"))
            except ReclassificacaoObsoleta:
                continue
            except HTTPException as exc:
                if exc.status_code == 422:  # texto insuficiente: vai para a revisão do líder
                    client.table("task_classificacoes").update(
                        {"status": "em_revisao", "motivo_revisao": MOTIVO_TEXTO_INSUFICIENTE}
                    ).eq("id", atual["id"]).execute()
            except Exception as exc:
                _LOG.warning("reclassificar_provisoria_falhou exc=%s", type(exc).__name__)
    except Exception as exc:
        _LOG.warning("job_reclassificar_provisorias_falhou exc=%s", type(exc).__name__)
