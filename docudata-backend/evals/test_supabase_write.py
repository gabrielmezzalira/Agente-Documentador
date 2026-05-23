import pytest
from graphs.extraction_graph import salvar, ExtractionState


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeInsertBuilder:
    def __init__(self, data):
        self._data = data
        self.recorded_payload = None

    def insert(self, payload):
        self.recorded_payload = payload
        return self

    def execute(self):
        return _FakeExecuteResult(self._data)


class _FakeTable:
    def __init__(self, data):
        self._builder = _FakeInsertBuilder(data)

    def table(self, name):
        return self._builder


def _make_state(extracted_content=None) -> ExtractionState:
    return {
        "arquivo_bytes": b"",
        "arquivo_nome": "sprint3.txt",
        "mime_type": "text/plain",
        "sprint_numero": 3,
        "projeto_id": "test-project-uuid",
        "tipo": "texto",
        "texto_preprocessado": "",
        "conteudo_estruturado": extracted_content or {"resumo": "ok", "tarefas": [], "decisoes": [], "problemas": [], "contexto_cliente": "", "proximos_passos": []},
        "valido": True,
        "tentativas": 0,
        "erro": None,
    }


@pytest.mark.asyncio
async def test_salvar_success(monkeypatch):
    state = _make_state({"resumo": "done", "tarefas": ["t1"], "decisoes": [], "problemas": [], "contexto_cliente": "c", "proximos_passos": []})
    fake_table = _FakeTable(data=[{"id": "abc"}])

    monkeypatch.setattr("graphs.extraction_graph.get_client", lambda: fake_table)

    result = await salvar(state)

    assert result == {}
    payload = fake_table._builder.recorded_payload
    assert set(payload.keys()) == {"project_id", "sprint_number", "file_name", "file_type", "extracted_content"}
    assert payload["project_id"] == state["projeto_id"]
    assert payload["sprint_number"] == state["sprint_numero"]
    assert payload["file_name"] == state["arquivo_nome"]
    assert payload["file_type"] == state["tipo"]
    assert payload["extracted_content"] == state["conteudo_estruturado"]


@pytest.mark.asyncio
async def test_salvar_empty_response_reports_failure(monkeypatch):
    state = _make_state()
    fake_table = _FakeTable(data=[])

    monkeypatch.setattr("graphs.extraction_graph.get_client", lambda: fake_table)

    result = await salvar(state)

    assert result.get("valido") is False
    assert result.get("erro") and len(result["erro"]) > 0
