# docudata-backend/tests/test_discovery_analise.py
import pytest

from models.discovery import AjustePrioridade, Conflito, NovoRequisito, Reforco, SaidaAnalise
from services import discovery_analise as analise
from services import discovery_store as store
from tests.fake_supabase import FakeClient


def _cliente():
    return FakeClient({"projects": [{"id": "p1", "subarea": "produto"}]})


def _reuniao(c, fonte="sessao-0001", tipo="contexto_empresa", transcricao=None):
    r = store.inserir_reuniao(c, project_id="p1", tipo=tipo, ocorrida_em=None, fonte_session_id=fonte,
                              conteudo_estruturado={"resumo": "cliente quer exportar PDF"})
    if transcricao:
        store.inserir_transcricao(c, reuniao_id=r["id"], conteudo=transcricao, redigida=False)
    return r


def _executor(saida: SaidaAnalise, capturas=None):
    async def _exec(**kwargs):
        if capturas is not None:
            capturas.append(kwargs)
        return saida
    return _exec


def _novo(titulo="Exportar relatório em PDF", trecho="precisamos exportar o relatório em PDF", **kw):
    return NovoRequisito(titulo=titulo, descricao="d", tipo="funcional", lente="produto",
                         criterios_aceite=["Dado X, quando Y, então Z"], prioridade_sugerida="must",
                         justificativa="dor citada", trecho=trecho, speaker="Marina", confianca=0.8, **kw)


@pytest.mark.asyncio
async def test_cria_requisito_proposto_com_codigo_e_evidencia():
    c = _cliente()
    r = _reuniao(c)
    contagens = await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    assert contagens["novos"] == 1
    reqs = store.listar_requisitos(c, "p1")
    assert [(q["codigo"], q["status"], q["lente"]) for q in reqs] == [("RQ-001", "proposto", "produto")]
    assert store.listar_evidencias(c, reqs[0]["id"])[0]["trecho"] == "precisamos exportar o relatório em PDF"
    assert store.buscar_reuniao(c, r["id"])["analise_status"] == "ok"


@pytest.mark.asyncio
async def test_segunda_reuniao_reforca_sem_duplicar():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    r2 = _reuniao(c, "sessao-0002", tipo="entrevista_tecnica")
    saida = SaidaAnalise(reforcos=[Reforco(codigo="RQ-001", trecho="o técnico confirmou que precisa do PDF", speaker="Davi")])
    contagens = await analise.analisar_reuniao(c, r2["id"], executar=_executor(saida), obter_chave=lambda: "k")
    assert contagens["reforcos"] == 1
    assert len(store.listar_requisitos(c, "p1")) == 1
    req = store.listar_requisitos(c, "p1")[0]
    assert store.contar_evidencias(c, [req["id"]])[req["id"]] == 2


@pytest.mark.asyncio
async def test_duplicata_duvidosa_vira_em_revisao_com_sinalizacao():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    r2 = _reuniao(c, "sessao-0002")
    saida = SaidaAnalise(novos=[_novo("Exportar relatorio em PDF", "o relatório em PDF é essencial")])
    contagens = await analise.analisar_reuniao(c, r2["id"], executar=_executor(saida), obter_chave=lambda: "k")
    assert contagens["duplicatas"] == 1
    novo = [q for q in store.listar_requisitos(c, "p1") if q["codigo"] == "RQ-002"][0]
    assert novo["status"] == "em_revisao" and novo["possivel_duplicata_de"] is not None


@pytest.mark.asyncio
async def test_validado_e_rejeitado_nunca_sao_alterados_automaticamente():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    req = store.listar_requisitos(c, "p1")[0]
    store.atualizar_requisito(c, req["id"], {"status": "validado", "prioridade_sugerida": "must"})
    r2 = _reuniao(c, "sessao-0002")
    saida = SaidaAnalise(
        ajustes_prioridade=[AjustePrioridade(codigo="RQ-001", prioridade="wont", justificativa="mudou")],
        conflitos=[Conflito(codigo="RQ-001", descricao="o cliente disse o contrário")],
        reforcos=[Reforco(codigo="RQ-001", trecho="de novo o PDF é obrigatório para nós")],
    )
    await analise.analisar_reuniao(c, r2["id"], executar=_executor(saida), obter_chave=lambda: "k")
    depois = store.buscar_requisito(c, req["id"])
    assert depois["status"] == "validado" and depois["prioridade_sugerida"] == "must"
    assert depois["conflito"] is True
    assert store.contar_evidencias(c, [req["id"]])[req["id"]] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["validado", "rejeitado"])
async def test_ajuste_e_demais_campos_de_validado_ou_rejeitado_ficam_intactos(status):
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    req = store.listar_requisitos(c, "p1")[0]
    store.atualizar_requisito(c, req["id"], {"status": status})
    antes = store.buscar_requisito(c, req["id"])
    transicoes_antes = len(store.listar_transicoes(c, req["id"]))
    r2 = _reuniao(c, "sessao-0002")
    saida = SaidaAnalise(
        ajustes_prioridade=[AjustePrioridade(codigo="RQ-001", prioridade="wont", justificativa="mudou")],
        conflitos=[Conflito(codigo="RQ-001", descricao="tensão")],
        reforcos=[Reforco(codigo="RQ-001", trecho="outra menção ao PDF")],
    )
    contagens = await analise.analisar_reuniao(c, r2["id"], executar=_executor(saida), obter_chave=lambda: "k")
    depois = store.buscar_requisito(c, req["id"])
    for campo in ("status", "prioridade_sugerida", "titulo", "descricao", "justificativa", "criterios_aceite", "tipo"):
        assert depois[campo] == antes[campo]
    assert contagens["ajustes"] == 0
    novas = store.listar_transicoes(c, req["id"])[transicoes_antes:]
    assert {t["campo"] for t in novas} <= {"conflito"}  # nenhuma transição de status/prioridade


@pytest.mark.asyncio
async def test_ajuste_de_prioridade_vale_para_proposto():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    r2 = _reuniao(c, "sessao-0002")
    saida = SaidaAnalise(ajustes_prioridade=[AjustePrioridade(codigo="RQ-001", prioridade="could", justificativa="cliente relativizou")])
    await analise.analisar_reuniao(c, r2["id"], executar=_executor(saida), obter_chave=lambda: "k")
    assert store.listar_requisitos(c, "p1")[0]["prioridade_sugerida"] == "could"


@pytest.mark.asyncio
async def test_falha_do_executor_marca_falhou_sem_vazar_detalhe():
    c = _cliente()
    r = _reuniao(c)

    async def quebra(**_):
        raise RuntimeError("detalhe interno SEGREDO-XYZ")
    await analise.analisar_reuniao(c, r["id"], executar=quebra, obter_chave=lambda: "k")
    linha = store.buscar_reuniao(c, r["id"])
    assert linha["analise_status"] == "falhou"
    assert "SEGREDO-XYZ" not in (linha["analise_erro"] or "")


@pytest.mark.asyncio
async def test_usa_a_transcricao_como_fonte_quando_existe():
    c = _cliente()
    r = _reuniao(c, transcricao="Marina: precisamos exportar o relatório em PDF")
    capturas = []
    await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(), capturas), obter_chave=lambda: "k")
    assert "Marina: precisamos exportar o relatório em PDF" in capturas[0]["fonte"]
    assert capturas[0]["tipo"] == "contexto_empresa" and capturas[0]["api_key"] == "k"
    assert isinstance(capturas[0]["existentes"], list)


def test_fonte_sem_transcricao_usa_o_conteudo_estruturado():
    assert "cliente quer exportar PDF" in analise.fonte_da_reuniao({"conteudo_estruturado": {"resumo": "cliente quer exportar PDF"}}, None)


@pytest.mark.asyncio
async def test_reconsolidar_reanalisa_em_ordem_e_nao_duplica_evidencia():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    saida = SaidaAnalise(reforcos=[Reforco(codigo="RQ-001", trecho="precisamos exportar o relatório em PDF")])
    total = await analise.reconsolidar_projeto(c, "p1", executar=_executor(saida), obter_chave=lambda: "k")
    assert total == 1
    req = store.listar_requisitos(c, "p1")[0]
    assert store.contar_evidencias(c, [req["id"]])[req["id"]] == 1


# ---- endurecimento (entrada do modelo é não confiável) ----
@pytest.mark.asyncio
async def test_codigos_sequenciais_na_mesma_rodada_e_titulo_vazio_ignorado():
    c = _cliente()
    r = _reuniao(c)
    saida = SaidaAnalise(novos=[_novo("Primeiro requisito"), _novo("   "), _novo("Segundo requisito totalmente diferente")])
    contagens = await analise.analisar_reuniao(c, r["id"], executar=_executor(saida), obter_chave=lambda: "k")
    assert contagens["novos"] == 2
    assert [q["codigo"] for q in store.listar_requisitos(c, "p1")] == ["RQ-001", "RQ-002"]


@pytest.mark.asyncio
async def test_limites_titulo_confianca_nan_e_speaker():
    c = _cliente()
    r = _reuniao(c)
    n = _novo("T" * 500).model_copy(update={"confianca": float("nan"), "speaker": "S" * 900})
    n2 = _novo("Outro requisito bem diferente aqui").model_copy(update={"confianca": 7.0})
    await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[n, n2])), obter_chave=lambda: "k")
    reqs = store.listar_requisitos(c, "p1")
    assert len(reqs[0]["titulo"]) <= 200
    ev = store.listar_evidencias(c, reqs[0]["id"])[0]
    assert ev["confianca"] == 0.5 and len(ev["speaker"]) <= 200
    assert store.listar_evidencias(c, reqs[1]["id"])[0]["confianca"] == 1.0


@pytest.mark.asyncio
async def test_reforcos_repetidos_na_mesma_rodada_contam_uma_vez():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    r2 = _reuniao(c, "sessao-0002")
    rf = Reforco(codigo="RQ-001", trecho="mais uma menção ao PDF")
    contagens = await analise.analisar_reuniao(c, r2["id"], executar=_executor(SaidaAnalise(reforcos=[rf, rf])), obter_chave=lambda: "k")
    assert contagens["reforcos"] == 1


@pytest.mark.asyncio
async def test_colisao_de_codigo_tem_retentativa_limitada_e_falha_limpa(monkeypatch):
    c = _cliente()
    r = _reuniao(c)
    chamadas = []

    def sempre_colide(client, dados):
        chamadas.append(dados["codigo"])
        raise RuntimeError("duplicate key SEGREDO-XYZ")
    monkeypatch.setattr(store, "inserir_requisito", sempre_colide)
    contagens = await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    assert contagens["novos"] == 0
    assert len(chamadas) == analise.MAX_TENTATIVAS_CODIGO
    linha = store.buscar_reuniao(c, r["id"])
    assert linha["analise_status"] == "falhou" and "SEGREDO" not in (linha["analise_erro"] or "")


@pytest.mark.asyncio
async def test_colisao_unica_e_resolvida_recalculando_o_codigo(monkeypatch):
    c = _cliente()
    r = _reuniao(c)
    original = store.inserir_requisito
    estado = {"n": 0}

    def colide_uma_vez(client, dados):
        estado["n"] += 1
        if estado["n"] == 1:
            original(client, {**dados, "titulo": "Concorrente que ocupou o código"})  # outro processo pegou RQ-001
            raise RuntimeError("unique violation")
        return original(client, dados)
    monkeypatch.setattr(store, "inserir_requisito", colide_uma_vez)
    await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    assert sorted(q["codigo"] for q in store.listar_requisitos(c, "p1")) == ["RQ-001", "RQ-002"]
    assert store.buscar_reuniao(c, r["id"])["analise_status"] == "ok"


@pytest.mark.asyncio
async def test_segundo_plano_nunca_levanta(monkeypatch):
    def quebra():
        raise RuntimeError("sem banco")
    monkeypatch.setattr(analise, "get_client", quebra)
    await analise.analisar_em_segundo_plano("x")
    await analise.reconsolidar_em_segundo_plano("p1")


# ---- rodada de correções 1 ----
@pytest.mark.asyncio
@pytest.mark.parametrize("novo_status", ["validado", "rejeitado"])
async def test_status_mudando_durante_a_chamada_ao_modelo_bloqueia_o_ajuste(novo_status):
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    req = store.listar_requisitos(c, "p1")[0]
    r2 = _reuniao(c, "sessao-0002")
    transicoes_antes = len(store.listar_transicoes(c, req["id"]))

    async def valida_no_meio(**_):
        store.atualizar_requisito(c, req["id"], {"status": novo_status})  # pessoa decide durante a chamada
        return SaidaAnalise(ajustes_prioridade=[AjustePrioridade(codigo="RQ-001", prioridade="wont", justificativa="x")])
    contagens = await analise.analisar_reuniao(c, r2["id"], executar=valida_no_meio, obter_chave=lambda: "k")
    depois = store.buscar_requisito(c, req["id"])
    assert depois["status"] == novo_status and depois["prioridade_sugerida"] == "must"
    assert contagens["ajustes"] == 0
    assert len(store.listar_transicoes(c, req["id"])) == transicoes_antes


@pytest.mark.asyncio
async def test_reconsolidar_tres_vezes_com_o_mesmo_novo_gera_um_requisito():
    c = _cliente()
    r = _reuniao(c)
    ex = _executor(SaidaAnalise(novos=[_novo()]))
    await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    await analise.reconsolidar_projeto(c, "p1", executar=ex, obter_chave=lambda: "k")
    contagens = await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    assert contagens["novos"] == 0 and contagens["duplicatas"] == 0
    reqs = store.listar_requisitos(c, "p1")
    assert [(q["codigo"], q["status"]) for q in reqs] == [("RQ-001", "proposto")]


@pytest.mark.asyncio
async def test_requisito_orfao_da_mesma_reuniao_e_reaproveitado(monkeypatch):
    c = _cliente()
    r = _reuniao(c)
    ex = _executor(SaidaAnalise(novos=[_novo()]))

    def evidencia_falha(*a, **k):
        raise RuntimeError("queda")
    original = store.inserir_evidencia
    monkeypatch.setattr(store, "inserir_evidencia", evidencia_falha)
    await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")  # deixa órfão
    monkeypatch.setattr(store, "inserir_evidencia", original)
    await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    reqs = store.listar_requisitos(c, "p1")
    assert len(reqs) == 1 and len(store.listar_evidencias(c, reqs[0]["id"])) == 1
    assert store.buscar_reuniao(c, r["id"])["analise_status"] == "ok"


@pytest.mark.asyncio
async def test_reconsolidar_continua_apos_falha_e_conta_so_sucessos():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    r2 = _reuniao(c, "sessao-0002")
    chamadas = []

    async def falha_na_primeira(**kw):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("x")
        return SaidaAnalise()
    total = await analise.reconsolidar_projeto(c, "p1", executar=falha_na_primeira, obter_chave=lambda: "k")
    assert total == 1 and len(chamadas) == 2
    assert {store.buscar_reuniao(c, r["id"])["analise_status"] for r in (r1, r2)} == {"falhou", "ok"}


@pytest.mark.asyncio
async def test_reconsolidar_ordena_por_ocorrida_em_e_created_at():
    c = _cliente()
    ordem = []
    a = _reuniao(c, "sessao-000A")
    b = _reuniao(c, "sessao-000B")
    for linha, (oc, cr) in zip((a, b), (("2026-02-01", "1"), ("2026-01-01", "2"))):
        for t in c.tables["discovery_reunioes"]:
            if t["id"] == linha["id"]:
                t["ocorrida_em"], t["created_at"] = oc, cr

    async def ex(**kw):
        ordem.append(kw["fonte"])
        return SaidaAnalise()
    for t in c.tables["discovery_reunioes"]:
        t["conteudo_estruturado"] = {"resumo": t["id"]}
    await analise.reconsolidar_projeto(c, "p1", executar=ex, obter_chave=lambda: "k")
    assert b["id"] in ordem[0]  # 2026-01-01 vem antes
    assert a["id"] in ordem[1]  # 2026-02-01 depois


@pytest.mark.asyncio
async def test_novo_com_trecho_vazio_e_ignorado():
    c = _cliente()
    r = _reuniao(c)
    n = _novo().model_copy(update={"trecho": "   "})
    contagens = await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[n])), obter_chave=lambda: "k")
    assert contagens["novos"] == 0 and store.listar_requisitos(c, "p1") == []


@pytest.mark.asyncio
async def test_erro_que_nao_e_de_unicidade_nao_e_retentado(monkeypatch):
    c = _cliente()
    r = _reuniao(c)
    chamadas = []

    def falha(client, dados):
        chamadas.append(1)
        raise RuntimeError("conexão caiu")
    monkeypatch.setattr(store, "inserir_requisito", falha)
    await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    assert len(chamadas) == 1
    assert store.buscar_reuniao(c, r["id"])["analise_status"] == "falhou"


# ---- rodada de correções 2 ----
@pytest.mark.asyncio
async def test_reanalise_com_empate_de_titulo_nao_multiplica_requisitos():
    c = _cliente()
    r1 = _reuniao(c, "sessao-0001")
    await analise.analisar_reuniao(c, r1["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    r2 = _reuniao(c, "sessao-0002")
    ex = _executor(SaidaAnalise(novos=[_novo(trecho="o relatório em PDF é essencial")]))
    for _ in range(3):
        await analise.analisar_reuniao(c, r2["id"], executar=ex, obter_chave=lambda: "k")
    reqs = store.listar_requisitos(c, "p1")
    assert [(q["codigo"], q["status"]) for q in reqs] == [("RQ-001", "proposto"), ("RQ-002", "em_revisao")]
    assert reqs[1]["possivel_duplicata_de"] == reqs[0]["id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["validado", "rejeitado"])
async def test_candidato_decidido_sem_evidencia_nao_e_absorvido(status):
    c = _cliente()
    r = _reuniao(c)
    decidido = store.inserir_requisito(c, {
        "project_id": "p1", "codigo": "RQ-001", "titulo": "Exportar relatório em PDF", "tipo": "funcional",
        "prioridade_sugerida": "must", "status": status, "conflito": False, "validado_por": "ana"})
    antes = dict(store.buscar_requisito(c, decidido["id"]))
    contagens = await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    assert contagens["novos"] == 1 and contagens["duplicatas"] == 1
    assert store.buscar_requisito(c, decidido["id"]) == antes
    assert store.listar_transicoes(c, decidido["id"]) == [] and store.listar_evidencias(c, decidido["id"]) == []
    novo = [q for q in store.listar_requisitos(c, "p1") if q["codigo"] == "RQ-002"][0]
    assert novo["status"] == "em_revisao" and novo["possivel_duplicata_de"] == decidido["id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["proposto", "em_revisao"])
async def test_orfao_legitimo_e_reaproveitado_com_o_status_real(status):
    c = _cliente()
    r = _reuniao(c)
    orfao = store.inserir_requisito(c, {
        "project_id": "p1", "codigo": "RQ-001", "titulo": "Exportar relatório em PDF", "tipo": "funcional",
        "prioridade_sugerida": "must", "status": status, "conflito": False})
    await analise.analisar_reuniao(c, r["id"], executar=_executor(SaidaAnalise(novos=[_novo()])), obter_chave=lambda: "k")
    assert len(store.listar_requisitos(c, "p1")) == 1
    assert len(store.listar_evidencias(c, orfao["id"])) == 1
    tr = store.listar_transicoes(c, orfao["id"])
    assert [(t["de"], t["para"]) for t in tr] == [("", status)]


@pytest.mark.asyncio
async def test_reconsolidar_poe_reuniao_sem_data_por_ultimo():
    c = _cliente()
    sem_data = _reuniao(c, "sessao-000A")
    com_data = _reuniao(c, "sessao-000B")
    for t in c.tables["discovery_reunioes"]:
        t["ocorrida_em"] = "2026-01-01" if t["id"] == com_data["id"] else None
        t["conteudo_estruturado"] = {"resumo": t["id"]}
    ordem = []

    async def ex(**kw):
        ordem.append(kw["fonte"])
        return SaidaAnalise()
    await analise.reconsolidar_projeto(c, "p1", executar=ex, obter_chave=lambda: "k")
    assert com_data["id"] in ordem[0] and sem_data["id"] in ordem[1]


# ---- janelas de análise (revisão final, I2) ----
from graphs.requisitos_graph import FONTE_MAX_CHARS, validar_saida  # noqa: E402
from services import discovery_fonte  # noqa: E402


def _transcricao_longa(linhas_de=1000, total=70_000, final="Marina: precisamos de SSO corporativo no fim da reunião"):
    linhas, usado = [], 0
    while usado < total:
        linha = "Davi: " + "conversa sem relevância " * 3
        linhas.append(linha[:linhas_de])
        usado += len(linha) + 1
    return "\n".join(linhas) + "\n" + final


@pytest.mark.asyncio
async def test_transcricao_longa_tem_a_evidencia_do_fim_na_janela_2():
    c = _cliente()
    final = "Marina: precisamos de SSO corporativo no fim da reunião"
    r = _reuniao(c, transcricao=_transcricao_longa(final=final))
    fontes = []

    async def ex(**kw):
        fontes.append(kw["fonte"])
        if final in kw["fonte"]:
            return SaidaAnalise(novos=[_novo("SSO corporativo", final)])
        return SaidaAnalise()
    contagens = await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    assert len(fontes) == 2 and all(len(f) <= FONTE_MAX_CHARS for f in fontes)
    assert final not in fontes[0] and "cliente quer exportar PDF" in fontes[0]  # estruturado antes, na janela 1
    assert contagens["novos"] == 1
    req = store.listar_requisitos(c, "p1")[0]
    assert store.listar_evidencias(c, req["id"])[0]["trecho"] == final
    linha = store.buscar_reuniao(c, r["id"])
    assert linha["analise_status"] == "ok" and linha["analise_erro"] is None


def test_estruturado_citado_como_evidencia_e_aceito_pela_validacao():
    reuniao = {"conteudo_estruturado": {"resumo": "cliente quer exportar relatórios em PDF"}}
    janelas, truncada = discovery_fonte.janelas_da_fonte(reuniao, "Marina: bom dia a todos e todas")
    assert truncada is False and "cliente quer exportar relatórios em PDF" in janelas[0]
    novo = _novo("Exportar PDF", "cliente quer exportar relatórios em PDF")
    saida = validar_saida(SaidaAnalise(novos=[novo]), fonte=janelas[0], existentes={})
    assert len(saida.novos) == 1


@pytest.mark.asyncio
async def test_mais_de_quatro_janelas_marca_analise_parcial():
    c = _cliente()
    r = _reuniao(c, transcricao=_transcricao_longa(total=FONTE_MAX_CHARS * 5))
    chamadas = []

    async def ex(**kw):
        chamadas.append(1)
        return SaidaAnalise()
    await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    assert len(chamadas) == discovery_fonte.MAX_JANELAS == 4
    linha = store.buscar_reuniao(c, r["id"])
    assert linha["analise_status"] == "ok"
    assert linha["analise_erro"] == "análise parcial: transcrição excede o limite analisado"


@pytest.mark.asyncio
async def test_reanalise_de_reuniao_longa_tres_vezes_e_idempotente():
    c = _cliente()
    final = "Marina: precisamos de SSO corporativo no fim da reunião"
    r = _reuniao(c, transcricao=_transcricao_longa(final=final))

    async def ex(**kw):
        return SaidaAnalise(novos=[_novo("SSO corporativo", final)]) if final in kw["fonte"] else SaidaAnalise()
    for _ in range(3):
        store.marcar_analise(c, r["id"], "pendente")
        await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    assert len(store.listar_requisitos(c, "p1")) == 1


@pytest.mark.asyncio
async def test_falha_na_janela_2_marca_falhou_sem_vazar_texto():
    c = _cliente()
    r = _reuniao(c, transcricao=_transcricao_longa())
    chamadas = []

    async def ex(**kw):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise RuntimeError("trecho da transcrição SEGREDO-XYZ")
        return SaidaAnalise()
    await analise.analisar_reuniao(c, r["id"], executar=ex, obter_chave=lambda: "k")
    linha = store.buscar_reuniao(c, r["id"])
    assert linha["analise_status"] == "falhou" and "SEGREDO" not in (linha["analise_erro"] or "")


def test_janelas_cortam_em_fronteira_de_linha():
    reuniao = {"conteudo_estruturado": {}}
    texto = "\n".join(f"linha {i:05d} " + "x" * 90 for i in range(1500))
    janelas, _ = discovery_fonte.janelas_da_fonte(reuniao, texto)
    assert len(janelas) == 3 and all(j.endswith("\n") for j in janelas[:-1])
    assert "".join(janelas) == discovery_fonte.texto_da_reuniao(reuniao, texto)
