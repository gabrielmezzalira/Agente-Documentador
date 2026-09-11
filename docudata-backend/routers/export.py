from fastapi import APIRouter, HTTPException

from core.observability import falha_externa
from services.google_docs import export_to_gdocs
from services.supabase_client import get_client

router = APIRouter(tags=["export"])

_ERRO_EXPORTACAO = "Não foi possível exportar o documento para o Google Docs"

_DOC_TYPE_LABELS = {
    "repasse_semanal": "Repasse Semanal",
    "retrospectiva": "Retrospectiva",
    "ata_reuniao": "Ata de Reunião",
    "log_decisoes": "Log de Decisões",
    "onboarding": "Onboarding",
    "documentacao_final": "Documentação Final",
    "planning": "Planning",
    "daily": "Daily",
    "review": "Review",
}


@router.post("/docs/{doc_id}/export-gdocs")
async def export_doc_to_gdocs(doc_id: str):
    client = get_client()

    doc_resp = client.table("generated_docs").select("*").eq("id", doc_id).execute()
    if not doc_resp.data:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = doc_resp.data[0]

    proj_resp = (
        client.table("projects")
        .select("id, name, client, squad, subarea")
        .eq("id", doc["project_id"])
        .execute()
    )
    if not proj_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = proj_resp.data[0]

    try:
        url = export_to_gdocs(
            project_id=doc["project_id"],
            markdown_content=doc["content"],
            doc_type_label=_DOC_TYPE_LABELS.get(doc["doc_type"], doc["doc_type"]),
            projeto_nome=project["name"],
            cliente=project["client"],
            squad=project.get("squad") or "—",
            sprint_numero=doc.get("sprint_number"),
            created_at=doc["created_at"],
            subarea=project["subarea"],
            doc_type=doc["doc_type"],
        )
    except RuntimeError as e:
        # Configuração ausente do Drive/Docs: o texto original cita variável de
        # ambiente e id de pasta, então some do corpo e fica só no log.
        raise falha_externa(
            "google_docs.configuracao", e, _ERRO_EXPORTACAO, status_code=503
        )
    except Exception as e:
        raise falha_externa("google_docs.export", e, _ERRO_EXPORTACAO)

    return {"url": url}
