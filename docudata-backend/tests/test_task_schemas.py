from models.schemas import TaskResponse


def test_task_response_aceita_campos_de_fila():
    resp = TaskResponse(
        id="t1", project_id="p1", titulo="X", pontos=3, coluna_kanban="planejado",
        bloqueado=False, checklist=[], ordem=0,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
        entrou_na_fila_em="2026-09-01T00:00:00Z", pull_em=None,
        atribuida_manualmente=False, motivo_atribuicao_manual=None,
        ordem_fila=2,
    )
    assert resp.ordem_fila == 2


def test_task_response_campos_de_fila_tem_default_seguro():
    resp = TaskResponse(
        id="t1", project_id="p1", titulo="X", pontos=3, coluna_kanban="planejado",
        bloqueado=False, checklist=[], ordem=0,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
    )
    assert resp.atribuida_manualmente is False
    assert resp.ordem_fila is None
