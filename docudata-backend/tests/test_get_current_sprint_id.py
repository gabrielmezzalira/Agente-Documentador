"""Testes para get_current_sprint_id (Phase 18) — mesma lógica de resolução
de GET /projects/{id}/current-sprint (routers/commit_ingest.py, Phase 4),
mas devolvendo o id (uuid) da sprint em vez do número. Mantida como
implementação paralela e não como import cruzado de um router: extrair pra
cá evita duplicar também o endpoint HTTP, e o router antigo não precisa mudar.
"""
from unittest.mock import MagicMock

from services.sprints import get_current_sprint_id


def _mock_client(sprints, ingestions):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = sprints
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "ingestions":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = ingestions
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_retorna_none_sem_nenhuma_sprint():
    client = _mock_client(sprints=[], ingestions=[])
    assert get_current_sprint_id(client, "proj-1") is None


def test_retorna_sprint_da_ultima_planning_ingestion():
    client = _mock_client(
        sprints=[{"id": "sprint-1", "numero": 1}, {"id": "sprint-2", "numero": 2}],
        ingestions=[{"sprint_number": 2, "created_at": "2026-09-01T00:00:00Z"}],
    )
    assert get_current_sprint_id(client, "proj-1") == "sprint-2"


def test_fallback_maior_numero_sem_planning():
    client = _mock_client(
        sprints=[{"id": "sprint-1", "numero": 1}, {"id": "sprint-3", "numero": 3}],
        ingestions=[],
    )
    assert get_current_sprint_id(client, "proj-1") == "sprint-3"


def test_ignora_planning_de_sprint_ja_deletada():
    client = _mock_client(
        sprints=[{"id": "sprint-1", "numero": 1}],
        ingestions=[{"sprint_number": 5, "created_at": "2026-09-01T00:00:00Z"}],
    )
    assert get_current_sprint_id(client, "proj-1") == "sprint-1"
