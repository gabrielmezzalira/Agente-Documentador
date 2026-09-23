"""Bloqueio do tipo 'cliente' — dependência do cliente não pode zerar a Entrega
de ninguém (design aprovado 2026-09-23)."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.schemas import TaskUpdate, TaskResponse

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text()


def test_schema_adiciona_bloqueio_tipo_nao_destrutivo():
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS bloqueio_tipo text" in SCHEMA
    assert "CHECK (bloqueio_tipo IN ('interno','cliente'))" in SCHEMA


def test_task_update_aceita_bloqueio_tipo_valido():
    assert TaskUpdate(bloqueio_tipo="cliente").bloqueio_tipo == "cliente"
    assert TaskUpdate(bloqueio_tipo="interno").bloqueio_tipo == "interno"


def test_task_update_rejeita_bloqueio_tipo_invalido():
    with pytest.raises(ValidationError):
        TaskUpdate(bloqueio_tipo="fornecedor")


def test_task_response_expoe_bloqueio_tipo_opcional():
    assert "bloqueio_tipo" in TaskResponse.model_fields
    assert TaskResponse.model_fields["bloqueio_tipo"].default is None


# ── PATCH /tasks/{id} ────────────────────────────────────────────────────────

from tests.test_bloqueio_manual import _BASE_TASK, _make_mock_client, _patch_and_client  # noqa: E402


def test_gerente_marca_bloqueio_de_cliente(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=False)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": True, "bloqueio_tipo": "cliente"})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["bloqueado_manual"] is True
    assert updates["bloqueio_tipo"] == "cliente"
    assert updates["travado_automatico"] is False


def test_marcar_bloqueio_sem_tipo_grava_interno(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=False)
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": True})

    assert resp.status_code == 200
    assert calls["tasks_update"][-1]["bloqueio_tipo"] == "interno"
    assert "travado_automatico" not in calls["tasks_update"][-1]


def test_trocar_tipo_de_task_ja_bloqueada_para_cliente(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueio_tipo="interno")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueio_tipo": "cliente"})

    assert resp.status_code == 200
    assert calls["tasks_update"][-1]["bloqueio_tipo"] == "cliente"
    assert calls["tasks_update"][-1]["travado_automatico"] is False


def test_destravar_bloqueio_de_cliente_nao_exige_quem_resolveu_e_nao_conta_autonomia(monkeypatch):
    task = dict(
        _BASE_TASK, bloqueado_manual=True, bloqueio_tipo="cliente",
        entrou_em_andamento_em="2026-09-01T00:00:00+00:00",
    )
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False})

    assert resp.status_code == 200
    updates = calls["tasks_update"][-1]
    assert updates["bloqueado_manual"] is False
    assert updates["bloqueio_tipo"] is None
    assert "bloqueado_resolvido_por" not in updates
    assert "bloqueado_resolvido_em" not in updates
    assert updates["entrou_em_andamento_em"] != "2026-09-01T00:00:00+00:00"
    assert updates["travado_automatico"] is False


def test_destravar_bloqueio_interno_continua_exigindo_quem_resolveu(monkeypatch):
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueio_tipo="interno")
    mock_sb, calls = _make_mock_client(task)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"bloqueado_manual": False})

    assert resp.status_code == 422
    assert len(calls["tasks_update"]) == 0


def test_operacional_nao_pode_mexer_no_tipo_de_bloqueio(monkeypatch):
    from tests.test_task_rbac_operacional import _client_como
    task = dict(_BASE_TASK, bloqueado_manual=True, bloqueio_tipo="interno")
    mock_sb, calls = _make_mock_client(task)
    tc = _client_como(monkeypatch, mock_sb, "operacional")

    resp = tc.patch("/tasks/task-1", json={"bloqueio_tipo": "cliente"})

    assert resp.status_code == 403
    assert len(calls["tasks_update"]) == 0
