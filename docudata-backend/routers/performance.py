from fastapi import APIRouter, Depends

from services.audit import registrar_auditoria
from services.auth import get_current_pessoa, require_role

router = APIRouter(tags=["performance"])


@router.get("/performance", dependencies=[Depends(require_role("lider"))])
async def performance(pessoa: dict = Depends(get_current_pessoa)):
    registrar_auditoria(pessoa, "/performance", "acesso")
    return {"status": "ok", "message": "Ranking ainda não implementado — Phase 19"}
