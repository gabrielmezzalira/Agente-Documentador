"""
Testes para GET /projects/{project_id}/usage.

Casos cobertos:
  1. Sem query param month -> retorna month == mês atual em America/Sao_Paulo, status 200
  2. Com month="2026-05" e mock de 2 ingestions + 1 generated_doc -> agrega corretamente
  3. month inválido "2026-13" -> 422 com detalhe sobre formato
"""
import pytest
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(ingestions_data=None, generated_docs_data=None, project_exists=True):
    """Cria um mock do cliente Supabase que responde às queries esperadas pelo handler."""
    client = MagicMock()

    proj_resp = MagicMock()
    proj_resp.data = [{"id": "test-project-id"}] if project_exists else []

    ing_resp = MagicMock()
    ing_resp.data = list(ingestions_data) if ingestions_data is not None else []

    gen_resp = MagicMock()
    gen_resp.data = list(generated_docs_data) if generated_docs_data is not None else []

    def table_side_effect(table_name):
        tbl = MagicMock()

        def select_side_effect(cols):
            query = MagicMock()
            # Cada método de filtragem retorna o mesmo query (fluent API)
            query.eq = MagicMock(return_value=query)
            query.gte = MagicMock(return_value=query)
            query.lt = MagicMock(return_value=query)
            query.order = MagicMock(return_value=query)

            if table_name == "projects":
                query.execute = MagicMock(return_value=proj_resp)
            elif table_name == "ingestions":
                query.execute = MagicMock(return_value=ing_resp)
            elif table_name == "generated_docs":
                query.execute = MagicMock(return_value=gen_resp)
            else:
                empty = MagicMock()
                empty.data = []
                query.execute = MagicMock(return_value=empty)
            return query

        tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    """Injeta o mock via monkeypatch no módulo que o router importa diretamente."""
    import routers.projects as proj_router
    monkeypatch.setattr(proj_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(
        app,
        headers={"X-Docudata-Key": os.environ["DOCUDATA_APP_SECRET"]},
    )


# ─── Teste 1: sem query param month → retorna mês atual de São Paulo ──────────

def test_usage_sem_month_retorna_mes_atual(monkeypatch):
    mock_sb = _make_mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/test-project-id/usage")
    assert resp.status_code == 200

    data = resp.json()
    assert "month" in data
    assert "total_usd" in data
    assert "input_tokens" in data
    assert "output_tokens" in data

    # Verifica que o month retornado é o mês atual em America/Sao_Paulo
    tz_sp = ZoneInfo("America/Sao_Paulo")
    expected_month = datetime.now(tz=tz_sp).strftime("%Y-%m")
    assert data["month"] == expected_month, (
        f"Esperava month={expected_month!r}, obteve {data['month']!r}"
    )
    assert data["project_id"] == "test-project-id"


# ─── Teste 2: aggregação de 2 ingestions + 1 generated_doc ────────────────────

def test_usage_agrega_ingestions_e_generated_docs(monkeypatch):
    ingestions = [
        {"cost_usd": 0.001, "input_tokens": 100, "output_tokens": 50},
        {"cost_usd": 0.002, "input_tokens": 200, "output_tokens": 80},
    ]
    generated_docs = [
        {"cost_usd": 0.005, "input_tokens": 300, "output_tokens": 120},
    ]
    mock_sb = _make_mock_client(
        ingestions_data=ingestions,
        generated_docs_data=generated_docs,
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/test-project-id/usage?month=2026-05")
    assert resp.status_code == 200

    data = resp.json()
    assert data["month"] == "2026-05"
    assert data["total_usd"] == pytest.approx(0.008, abs=1e-9)
    assert data["input_tokens"] == 600
    assert data["output_tokens"] == 250


# ─── Teste 3: month inválido → 422 ───────────────────────────────────────────

def test_usage_month_invalido_retorna_422(monkeypatch):
    mock_sb = _make_mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/test-project-id/usage?month=2026-13")
    assert resp.status_code == 422

    data = resp.json()
    detail = data.get("detail", "")
    assert "Formato invalido" in detail or "YYYY-MM" in detail, (
        f"Esperava mensagem sobre formato inválido, obteve: {detail!r}"
    )


# ─── Teste 4: breakdown por tipo ─────────────────────────────────────────────

def _make_mock_client_full(ingestions_data=None, generated_docs_data=None):
    """Mock com dados completos (id, created_at, tipo_documentacao/doc_type)."""
    client = _make_mock_client(
        ingestions_data=ingestions_data,
        generated_docs_data=generated_docs_data,
    )
    return client


def test_usage_breakdown_by_type(monkeypatch):
    ingestions = [
        {"id": "i1", "created_at": "2026-05-01T10:00:00+00:00", "tipo_documentacao": "commit",   "cost_usd": 0.001, "input_tokens": 100, "output_tokens": 50},
        {"id": "i2", "created_at": "2026-05-02T10:00:00+00:00", "tipo_documentacao": "planning",  "cost_usd": 0.002, "input_tokens": 200, "output_tokens": 80},
    ]
    generated_docs = [
        {"id": "g1", "created_at": "2026-05-03T10:00:00+00:00", "doc_type": "repasse_semanal", "cost_usd": 0.005, "input_tokens": 300, "output_tokens": 120},
        {"id": "g2", "created_at": "2026-05-04T10:00:00+00:00", "doc_type": "planning",        "cost_usd": 0.0,   "input_tokens": 0,   "output_tokens": 0},
    ]
    mock_sb = _make_mock_client_full(ingestions_data=ingestions, generated_docs_data=generated_docs)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/test-project-id/usage?month=2026-05")
    assert resp.status_code == 200
    data = resp.json()

    bd = data["breakdown"]
    assert "ingestion:commit" in bd
    assert "ingestion:planning" in bd
    assert "generation:repasse_semanal" in bd
    assert "generation:manual" in bd

    assert bd["ingestion:commit"]["count"] == 1
    assert bd["ingestion:planning"]["count"] == 1
    assert bd["generation:repasse_semanal"]["count"] == 1
    assert bd["generation:manual"]["count"] == 1

    # Somatório do breakdown deve bater com total_usd
    soma = sum(v["cost_usd"] for v in bd.values())
    assert soma == pytest.approx(data["total_usd"], abs=1e-6)


# ─── Teste 5: items cronológicos + zeros incluídos ────────────────────────────

def test_usage_items_ordered_and_zero_shown(monkeypatch):
    ingestions = [
        {"id": "i1", "created_at": "2026-05-01T10:00:00+00:00", "tipo_documentacao": "commit",  "cost_usd": 0.001, "input_tokens": 100, "output_tokens": 50},
        {"id": "i2", "created_at": "2026-05-02T10:00:00+00:00", "tipo_documentacao": "planning", "cost_usd": 0.002, "input_tokens": 200, "output_tokens": 80},
    ]
    generated_docs = [
        {"id": "g1", "created_at": "2026-05-03T10:00:00+00:00", "doc_type": "repasse_semanal", "cost_usd": 0.005, "input_tokens": 300, "output_tokens": 120},
        {"id": "g2", "created_at": "2026-05-04T10:00:00+00:00", "doc_type": "planning",        "cost_usd": 0.0,   "input_tokens": 0,   "output_tokens": 0},
    ]
    mock_sb = _make_mock_client_full(ingestions_data=ingestions, generated_docs_data=generated_docs)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/test-project-id/usage?month=2026-05")
    assert resp.status_code == 200
    data = resp.json()

    items = data["items"]
    assert len(items) == 4

    # Ordenação desc por created_at — mais recente primeiro
    created_ats = [item["created_at"] for item in items]
    assert created_ats == sorted(created_ats, reverse=True)

    # Item com cost_usd=0 está presente (não filtrado)
    zero_items = [it for it in items if it["cost_usd"] == 0.0]
    assert len(zero_items) >= 1, "Doc manual com custo 0 deve aparecer na lista"

    assert data["truncated"] is False


# ─── Teste 6: truncation acima de 100 ────────────────────────────────────────

def test_usage_truncation(monkeypatch):
    ingestions = [
        {
            "id": f"i{n}",
            "created_at": f"2026-05-{(n % 28) + 1:02d}T10:00:00+00:00",
            "tipo_documentacao": "commit",
            "cost_usd": 0.001,
            "input_tokens": 100,
            "output_tokens": 50,
        }
        for n in range(105)
    ]
    mock_sb = _make_mock_client_full(ingestions_data=ingestions, generated_docs_data=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/test-project-id/usage?month=2026-05")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["items"]) == 100
    assert data["truncated"] is True
