"""Orquestra a análise de uma reunião de Discovery (Spec 12 §3): carrega o contexto, roda o grafo
e aplica o resultado. Regra de ouro: requisito `validado`/`rejeitado` NUNCA tem status, prioridade
ou conteúdo alterados aqui — só recebe evidência e, havendo tensão, a marca `conflito`.
Dúvida de duplicata vira `em_revisao`. A saída do modelo é tratada como não confiável.
"""
import json
import logging
from typing import Any, Awaitable, Callable

from graphs.requisitos_graph import (
    CRITERIOS_MAX, FONTE_MAX_CHARS, SPEAKER_MAX_CHARS, TEXTO_MAX_CHARS, TITULO_MAX_CHARS,
    executar_analise,
)
from models.discovery import SaidaAnalise
from services import discovery_store as store
from services.discovery_redacao import limitar_trecho
from services.discovery_saneamento import candidatos_duplicata, confianca_segura, speaker_limitado
from services.discovery_requisitos import achar_duplicata, normalizar_titulo, proximo_codigo
from services.gemini_key import get_gemini_api_key
from services.supabase_client import get_client

_LOG = logging.getLogger("docudata.discovery")
_ERRO_GENERICO = "Falha na análise da reunião"
_AUTOR = "agente"
_EDITAVEIS_PELO_AGENTE = ("proposto", "em_revisao")
MAX_TENTATIVAS_CODIGO = 3
_MARCAS_UNICIDADE = ("23505", "duplicate key", "unique")
_ZERO = {"novos": 0, "reforcos": 0, "conflitos": 0, "ajustes": 0, "duplicatas": 0}


def fonte_da_reuniao(reuniao: dict, transcricao: str | None) -> str:
    """Texto sobre o qual o modelo trabalha e contra o qual as evidências são conferidas."""
    estruturado = json.dumps(reuniao.get("conteudo_estruturado") or {}, ensure_ascii=False)
    base = f"{transcricao}\n\n{estruturado}" if transcricao else estruturado
    return base[:FONTE_MAX_CHARS]


def _compactar(requisitos: list[dict], contagem: dict[str, int]) -> list[dict]:
    return [
        {
            "codigo": r["codigo"], "titulo": r["titulo"],
            "descricao_curta": (r.get("descricao") or "")[:160],
            "status": r["status"], "prioridade": r["prioridade_sugerida"],
            "n_evidencias": contagem.get(r["id"], 0),
        }
        for r in requisitos
    ]


def _violou_unicidade(exc: Exception) -> bool:
    texto = f"{getattr(exc, 'code', '')} {exc}".lower()
    return any(marca in texto for marca in _MARCAS_UNICIDADE)


def _ja_registrado(client: Any, duplicata: dict, reuniao_id: str, trecho: str) -> bool | None:
    """True: esta reunião já deu esta evidência a esse requisito (reanálise, no-op).
    None: requisito órfão (sem nenhuma evidência) - deve ser reaproveitado. False: caso comum."""
    evidencias = store.listar_evidencias(client, duplicata["id"])
    if not evidencias:
        return None
    alvo = normalizar_titulo(trecho)
    return any(e["reuniao_id"] == reuniao_id and normalizar_titulo(e["trecho"]) == alvo for e in evidencias)


def _inserir_com_codigo(client: Any, dados: dict, conhecidos: list[dict]) -> dict:
    """Aloca RQ-nnn sobre os códigos conhecidos; em colisão (UNIQUE) recalcula a partir do banco."""
    codigos = [r["codigo"] for r in conhecidos]
    for tentativa in range(MAX_TENTATIVAS_CODIGO):
        try:
            return store.inserir_requisito(client, {**dados, "codigo": proximo_codigo(codigos)})
        except Exception as exc:
            _LOG.warning("inserir_requisito_falhou tentativa=%s exc=%s", tentativa + 1, type(exc).__name__)
            if tentativa == MAX_TENTATIVAS_CODIGO - 1 or not _violou_unicidade(exc):
                raise
            codigos = codigos + [r["codigo"] for r in store.listar_requisitos(client, dados["project_id"])]
    raise RuntimeError("inalcançável")  # pragma: no cover


def _aplicar_novos(client: Any, reuniao: dict, saida: SaidaAnalise, conhecidos: list[dict],
                   por_codigo: dict[str, dict], contagens: dict[str, int]) -> None:
    for novo in saida.novos:
        titulo = novo.titulo.strip()[:TITULO_MAX_CHARS]
        trecho = limitar_trecho(novo.trecho.strip())
        if not titulo or not trecho:
            continue
        duplicata = achar_duplicata(titulo, candidatos_duplicata(conhecidos))
        if duplicata:
            registrado = _ja_registrado(client, duplicata, reuniao["id"], trecho)
            if registrado:
                continue  # reanálise: mesmo novo da mesma reunião já aplicado
            if registrado is None:  # órfão de execução interrompida: completa em vez de criar outro
                store.inserir_evidencia(client, requisito_id=duplicata["id"], reuniao_id=reuniao["id"],
                                        trecho=trecho, speaker=speaker_limitado(novo.speaker), confianca=confianca_segura(novo.confianca))
                if not store.listar_transicoes(client, duplicata["id"]):
                    store.inserir_transicao(client, requisito_id=duplicata["id"], campo="status", de="",
                                            para="proposto", autor=_AUTOR, motivo=None)
                contagens["novos"] += 1
                continue
        status = "em_revisao" if duplicata else "proposto"
        criado = _inserir_com_codigo(client, {
            "project_id": reuniao["project_id"], "titulo": titulo,
            "descricao": novo.descricao[:TEXTO_MAX_CHARS] or None, "tipo": novo.tipo, "lente": novo.lente,
            "criterios_aceite": [c[:TEXTO_MAX_CHARS] for c in novo.criterios_aceite[:CRITERIOS_MAX]],
            "prioridade_sugerida": novo.prioridade_sugerida,
            "justificativa": novo.justificativa[:TEXTO_MAX_CHARS] or None, "status": status,
            "possivel_duplicata_de": duplicata["id"] if duplicata else None, "conflito": False,
        }, conhecidos)
        store.inserir_evidencia(client, requisito_id=criado["id"], reuniao_id=reuniao["id"],
                                trecho=trecho, speaker=speaker_limitado(novo.speaker),
                                confianca=confianca_segura(novo.confianca))
        store.inserir_transicao(client, requisito_id=criado["id"], campo="status", de="", para=status,
                                autor=_AUTOR, motivo="possível duplicata" if duplicata else None)
        conhecidos.append(criado)
        por_codigo[criado["codigo"]] = criado
        contagens["novos"] += 1
        contagens["duplicatas"] += 1 if duplicata else 0


def _aplicar(client: Any, reuniao: dict, saida: SaidaAnalise, requisitos: list[dict]) -> dict[str, int]:
    contagens = dict(_ZERO)
    por_codigo = {r["codigo"]: r for r in requisitos}
    conhecidos = list(requisitos)

    _aplicar_novos(client, reuniao, saida, conhecidos, por_codigo, contagens)

    vistos: set[tuple[str, str]] = set()
    for reforco in saida.reforcos:
        alvo = por_codigo.get(reforco.codigo)
        trecho = limitar_trecho(reforco.trecho.strip())
        if not alvo or not trecho or (reforco.codigo, trecho) in vistos:
            continue
        vistos.add((reforco.codigo, trecho))
        if store.inserir_evidencia(client, requisito_id=alvo["id"], reuniao_id=reuniao["id"], trecho=trecho,
                                   speaker=speaker_limitado(reforco.speaker), confianca=confianca_segura(reforco.confianca)):
            contagens["reforcos"] += 1

    for conflito in saida.conflitos:
        alvo = por_codigo.get(conflito.codigo)
        if alvo and not alvo.get("conflito"):
            store.atualizar_requisito(client, alvo["id"], {"conflito": True})
            store.inserir_transicao(client, requisito_id=alvo["id"], campo="conflito", de="false", para="true",
                                    autor=_AUTOR, motivo=limitar_trecho(conflito.descricao[:TEXTO_MAX_CHARS], 500))
            alvo["conflito"] = True
            contagens["conflitos"] += 1

    for ajuste in saida.ajustes_prioridade:
        alvo = por_codigo.get(ajuste.codigo)
        if not alvo or alvo["status"] not in _EDITAVEIS_PELO_AGENTE:
            continue  # validado/rejeitado: decisão humana, nunca mexe sozinho
        if alvo["prioridade_sugerida"] != ajuste.prioridade:
            atualizado = store.atualizar_requisito_se_editavel(client, alvo["id"], {
                "prioridade_sugerida": ajuste.prioridade,
                "justificativa": ajuste.justificativa[:TEXTO_MAX_CHARS] or alvo.get("justificativa"),
            })
            if atualizado is None:
                continue  # validado/rejeitado entre a leitura e a escrita: decisão humana vence
            store.inserir_transicao(client, requisito_id=alvo["id"], campo="prioridade_sugerida",
                                    de=alvo["prioridade_sugerida"], para=ajuste.prioridade,
                                    autor=_AUTOR, motivo=limitar_trecho(ajuste.justificativa, 500) or None)
            alvo["prioridade_sugerida"] = ajuste.prioridade
            contagens["ajustes"] += 1
    return contagens


async def analisar_reuniao(
    client: Any, reuniao_id: str, *,
    executar: Callable[..., Awaitable[SaidaAnalise]] = executar_analise,
    obter_chave: Callable[[], str] = get_gemini_api_key,
) -> dict[str, int]:
    reuniao = store.buscar_reuniao(client, reuniao_id)
    if reuniao is None:
        raise LookupError("Reunião não encontrada")
    try:
        requisitos = store.listar_requisitos(client, reuniao["project_id"])
        contagem = store.contar_evidencias(client, [r["id"] for r in requisitos])
        transcricao = (store.buscar_transcricao(client, reuniao_id) or {}).get("conteudo")
        saida = await executar(
            tipo=reuniao["tipo"], conteudo=reuniao.get("conteudo_estruturado") or {},
            fonte=fonte_da_reuniao(reuniao, transcricao), existentes=_compactar(requisitos, contagem),
            api_key=obter_chave(),
        )
        contagens = _aplicar(client, reuniao, saida, requisitos)
    except Exception as exc:  # AnaliseFalhouErro e qualquer imprevisto: status falhou, sem detalhe
        _LOG.warning("analise_reuniao_falhou reuniao=%s exc=%s", reuniao_id, type(exc).__name__)
        store.marcar_analise(client, reuniao_id, "falhou", _ERRO_GENERICO)
        return dict(_ZERO)
    store.marcar_analise(client, reuniao_id, "ok", None)
    return contagens


async def analisar_em_segundo_plano(reuniao_id: str) -> None:
    """Entrada das BackgroundTasks: nunca levanta (o status da reunião já registra a falha)."""
    try:
        await analisar_reuniao(get_client(), reuniao_id)
    except Exception as exc:
        _LOG.warning("analise_segundo_plano_falhou reuniao=%s exc=%s", reuniao_id, type(exc).__name__)


async def reconsolidar_projeto(
    client: Any, project_id: str, *,
    executar: Callable[..., Awaitable[SaidaAnalise]] = executar_analise,
    obter_chave: Callable[[], str] = get_gemini_api_key,
) -> int:
    """Reanalisa as reuniões em ordem cronológica. As travas (evidência única, duplicata em
    `em_revisao`, validado/rejeitado intocáveis) fazem disso uma PROPOSTA, nunca uma sobrescrita."""
    reunioes = sorted(
        store.listar_reunioes(client, project_id),
        key=lambda r: (str(r.get("ocorrida_em") or ""), str(r.get("created_at") or "")),
    )
    analisadas = 0
    for reuniao in reunioes:
        try:
            await analisar_reuniao(client, reuniao["id"], executar=executar, obter_chave=obter_chave)
            if (store.buscar_reuniao(client, reuniao["id"]) or {}).get("analise_status") == "ok":
                analisadas += 1
        except Exception as exc:  # uma reunião ruim não aborta as seguintes
            _LOG.warning("reconsolidar_reuniao_falhou reuniao=%s exc=%s", reuniao["id"], type(exc).__name__)
    return analisadas


async def reconsolidar_em_segundo_plano(project_id: str) -> None:
    try:
        await reconsolidar_projeto(get_client(), project_id)
    except Exception as exc:
        _LOG.warning("reconsolidar_falhou projeto=%s exc=%s", project_id, type(exc).__name__)
