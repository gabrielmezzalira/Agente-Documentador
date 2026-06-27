from fastapi import APIRouter, HTTPException

from services.google_docs import export_to_gdocs
from services.supabase_client import get_client

router = APIRouter(tags=["export"])

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

    proj_resp = client.table("projects").select("*").eq("id", doc["project_id"]).execute()
    if not proj_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = proj_resp.data[0]

    try:
        url = export_to_gdocs(
            markdown_content=doc["content"],
            doc_type_label=_DOC_TYPE_LABELS.get(doc["doc_type"], doc["doc_type"]),
            projeto_nome=project["name"],
            cliente=project["client"],
            sprint_numero=doc.get("sprint_number"),
            created_at=doc["created_at"],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao exportar para Google Docs: {e}")

    return {"url": url}
