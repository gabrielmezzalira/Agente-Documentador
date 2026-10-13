# docudata-backend/tests/test_discovery_store.py
from services import discovery_store as store
from tests.fake_supabase import FakeClient


def _cliente() -> FakeClient:
    return FakeClient({"projects": [{"id": "p1", "subarea": "produto"}]})


def _reuniao(c, fonte="sessao-0001"):
    return store.inserir_reuniao(
        c, project_id="p1", tipo="contexto_empresa", ocorrida_em=None,
        fonte_session_id=fonte, conteudo_estruturado={"resumo": "x"},
    )


def _requisito(c, codigo="RQ-001", status="proposto", titulo="Exportar PDF"):
    return store.inserir_requisito(c, {
        "project_id": "p1", "codigo": codigo, "titulo": titulo, "tipo": "funcional",
        "prioridade_sugerida": "should", "status": status, "criterios_aceite": [],
    })


def test_buscar_projeto():
    c = _cliente()
    assert store.buscar_projeto(c, "p1")["subarea"] == "produto"
    assert store.buscar_projeto(c, "nada") is None


def test_reuniao_e_busca_por_fonte():
    c = _cliente()
    r = _reuniao(c)
    assert store.buscar_reuniao_por_fonte(c, "sessao-0001")["id"] == r["id"]
    assert store.buscar_reuniao_por_fonte(c, "outra") is None
    assert r["analise_status"] == "pendente"


def test_transcricao_fica_em_tabela_propria_e_conta_bytes():
    c = _cliente()
    r = _reuniao(c)
    store.inserir_transcricao(c, reuniao_id=r["id"], conteudo="olá", redigida=True)
    assert "conteudo" not in store.buscar_reuniao(c, r["id"])
    t = store.buscar_transcricao(c, r["id"])
    assert t["conteudo"] == "olá" and t["redigida"] is True
    assert c.tables["discovery_transcricoes"][0]["tamanho"] == 4
    assert store.buscar_transcricao(c, "nada") is None


def test_marcar_analise():
    c = _cliente()
    r = _reuniao(c)
    store.marcar_analise(c, r["id"], "falhou", "falha na análise")
    linha = store.buscar_reuniao(c, r["id"])
    assert linha["analise_status"] == "falhou" and linha["analise_erro"] == "falha na análise"
    store.marcar_analise(c, r["id"], "ok")
    assert store.buscar_reuniao(c, r["id"])["analise_erro"] is None


def test_listar_requisitos_filtra_por_status():
    c = _cliente()
    _requisito(c, "RQ-001", "proposto")
    _requisito(c, "RQ-002", "validado")
    assert len(store.listar_requisitos(c, "p1")) == 2
    assert [r["codigo"] for r in store.listar_requisitos(c, "p1", "validado")] == ["RQ-002"]


def test_atualizar_requisito_grava_updated_at():
    c = _cliente()
    r = _requisito(c)
    novo = store.atualizar_requisito(c, r["id"], {"status": "em_revisao"})
    assert novo["status"] == "em_revisao" and novo["updated_at"]


def test_evidencia_duplicada_nao_insere_e_contagem_por_requisito():
    c = _cliente()
    r1, r2 = _requisito(c, "RQ-001"), _requisito(c, "RQ-002")
    m = _reuniao(c)
    assert store.inserir_evidencia(c, requisito_id=r1["id"], reuniao_id=m["id"], trecho="queremos pdf", speaker="Ana", confianca=0.9) is True
    assert store.inserir_evidencia(c, requisito_id=r1["id"], reuniao_id=m["id"], trecho="queremos pdf", speaker="Ana", confianca=0.9) is False
    assert store.inserir_evidencia(c, requisito_id=r1["id"], reuniao_id=m["id"], trecho="outro trecho", speaker=None, confianca=None) is True
    assert store.contar_evidencias(c, [r1["id"], r2["id"]]) == {r1["id"]: 2, r2["id"]: 0}
    assert len(store.listar_evidencias(c, r1["id"])) == 2


def test_transicoes_em_ordem():
    c = _cliente()
    r = _requisito(c)
    store.inserir_transicao(c, requisito_id=r["id"], campo="status", de="proposto", para="em_revisao", autor="a@x", motivo=None)
    assert store.listar_transicoes(c, r["id"])[0]["para"] == "em_revisao"


def test_atualizar_requisito_se_editavel_respeita_o_status_atual():
    c = _cliente()
    r = _requisito(c)
    store.atualizar_requisito(c, r["id"], {"status": "validado"})
    assert store.atualizar_requisito_se_editavel(c, r["id"], {"prioridade_sugerida": "wont"}) is None
    assert store.buscar_requisito(c, r["id"])["prioridade_sugerida"] != "wont"
    store.atualizar_requisito(c, r["id"], {"status": "proposto"})
    assert store.atualizar_requisito_se_editavel(c, r["id"], {"prioridade_sugerida": "wont"})["prioridade_sugerida"] == "wont"


# ---- reserva da análise (compare-and-swap) ----
from datetime import datetime, timedelta, timezone

_T0 = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def test_reservar_analise_so_uma_vez_e_so_se_pendente():
    c = _cliente()
    m = _reuniao(c)
    assert store.reservar_analise(c, m["id"], agora=_T0) is True
    assert store.reservar_analise(c, m["id"], agora=_T0 + timedelta(seconds=10)) is False  # reserva ativa
    store.marcar_analise(c, m["id"], "ok")
    assert store.reservar_analise(c, m["id"], agora=_T0 + timedelta(hours=1)) is False  # não pendente


def test_reserva_expirada_e_retomada_e_falhou_nao_reserva_ate_reiniciar():
    c = _cliente()
    m = _reuniao(c)
    assert store.reservar_analise(c, m["id"], agora=_T0)
    assert store.reservar_analise(c, m["id"], agora=_T0 + timedelta(minutes=16)) is True
    store.marcar_analise(c, m["id"], "falhou", "x")
    assert store.reservar_analise(c, m["id"], agora=_T0 + timedelta(hours=2)) is False
    assert store.reiniciar_analise(c, m["id"], agora=_T0 + timedelta(hours=2)) is True
    assert store.reservar_analise(c, m["id"], agora=_T0 + timedelta(hours=2)) is True


def test_reiniciar_nao_derruba_analise_em_andamento():
    c = _cliente()
    m = _reuniao(c)
    assert store.reservar_analise(c, m["id"], agora=_T0)
    assert store.reiniciar_analise(c, m["id"], agora=_T0 + timedelta(seconds=5)) is False
    assert store.buscar_reuniao(c, m["id"])["analise_iniciada_em"] is not None
    assert store.reiniciar_analise(c, m["id"], agora=_T0 + timedelta(minutes=20)) is True
    assert store.buscar_reuniao(c, m["id"])["analise_iniciada_em"] is None


def test_cas_perde_quando_outra_reserva_ocorre_entre_a_leitura_e_a_escrita(monkeypatch):
    c = _cliente()
    m = _reuniao(c)
    leitura_antiga = dict(store.buscar_reuniao(c, m["id"]))  # ainda sem reserva
    assert store.reservar_analise(c, m["id"], agora=_T0)  # o concorrente ganhou
    monkeypatch.setattr(store, "buscar_reuniao", lambda *_a, **_k: leitura_antiga)
    assert store.reservar_analise(c, m["id"], agora=_T0 + timedelta(seconds=1)) is False
