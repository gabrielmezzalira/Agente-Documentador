"""Acesso ao Supabase para o domínio Discovery (Spec 12). Só consultas; nenhuma regra de negócio.

Projeção mínima de colunas (AGENTS.md §6.1): a transcrição vive em tabela própria e só sai
por `buscar_transcricao`, nunca junto da reunião nem de listagens.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

_COLS_REUNIAO = (
    "id, project_id, tipo, origem, fonte_session_id, ocorrida_em, conteudo_estruturado, "
    "analise_status, analise_erro, analise_iniciada_em, created_at"
)
_COLS_REQUISITO = (
    "id, project_id, codigo, titulo, descricao, tipo, lente, criterios_aceite, prioridade_sugerida, "
    "justificativa, status, motivo_decisao, possivel_duplicata_de, conflito, revisado_por, "
    "validado_por, funcionalidade_id, created_at, updated_at"
)
_COLS_EVIDENCIA = "id, requisito_id, reuniao_id, trecho, speaker, confianca, created_at"
_COLS_TRANSICAO = "id, requisito_id, campo, de, para, autor, motivo, timestamp"


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _um(resposta) -> dict | None:
    return resposta.data[0] if resposta.data else None


def buscar_projeto(client: Any, project_id: str) -> dict | None:
    return _um(client.table("projects").select("id, subarea").eq("id", project_id).execute())


# ---- reuniões ----
def buscar_reuniao_por_fonte(client: Any, fonte_session_id: str) -> dict | None:
    return _um(
        client.table("discovery_reunioes")
        .select("id, project_id, analise_status")
        .eq("fonte_session_id", fonte_session_id)
        .execute()
    )


def inserir_reuniao(
    client: Any, *, project_id: str, tipo: str, ocorrida_em: str | None,
    fonte_session_id: str | None, conteudo_estruturado: dict, origem: str = "agente_diagnostico",
) -> dict:
    resposta = client.table("discovery_reunioes").insert({
        "project_id": project_id, "tipo": tipo, "origem": origem,
        "fonte_session_id": fonte_session_id, "ocorrida_em": ocorrida_em,
        "conteudo_estruturado": conteudo_estruturado, "analise_status": "pendente",
    }).execute()
    return resposta.data[0]


def buscar_reuniao(client: Any, reuniao_id: str) -> dict | None:
    return _um(client.table("discovery_reunioes").select(_COLS_REUNIAO).eq("id", reuniao_id).execute())


def listar_reunioes(client: Any, project_id: str) -> list[dict]:
    return (
        client.table("discovery_reunioes").select(_COLS_REUNIAO)
        .eq("project_id", project_id).order("ocorrida_em", desc=False).execute().data or []
    )


def marcar_analise(client: Any, reuniao_id: str, status: str, erro: str | None = None) -> None:
    campos = {"analise_status": status, "analise_erro": erro}
    if status == "pendente":
        campos["analise_iniciada_em"] = None  # pendente = sem reserva: pronta para uma nova reserva
    client.table("discovery_reunioes").update(campos).eq("id", reuniao_id).execute()


def _reserva_ativa(reuniao: dict, agora: datetime, ttl_segundos: int) -> bool:
    valor = reuniao.get("analise_iniciada_em")
    if not valor:
        return False
    try:
        inicio = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return False  # valor ilegível não prende a análise para sempre
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    return agora - inicio < timedelta(seconds=ttl_segundos)


def reservar_analise(client: Any, reuniao_id: str, *, agora: datetime, ttl_segundos: int = 900) -> bool:
    """Reserva a análise por compare-and-swap: só quem atualizar a linha ganha.

    Reserva se a reunião está `pendente` e sem reserva ativa (nula ou mais velha que o TTL).
    """
    reuniao = buscar_reuniao(client, reuniao_id)
    if reuniao is None or reuniao.get("analise_status") != "pendente" or _reserva_ativa(reuniao, agora, ttl_segundos):
        return False
    consulta = client.table("discovery_reunioes").update({"analise_iniciada_em": agora.isoformat()}).eq("id", reuniao_id).eq("analise_status", "pendente")
    anterior = reuniao.get("analise_iniciada_em")
    consulta = consulta.is_("analise_iniciada_em", "null") if anterior is None else consulta.eq("analise_iniciada_em", anterior)
    return bool(consulta.execute().data)


def reiniciar_analise(client: Any, reuniao_id: str, *, agora: datetime, ttl_segundos: int = 900) -> bool:
    """Ação explícita (reanalisar/reconsolidar): volta a reunião para `pendente` sem reserva.

    Não derruba uma análise realmente em andamento (pendente com reserva ativa): devolve False.
    """
    reuniao = buscar_reuniao(client, reuniao_id)
    if reuniao is None or (reuniao.get("analise_status") == "pendente" and _reserva_ativa(reuniao, agora, ttl_segundos)):
        return False
    marcar_analise(client, reuniao_id, "pendente", None)
    return True


# ---- transcrição ----
def inserir_transcricao(client: Any, *, reuniao_id: str, conteudo: str, redigida: bool) -> None:
    client.table("discovery_transcricoes").insert({
        "reuniao_id": reuniao_id, "conteudo": conteudo,
        "tamanho": len(conteudo.encode("utf-8")), "redigida": redigida,
    }).execute()


def buscar_transcricao(client: Any, reuniao_id: str) -> dict | None:
    return _um(
        client.table("discovery_transcricoes")
        .select("conteudo, redigida, expira_em").eq("reuniao_id", reuniao_id).execute()
    )


def existe_transcricao(client: Any, reuniao_id: str) -> bool:
    """Só checa a existência (não traz o conteúdo, que pode ter até 2 MB)."""
    return _um(
        client.table("discovery_transcricoes").select("reuniao_id").eq("reuniao_id", reuniao_id).execute()
    ) is not None


# ---- requisitos ----
def listar_requisitos(client: Any, project_id: str, status: str | None = None) -> list[dict]:
    consulta = client.table("requisitos").select(_COLS_REQUISITO).eq("project_id", project_id)
    if status is not None:
        consulta = consulta.eq("status", status)
    return consulta.order("codigo", desc=False).execute().data or []


def buscar_requisito(client: Any, requisito_id: str) -> dict | None:
    return _um(client.table("requisitos").select(_COLS_REQUISITO).eq("id", requisito_id).execute())


def inserir_requisito(client: Any, dados: dict) -> dict:
    return client.table("requisitos").insert(dados).execute().data[0]


def atualizar_requisito(client: Any, requisito_id: str, campos: dict) -> dict:
    resposta = client.table("requisitos").update({**campos, "updated_at": _agora()}).eq("id", requisito_id).execute()
    return resposta.data[0]


def atualizar_requisito_se_editavel(client: Any, requisito_id: str, campos: dict) -> dict | None:
    """Update condicional ao status NO MOMENTO da escrita (proposto/em_revisao); None se não casou."""
    resposta = (
        client.table("requisitos").update({**campos, "updated_at": _agora()})
        .eq("id", requisito_id).in_("status", ["proposto", "em_revisao"]).execute()
    )
    return resposta.data[0] if resposta.data else None


# ---- evidências e transições ----
def inserir_evidencia(
    client: Any, *, requisito_id: str, reuniao_id: str, trecho: str,
    speaker: str | None, confianca: float | None,
) -> bool:
    ja_existe = (
        client.table("requisito_evidencias").select("id")
        .eq("requisito_id", requisito_id).eq("reuniao_id", reuniao_id).eq("trecho", trecho).execute()
    )
    if ja_existe.data:
        return False
    client.table("requisito_evidencias").insert({
        "requisito_id": requisito_id, "reuniao_id": reuniao_id, "trecho": trecho,
        "speaker": speaker, "confianca": confianca,
    }).execute()
    return True


def listar_evidencias(client: Any, requisito_id: str) -> list[dict]:
    return (
        client.table("requisito_evidencias").select(_COLS_EVIDENCIA)
        .eq("requisito_id", requisito_id).order("created_at", desc=False).execute().data or []
    )


def contar_evidencias(client: Any, requisito_ids: list[str]) -> dict[str, int]:
    contagem = {rid: 0 for rid in requisito_ids}
    if not requisito_ids:
        return contagem
    linhas = client.table("requisito_evidencias").select("requisito_id").in_("requisito_id", requisito_ids).execute().data or []
    for linha in linhas:
        contagem[linha["requisito_id"]] = contagem.get(linha["requisito_id"], 0) + 1
    return contagem


def inserir_transicao(
    client: Any, *, requisito_id: str, campo: str, de: str, para: str,
    autor: str | None, motivo: str | None,
) -> None:
    client.table("requisito_transicoes").insert({
        "requisito_id": requisito_id, "campo": campo, "de": de, "para": para,
        "autor": autor, "motivo": motivo, "timestamp": _agora(),
    }).execute()


def listar_transicoes(client: Any, requisito_id: str) -> list[dict]:
    return (
        client.table("requisito_transicoes").select(_COLS_TRANSICAO)
        .eq("requisito_id", requisito_id).order("timestamp", desc=False).execute().data or []
    )
