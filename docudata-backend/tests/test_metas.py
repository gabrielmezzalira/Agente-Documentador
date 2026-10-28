from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import routers.metas as rota
from services.metas import diferenca_meta, meta_em, meta_original, resultado_meta, funcionalidade_entregue
from tests.fake_supabase import FakeClient


def ev(f, acao, dia, hora=12):
    return {"funcionalidade_id": f, "acao": acao, "criado_em": datetime(2026, 11, dia, hora, tzinfo=timezone.utc).isoformat()}


def test_diferenca():
    assert diferenca_meta({"a", "b"}, {"b", "c"}) == ({"c"}, {"a"})


def test_meta_em_reaplica_eventos():
    evs = [ev("a", "incluiu", 1), ev("b", "incluiu", 1), ev("a", "retirou", 3)]
    assert meta_em(evs, datetime(2026, 11, 2, tzinfo=timezone.utc)) == {"a", "b"}
    assert meta_em(evs, datetime(2026, 11, 4, tzinfo=timezone.utc)) == {"b"}


def test_meta_original_com_inicio():
    evs = [ev("a", "incluiu", 1), ev("b", "incluiu", 5)]
    assert meta_original(evs, datetime(2026, 11, 3, tzinfo=timezone.utc)) == {"a"}


def test_meta_original_sem_inicio_usa_fim_do_dia_do_primeiro_evento():
    evs = [ev("a", "incluiu", 1, 9), ev("b", "incluiu", 1, 18), ev("c", "incluiu", 2)]
    assert meta_original(evs, None) == {"a", "b"}


def test_meta_original_definida_depois_do_inicio():
    evs = [ev("a", "incluiu", 6, 9), ev("b", "incluiu", 6, 10)]
    assert meta_original(evs, datetime(2026, 11, 3, tzinfo=timezone.utc)) == {"a", "b"}


def test_resultado_meta():
    assert resultado_meta(set(), set()) == {"total": 0, "entregues": 0, "batida": None}
    assert resultado_meta({"a", "b"}, {"a"}) == {"total": 2, "entregues": 1, "batida": False}
    assert resultado_meta({"a"}, {"a", "x"}) == {"total": 1, "entregues": 1, "batida": True}


def test_entregue_respeita_fechamento():
    f = {"status": "concluida", "aprovada_em": "2026-11-10T10:00:00+00:00"}
    assert funcionalidade_entregue(f, None) is True
    assert funcionalidade_entregue(f, "2026-11-09T23:00:00+00:00") is False
    assert funcionalidade_entregue(f, "2026-11-10T12:00:00+00:00") is True
    assert funcionalidade_entregue({"status": "em_andamento", "aprovada_em": None}, None) is False


# ── rotas ──

def _fake(sprint_extra=None):
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "avaliacao_completa_em": None, **(sprint_extra or {})}],
        "funcionalidades": [
            {"id": "a", "project_id": "p1", "id_funcional": "F-1", "titulo": "Func A", "status": "em_andamento", "aprovada_em": None},
            {"id": "b", "project_id": "p1", "id_funcional": "F-2", "titulo": "Func B", "status": "nao_iniciada", "aprovada_em": None},
            {"id": "c", "project_id": "p1", "id_funcional": "F-3", "titulo": "Func C", "status": "nao_iniciada", "aprovada_em": None},
            {"id": "x", "project_id": "p2", "id_funcional": "F-9", "titulo": "Outra", "status": "nao_iniciada", "aprovada_em": None},
            {"id": "d", "project_id": "p1", "id_funcional": "F-4", "titulo": "Entregue", "status": "concluida",
             "aprovada_em": "2026-10-01T10:00:00+00:00"},
        ],
        "pessoa": [{"id": "pessoa-teste", "nome": "Líder Teste"}],
    })


def _tc(monkeypatch, autenticar, cargo="lider", fake=None):
    from main import app
    fake = fake or _fake()
    monkeypatch.setattr(rota, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo), fake


def _ids(fake):
    return {r["funcionalidade_id"] for r in fake.tables.get("sprint_meta_funcionalidades", [])}


def test_put_inclui_e_registra_eventos(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a", "b"]})
    assert r.status_code == 200
    assert r.json()["sprint_id"] == "s1"
    assert set(r.json()["funcionalidade_ids"]) == {"a", "b"}
    assert _ids(fake) == {"a", "b"}
    eventos = fake.tables["sprint_meta_eventos"]
    assert {(e["funcionalidade_id"], e["acao"], e["pessoa_id"]) for e in eventos} == {
        ("a", "incluiu", "pessoa-teste"), ("b", "incluiu", "pessoa-teste")}
    assert all(l["incluida_por"] == "pessoa-teste" for l in fake.tables["sprint_meta_funcionalidades"])


def test_put_troca_gera_incluiu_e_retirou(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a", "b"]})
    tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["b", "c"]})
    assert _ids(fake) == {"b", "c"}
    novos = fake.tables["sprint_meta_eventos"][2:]
    assert {(e["funcionalidade_id"], e["acao"]) for e in novos} == {("c", "incluiu"), ("a", "retirou")}
    assert set(tc.get("/sprints/s1/meta").json()["funcionalidade_ids"]) == {"b", "c"}


def test_put_sprint_fechada_409(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar, fake=_fake({"avaliacao_completa_em": "2026-10-20T00:00:00+00:00"}))
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a"]})
    assert r.status_code == 409
    assert r.json()["detail"] == "A sprint já foi fechada; a meta não pode mais mudar."


def test_put_funcionalidade_de_outro_projeto_422(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a", "x"]})
    assert r.status_code == 422
    assert r.json()["detail"] == "Funcionalidade inválida para a meta: F-9"
    assert _ids(fake) == set()


def test_put_funcionalidade_entregue_422(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar)
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["d"]})
    assert r.status_code == 422
    assert r.json()["detail"] == "Funcionalidade inválida para a meta: F-4"


def test_put_sprint_inexistente_404(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar)
    assert tc.put("/sprints/zzz/meta", json={"funcionalidade_ids": []}).status_code == 404


@pytest.mark.parametrize("cargo", ["gerente", "operacional"])
def test_so_lider_acessa(monkeypatch, autenticar, cargo):
    tc, _ = _tc(monkeypatch, autenticar, cargo=cargo)
    assert tc.get("/sprints/s1/meta").status_code == 403
    assert tc.put("/sprints/s1/meta", json={"funcionalidade_ids": []}).status_code == 403
    assert tc.get("/sprints/s1/meta/eventos").status_code == 403


def test_owner_acessa(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar, cargo="owner")
    assert tc.get("/sprints/s1/meta").status_code == 200


def test_eventos_em_ordem_cronologica_com_titulo_e_pessoa(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["sprint_meta_eventos"] = [
        {"id": "e2", "sprint_id": "s1", "funcionalidade_id": "b", "acao": "retirou", "pessoa_id": "pessoa-teste",
         "criado_em": "2026-11-03T10:00:00+00:00"},
        {"id": "e1", "sprint_id": "s1", "funcionalidade_id": "b", "acao": "incluiu", "pessoa_id": "pessoa-teste",
         "criado_em": "2026-11-01T10:00:00+00:00"},
    ]
    tc, _ = _tc(monkeypatch, autenticar, fake=fake)
    r = tc.get("/sprints/s1/meta/eventos")
    assert r.status_code == 200
    assert [e["acao"] for e in r.json()] == ["incluiu", "retirou"]
    assert r.json()[0] == {"funcionalidade_id": "b", "titulo": "Func B", "acao": "incluiu",
                           "pessoa_nome": "Líder Teste", "criado_em": "2026-11-01T10:00:00+00:00"}


def test_put_mantem_entregue_ja_na_meta(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["sprint_meta_funcionalidades"] = [{"sprint_id": "s1", "funcionalidade_id": "d", "incluida_por": "x"},
                                                  {"sprint_id": "s1", "funcionalidade_id": "a", "incluida_por": "x"}]
    tc, _ = _tc(monkeypatch, autenticar, fake=fake)
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["d", "b"]})
    assert r.status_code == 200
    assert _ids(fake) == {"d", "b"}


def test_put_ids_duplicados(monkeypatch, autenticar):
    tc, fake = _tc(monkeypatch, autenticar)
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a", "a"]})
    assert r.status_code == 200 and r.json()["funcionalidade_ids"] == ["a"]
    assert len(fake.tables["sprint_meta_eventos"]) == 1


def test_get_meta_sprint_inexistente_404(monkeypatch, autenticar):
    tc, _ = _tc(monkeypatch, autenticar)
    assert tc.get("/sprints/zzz/meta").status_code == 404
    assert tc.get("/sprints/zzz/meta/eventos").status_code == 404


def test_falha_na_inclusao_vira_409_e_retry_cura(monkeypatch, autenticar):
    from tests import fake_supabase
    fake = _fake()
    tc, _ = _tc(monkeypatch, autenticar, fake=fake)
    original = fake_supabase._Query.execute

    def quebra(self):
        if self._name == "sprint_meta_funcionalidades" and self._op == "upsert":
            raise RuntimeError("duplicate key value violates unique constraint")
        return original(self)

    monkeypatch.setattr(fake_supabase._Query, "execute", quebra)
    r = tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a", "b"]})
    assert r.status_code == 409
    assert r.json()["detail"] == "A meta foi alterada ao mesmo tempo; recarregue e tente de novo."
    assert _ids(fake) == set() and len(fake.tables["sprint_meta_eventos"]) == 2  # eventos escritos antes

    monkeypatch.setattr(fake_supabase._Query, "execute", original)
    assert tc.put("/sprints/s1/meta", json={"funcionalidade_ids": ["a", "b"]}).status_code == 200
    from services.metas import meta_em
    evs = [dict(e, criado_em=e.get("criado_em") or "2026-11-01T00:00:00+00:00") for e in fake.tables["sprint_meta_eventos"]]
    assert _ids(fake) == {"a", "b"} == meta_em(evs, datetime(2030, 1, 1, tzinfo=timezone.utc))
