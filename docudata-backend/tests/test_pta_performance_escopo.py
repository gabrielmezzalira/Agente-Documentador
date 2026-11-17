from tests.test_performance_endpoint import _LINHA, _client_as, _mock_client


def _cenario():
    return _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Bia", "email": "bia@citi.com", "ativo": True, "project_id": "proj-pta"},
        ],
        pontuacao=[
            dict(_LINHA, operacional_id="op-1", projeto_id="proj-1"),
            dict(_LINHA, operacional_id="op-2", projeto_id="proj-pta"),
        ],
        projetos=[
            {"id": "proj-1", "arquetipo": "padrao", "name": "Projeto CITi", "subarea": "dados"},
            {"id": "proj-pta", "arquetipo": "padrao", "name": "PTA 2026", "subarea": "pta"},
        ],
    )


def test_padrao_e_citi_e_exclui_pta(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    r = tc.get("/performance")
    assert r.status_code == 200
    assert [p["projeto_id"] for p in r.json()["projetos"]] == ["proj-1"]


def test_escopo_pta_so_traz_projetos_pta(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    r = tc.get("/performance?escopo=pta")
    assert r.status_code == 200
    assert [p["projeto_id"] for p in r.json()["projetos"]] == ["proj-pta"]


def test_escopo_citi_explicito_igual_ao_padrao(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    r = tc.get("/performance?escopo=citi")
    assert [p["projeto_id"] for p in r.json()["projetos"]] == ["proj-1"]


def test_escopo_invalido_422(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    assert tc.get("/performance?escopo=todos").status_code == 422


def test_projeto_sem_subarea_conta_como_citi(monkeypatch):
    client = _mock_client(
        operacionais=[{"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"}],
        pontuacao=[dict(_LINHA, operacional_id="op-1", projeto_id="proj-1")],
        projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Legado"}],
    )
    tc = _client_as(monkeypatch, client, "lider")
    assert [p["projeto_id"] for p in tc.get("/performance").json()["projetos"]] == ["proj-1"]
    assert tc.get("/performance?escopo=pta").json()["projetos"] == []
