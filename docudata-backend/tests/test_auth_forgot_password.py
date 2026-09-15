"""Testes para o fluxo de 'esqueci minha senha' (POST /auth/forgot-password
e POST /auth/reset-password). Token é um JWT de curta duração com claim
purpose='password_reset', assinado com o mesmo JWT_SECRET da sessão — mas
rejeitado explicitamente se usado fora desse propósito (ex: um token de
sessão normal não pode servir de token de reset)."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.auth import criar_jwt, criar_jwt_reset_senha, decodificar_jwt_reset_senha, hash_senha


# ── Unidade: services/auth.py ──────────────────────────────────────────────

def test_criar_e_decodificar_jwt_reset_senha(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    token = criar_jwt_reset_senha("pessoa-1", "a@citi.com")

    payload = decodificar_jwt_reset_senha(token)

    assert payload["sub"] == "pessoa-1"
    assert payload["email"] == "a@citi.com"
    assert payload["purpose"] == "password_reset"


def test_decodificar_jwt_reset_senha_rejeita_token_de_sessao_normal(monkeypatch):
    """Um JWT de sessão (login normal) não pode ser reaproveitado como token
    de redefinição de senha — teria acesso permanente (8h) a trocar a senha."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    token_sessao = criar_jwt("pessoa-1", "a@citi.com", "gerente")

    with pytest.raises(Exception):
        decodificar_jwt_reset_senha(token_sessao)


# ── Endpoint: POST /auth/forgot-password ───────────────────────────────────

def _mock_client_pessoa(pessoa_row):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pessoa":
            def select_side_effect(cols):
                query = MagicMock()

                def eq_side_effect(field, value):
                    resp = MagicMock()
                    resp.data = [pessoa_row] if pessoa_row and pessoa_row.get(field) == value else []
                    q = MagicMock()
                    q.execute = MagicMock(return_value=resp)
                    return q

                query.eq = MagicMock(side_effect=eq_side_effect)
                return query

            def update_side_effect(updates):
                q = MagicMock()

                def eq_then_execute(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(pessoa_row, **updates)] if pessoa_row and pessoa_row.get("id") == value else []
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_then_execute)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase, send_email_mock=None):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.auth as auth_router
    monkeypatch.setattr(auth_router, "get_client", lambda: mock_supabase)
    if send_email_mock is not None:
        monkeypatch.setattr(auth_router, "send_email", send_email_mock)
    from main import app
    return TestClient(app)


_PESSOA = {"id": "pessoa-1", "email": "gerente@citi.com", "nome": "Gerente Um", "cargo": "gerente"}


def test_forgot_password_email_existente_envia_email(monkeypatch):
    enviados = []
    mock_sb = _mock_client_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb, send_email_mock=lambda to, subject, body: enviados.append((to, subject, body)))

    resp = tc.post("/auth/forgot-password", json={"email": "gerente@citi.com"})

    assert resp.status_code == 200
    assert len(enviados) == 1
    assert enviados[0][0] == "gerente@citi.com"


def test_forgot_password_email_inexistente_nao_envia_mas_resposta_e_identica(monkeypatch):
    """Anti-enumeração: resposta idêntica exista ou não o email, e nenhum
    email é disparado se a conta não existir."""
    enviados = []
    mock_sb = _mock_client_pessoa(None)
    tc = _patch_and_client(monkeypatch, mock_sb, send_email_mock=lambda to, subject, body: enviados.append((to, subject, body)))

    resp_existente = tc.post("/auth/forgot-password", json={"email": "gerente@citi.com"})
    mock_sb2 = _mock_client_pessoa(_PESSOA)
    tc2 = _patch_and_client(monkeypatch, mock_sb2, send_email_mock=lambda to, subject, body: enviados.append((to, subject, body)))
    resp_inexistente = tc.post("/auth/forgot-password", json={"email": "naoexiste@citi.com"})

    assert resp_inexistente.status_code == 200
    assert resp_inexistente.json() == resp_existente.json()
    assert len(enviados) == 0


def test_forgot_password_falha_no_envio_nao_quebra_resposta(monkeypatch):
    def _explode(to, subject, body):
        raise RuntimeError("Resend fora do ar")

    mock_sb = _mock_client_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb, send_email_mock=_explode)

    resp = tc.post("/auth/forgot-password", json={"email": "gerente@citi.com"})

    assert resp.status_code == 200


# ── Endpoint: POST /auth/reset-password ────────────────────────────────────

def test_reset_password_token_valido_atualiza_senha(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb)
    token = criar_jwt_reset_senha("pessoa-1", "gerente@citi.com")

    resp = tc.post("/auth/reset-password", json={"token": token, "nova_senha": "senha-nova-123"})

    assert resp.status_code == 200


def test_reset_password_token_invalido_retorna_400(monkeypatch):
    mock_sb = _mock_client_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/auth/reset-password", json={"token": "token-invalido-qualquer", "nova_senha": "senha-nova-123"})

    assert resp.status_code == 400


def test_reset_password_token_de_sessao_normal_e_rejeitado(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb)
    token_sessao = criar_jwt("pessoa-1", "gerente@citi.com", "gerente")

    resp = tc.post("/auth/reset-password", json={"token": token_sessao, "nova_senha": "senha-nova-123"})

    assert resp.status_code == 400


def test_reset_password_senha_curta_retorna_422(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    mock_sb = _mock_client_pessoa(_PESSOA)
    tc = _patch_and_client(monkeypatch, mock_sb)
    token = criar_jwt_reset_senha("pessoa-1", "gerente@citi.com")

    resp = tc.post("/auth/reset-password", json={"token": token, "nova_senha": "123"})

    assert resp.status_code == 422
