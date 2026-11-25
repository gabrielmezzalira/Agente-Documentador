import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel

from core.rate_limit import GEMINI_RATE_LIMIT, limiter

from models.schemas import (
    FuncionalidadeCreate,
    FuncionalidadeUpdate,
    FuncionalidadeResponse,
    TransicaoStatusResponse,
    ImportPropostaResponse,
    ImportConfirmarRequest,
    FuncionalidadeProposta,
    normalizar_sprint_alvo,
)
from services.aprovacao_funcionalidade import aprovar, com_tem_tasks, desfazer_aprovacao, nomes_dos_aprovadores, revogar_se_aprovada
from services.acesso import exigir_acesso, exigir_acesso_por
from services.auth import get_current_pessoa, require_not_operacional
from services.status_funcionalidade import registrar_transicao_status, status_derivado, tasks_da_funcionalidade
from services.supabase_client import get_client
from services.gemini_key import get_gemini_api_key


router = APIRouter(prefix="/funcionalidades", tags=["funcionalidades"])


class ImportarRequest(BaseModel):
    project_id: str
    texto_contrato: str


@router.post("/importar", response_model=ImportPropostaResponse)
@limiter.limit(GEMINI_RATE_LIMIT)
async def importar_funcionalidades(request: Request, response: Response, data: ImportarRequest, pessoa: dict = Depends(get_current_pessoa)):
    """Propõe funcionalidades a partir do texto do contrato via IA. Não salva nada."""
    from graphs.import_graph import import_graph

    texto = data.texto_contrato[:50000]
    if len(texto.strip()) < 20:
        raise HTTPException(status_code=422, detail="Texto do contrato muito curto para análise")

    client = get_client()
    exigir_acesso(client, pessoa, data.project_id)
    proj = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = get_gemini_api_key()

    state = await import_graph.ainvoke({
        "texto_contrato": texto,
        "projeto_id": data.project_id,
        "api_key": api_key,
        "proposta": None,
        "valido": False,
        "tentativas": 0,
        "erro": None,
    })

    if not state.get("valido") or not state.get("proposta"):
        raise HTTPException(
            status_code=502,
            detail="Não foi possível extrair funcionalidades do contrato",
        )

    propostas = []
    for item in state["proposta"]:
        try:
            propostas.append(FuncionalidadeProposta(**item))
        except Exception:
            pass

    if not propostas:
        raise HTTPException(status_code=502, detail="Gemini retornou lista sem itens válidos")

    return ImportPropostaResponse(propostas=propostas)


@router.post("/importar/arquivo", response_model=ImportPropostaResponse)
@limiter.limit(GEMINI_RATE_LIMIT)
async def importar_funcionalidades_arquivo(
    request: Request,
    response: Response,
    project_id: str = Form(...),
    arquivo: UploadFile = File(...),
    pessoa: dict = Depends(get_current_pessoa),
):
    """Propõe funcionalidades extraindo texto de PDF, DOCX ou TXT. Não salva nada."""
    from graphs.import_graph import import_graph
    from services.file_parser import ArquivoInvalido, parse_pdf, parse_docx, parse_txt
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage

    client = get_client()
    exigir_acesso(client, pessoa, project_id)
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")
    api_key = get_gemini_api_key()

    content_type = arquivo.content_type or ""
    file_bytes = await arquivo.read()

    texto: str = ""
    b64_image: str | None = None

    if content_type == "application/pdf" or arquivo.filename.endswith(".pdf"):
        result = parse_pdf(file_bytes)
        if result["is_scanned"]:
            b64_image = result["b64"]
        else:
            texto = result["text"]
    elif content_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",) or arquivo.filename.endswith(".docx"):
        try:
            texto = parse_docx(file_bytes)
        except ArquivoInvalido:
            raise HTTPException(status_code=422, detail="DOCX inválido ou corrompido")
    else:
        texto = parse_txt(file_bytes)

    # PDF escaneado: enviar imagem diretamente ao Gemini
    if b64_image:
        from graphs.import_graph import _IMPORT_SYSTEM_PROMPT, _HARDENED_SUFFIX
        import json

        proposta_raw = None
        for tentativa in range(2):
            suffix = _HARDENED_SUFFIX if tentativa > 0 else ""
            try:
                llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", max_tokens=4096, google_api_key=api_key)
                messages = [
                    SystemMessage(_IMPORT_SYSTEM_PROMPT),
                    HumanMessage(content=[
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                        {"type": "text", "text": f"Extraia as funcionalidades deste documento.{suffix}"},
                    ]),
                ]
                raw = (await llm.ainvoke(messages)).content
                if isinstance(raw, list):
                    raw = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in raw)
                parsed = json.loads(raw.strip())
                proposta_raw = parsed.get("funcionalidades", [])
                if proposta_raw:
                    break
            except Exception:
                continue

        if not proposta_raw:
            raise HTTPException(status_code=502, detail="Não foi possível extrair funcionalidades do PDF escaneado")

        propostas = []
        for item in proposta_raw:
            try:
                propostas.append(FuncionalidadeProposta(**item))
            except Exception:
                pass
        if not propostas:
            raise HTTPException(status_code=502, detail="Gemini retornou lista sem itens válidos")
        return ImportPropostaResponse(propostas=propostas)

    # PDF com texto ou DOCX/TXT
    if len(texto.strip()) < 20:
        raise HTTPException(status_code=422, detail="Não foi possível extrair texto do arquivo")

    state = await import_graph.ainvoke({
        "texto_contrato": texto[:50000],
        "projeto_id": project_id,
        "api_key": api_key,
        "proposta": None,
        "valido": False,
        "tentativas": 0,
        "erro": None,
    })

    if not state.get("valido") or not state.get("proposta"):
        raise HTTPException(
            status_code=502,
            detail="Não foi possível extrair funcionalidades do arquivo",
        )

    propostas = []
    for item in state["proposta"]:
        try:
            propostas.append(FuncionalidadeProposta(**item))
        except Exception:
            pass
    if not propostas:
        raise HTTPException(status_code=502, detail="Gemini retornou lista sem itens válidos")
    return ImportPropostaResponse(propostas=propostas)


@router.post("/importar/confirmar", response_model=list[FuncionalidadeResponse], status_code=201)
async def confirmar_importacao(data: ImportConfirmarRequest, pessoa: dict = Depends(get_current_pessoa)):
    """Cria as funcionalidades confirmadas e descarta as rejeitadas."""
    client = get_client()
    exigir_acesso(client, pessoa, data.project_id)
    proj_check = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not proj_check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    confirmadas = [item for item in data.itens if item.confirmed]
    if not confirmadas:
        return []
    sprints_alvo: list[str] = []
    for item in confirmadas:
        try:
            sprints_alvo.append(normalizar_sprint_alvo(item.sprint_alvo))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Informe a sprint alvo de \"{item.proposta.titulo}\".")

    criadas = []
    for item, sprint_alvo in zip(confirmadas, sprints_alvo):
        prop = item.proposta
        payload = {
            "project_id": data.project_id,
            "id_funcional": prop.id_funcional,
            "titulo": prop.titulo,
            "criterios_aceite": prop.criterios_aceite,
            "prioridade": prop.prioridade,
            "sprint_alvo": sprint_alvo,
        }
        if prop.descricao:
            payload["descricao"] = prop.descricao
        resp = client.table("funcionalidades").insert(payload).execute()
        if resp.data:
            criadas.append(resp.data[0])

    return criadas


@router.post("", response_model=FuncionalidadeResponse, status_code=201)
async def create_funcionalidade(data: FuncionalidadeCreate, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    exigir_acesso(client, pessoa, data.project_id)
    payload = {
        "project_id": data.project_id,
        "id_funcional": data.id_funcional,
        "titulo": data.titulo,
        "criterios_aceite": data.criterios_aceite,
        "prioridade": data.prioridade,
    }
    if data.descricao is not None:
        payload["descricao"] = data.descricao
    if data.responsavel is not None:
        payload["responsavel"] = data.responsavel
    payload["sprint_alvo"] = data.sprint_alvo
    response = client.table("funcionalidades").insert(payload).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to create funcionalidade")
    return response.data[0]


@router.get("", response_model=list[FuncionalidadeResponse])
async def list_funcionalidades(project_id: str = Query(...), pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    exigir_acesso(client, pessoa, project_id)
    response = (
        client.table("funcionalidades")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=False)
        .execute()
    )
    return com_tem_tasks(client, nomes_dos_aprovadores(client, response.data or []))


@router.get("/{funcionalidade_id}/transicoes", response_model=list[TransicaoStatusResponse])
async def list_transicoes(funcionalidade_id: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    exigir_acesso_por(client, pessoa, "funcionalidade", funcionalidade_id)
    response = (
        client.table("transicoes_status")
        .select("*")
        .eq("funcionalidade_id", funcionalidade_id)
        .order("timestamp", desc=False)
        .execute()
    )
    return response.data or []


@router.post("/{funcionalidade_id}/aprovar", response_model=FuncionalidadeResponse)
async def aprovar_funcionalidade(funcionalidade_id: str, pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    exigir_acesso_por(client, pessoa, "funcionalidade", funcionalidade_id)
    return aprovar(client, funcionalidade_id, pessoa["id"])


@router.delete("/{funcionalidade_id}/aprovacao", response_model=FuncionalidadeResponse)
async def desfazer_aprovacao_funcionalidade(funcionalidade_id: str, pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    exigir_acesso_por(client, pessoa, "funcionalidade", funcionalidade_id)
    return desfazer_aprovacao(client, funcionalidade_id, pessoa["id"])


@router.get("/{funcionalidade_id}", response_model=FuncionalidadeResponse)
async def get_funcionalidade(funcionalidade_id: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    response = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    exigir_acesso(client, pessoa, response.data[0]["project_id"])
    return com_tem_tasks(client, nomes_dos_aprovadores(client, [response.data[0]]))[0]


@router.patch("/{funcionalidade_id}", response_model=FuncionalidadeResponse)
async def patch_funcionalidade(
    funcionalidade_id: str,
    data: FuncionalidadeUpdate,
    pessoa: dict = Depends(get_current_pessoa),
):
    client = get_client()

    # Fetch current row
    resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    func = resp.data[0]
    exigir_acesso(client, pessoa, func["project_id"])

    if data.status is not None and data.status != func.get("status"):
        if status_derivado(tasks_da_funcionalidade(client, funcionalidade_id)) is not None:
            raise HTTPException(status_code=409, detail="O status vem das tasks desta funcionalidade.")

    agora = datetime.now(timezone.utc)

    if data.status is not None and data.status != func.get("status"):
        registrar_transicao_status(client, func, data.status, data.autor, data.motivo, agora)

    # Build update payload
    updates: dict = {}
    for field in ("titulo", "descricao", "criterios_aceite", "prioridade", "responsavel", "sprint_alvo"):
        val = getattr(data, field, None)
        if val is not None:
            updates[field] = val

    for campo in ("status",):
        novo_valor = getattr(data, campo, None)
        if novo_valor is not None and novo_valor != func.get(campo):
            updates[campo] = novo_valor

    if not updates:
        return func

    result = client.table("funcionalidades").update(updates).eq("id", funcionalidade_id).execute()
    if data.status is not None and data.status != "concluida":
        revogar_se_aprovada(client, funcionalidade_id, "revogada: status alterado")
        return com_tem_tasks(client, nomes_dos_aprovadores(client, client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute().data))[0]
    return com_tem_tasks(client, nomes_dos_aprovadores(client, result.data))[0]


@router.delete("/{funcionalidade_id}", status_code=204)
async def delete_funcionalidade(funcionalidade_id: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    check = client.table("funcionalidades").select("id, project_id").eq("id", funcionalidade_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    exigir_acesso(client, pessoa, check.data[0]["project_id"])
    client.table("funcionalidades").delete().eq("id", funcionalidade_id).execute()
