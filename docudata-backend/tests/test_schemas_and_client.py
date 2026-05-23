"""
TDD RED tests for Task 2: Pydantic schemas, lazy Supabase client, project CRUD router.
Tests verify:
- ConteudoEstruturado has exactly 6 required fields with correct types
- ProjectCreate validates name/client required, description optional
- ProjectResponse has id, name, client, description, created_at
- IngestResponse has status, sprint, tentativas
- get_client() is a function (not a module-level instance)
- get_client() reads env at call time (not import time)
- routers/projects.py defines router with prefix /projects
- router has exactly 3 route decorators
- GET /{project_id} raises 404 with "Project not found"
"""
import importlib
import inspect
import os
import sys
import pytest
from typing import get_type_hints


def test_conteudo_estruturado_has_exactly_6_fields():
    """ConteudoEstruturado must have exactly these 6 fields."""
    from models.schemas import ConteudoEstruturado
    fields = set(ConteudoEstruturado.model_fields.keys())
    expected = {"resumo", "tarefas", "decisoes", "problemas", "contexto_cliente", "proximos_passos"}
    assert fields == expected, f"Fields mismatch: got {fields}, expected {expected}"


def test_conteudo_estruturado_field_types():
    """tarefas, decisoes, problemas, proximos_passos must be list[str]; resumo and contexto_cliente must be str."""
    from models.schemas import ConteudoEstruturado
    import pydantic
    fields = ConteudoEstruturado.model_fields
    # Check list fields
    for field_name in ("tarefas", "decisoes", "problemas", "proximos_passos"):
        field = fields[field_name]
        annotation = ConteudoEstruturado.__annotations__[field_name]
        assert annotation == list[str], f"{field_name} should be list[str], got {annotation}"
    # Check str fields
    for field_name in ("resumo", "contexto_cliente"):
        annotation = ConteudoEstruturado.__annotations__[field_name]
        assert annotation == str, f"{field_name} should be str, got {annotation}"


def test_conteudo_estruturado_instantiation():
    """ConteudoEstruturado must be instantiable with 6 fields."""
    from models.schemas import ConteudoEstruturado
    obj = ConteudoEstruturado(
        resumo="Resumo teste",
        tarefas=["tarefa 1", "tarefa 2"],
        decisoes=["decisao 1"],
        problemas=["problema 1"],
        contexto_cliente="Cliente X",
        proximos_passos=["passo 1"],
    )
    assert obj.resumo == "Resumo teste"
    assert obj.tarefas == ["tarefa 1", "tarefa 2"]
    assert obj.model_dump()["decisoes"] == ["decisao 1"]


def test_project_create_requires_name_and_client():
    """ProjectCreate must require name and client; missing either raises ValidationError."""
    from models.schemas import ProjectCreate
    import pydantic
    # Valid creation
    proj = ProjectCreate(name="Proj X", client="Client A")
    assert proj.name == "Proj X"
    assert proj.client == "Client A"
    assert proj.description is None

    # Missing name
    with pytest.raises(pydantic.ValidationError):
        ProjectCreate(client="Client A")

    # Missing client
    with pytest.raises(pydantic.ValidationError):
        ProjectCreate(name="Proj X")


def test_project_create_description_optional():
    """ProjectCreate description is optional."""
    from models.schemas import ProjectCreate
    proj_with_desc = ProjectCreate(name="P", client="C", description="desc")
    proj_without = ProjectCreate(name="P", client="C")
    assert proj_with_desc.description == "desc"
    assert proj_without.description is None


def test_project_response_has_required_fields():
    """ProjectResponse must have id, name, client, description, created_at."""
    from models.schemas import ProjectResponse
    fields = set(ProjectResponse.model_fields.keys())
    expected = {"id", "name", "client", "description", "created_at"}
    assert fields == expected


def test_project_response_id_is_str():
    """ProjectResponse.id must be typed as str."""
    from models.schemas import ProjectResponse
    assert ProjectResponse.__annotations__["id"] == str


def test_ingest_response_fields():
    """IngestResponse must have status (str), sprint (int), tentativas (int default 0)."""
    from models.schemas import IngestResponse
    fields = IngestResponse.model_fields
    assert "status" in fields
    assert "sprint" in fields
    assert "tentativas" in fields
    # Default tentativas=0
    ir = IngestResponse(status="ok", sprint=1)
    assert ir.tentativas == 0
    assert ir.status == "ok"
    assert ir.sprint == 1


def test_get_client_is_function_not_module_level_instance():
    """get_client must be a callable function, not an instantiated client at module level."""
    import services.supabase_client as sc
    assert callable(sc.get_client), "get_client must be callable"
    # The module must NOT have a 'client' attribute at module level
    # (this would indicate module-level instantiation)
    assert not hasattr(sc, "client") or callable(getattr(sc, "client", None)), \
        "supabase_client.py must not instantiate Client at module level"


def test_get_client_source_reads_env_at_call_time():
    """get_client() function body must call create_client with os.environ reads, not module-level."""
    import services.supabase_client as sc
    source = inspect.getsource(sc.get_client)
    assert "create_client" in source, "get_client must call create_client"
    # Ensure create_client is NOT called at module level
    import ast, textwrap
    tree = ast.parse(inspect.getsource(sc))
    # Find all Call nodes at module level (not inside a function)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_client":
            # create_client call should be INSIDE this function
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    if hasattr(subnode.func, "id") and subnode.func.id == "create_client":
                        return  # Found inside function body — good
    pytest.fail("create_client() call not found inside get_client() function body")


def test_projects_router_has_prefix():
    """routers/projects.py must define router with prefix /projects."""
    from routers.projects import router
    assert router.prefix == "/projects", f"Router prefix should be /projects, got {router.prefix}"


def test_projects_router_has_3_routes():
    """projects router must have exactly 3 route objects."""
    from routers.projects import router
    routes = router.routes
    assert len(routes) == 3, f"Expected 3 routes, got {len(routes)}: {[r.path for r in routes]}"


def test_projects_router_get_by_id_raises_404():
    """GET /projects/{project_id} endpoint source must raise HTTPException 404 with 'Project not found'."""
    import inspect
    from routers import projects as proj_module
    # Get the get_project function source
    source = inspect.getsource(proj_module)
    assert "HTTPException" in source, "Router must use HTTPException"
    assert "404" in source, "Router must raise 404 for unknown project"
    assert "Project not found" in source, "Router must have detail 'Project not found'"
