#!/usr/bin/env python3
"""
DocuData Aceite Agent — roda suíte de gates e reporta resultados ao DocuData.

Instalação no repositório do projeto:
  mkdir -p .github/workflows scripts
  cp aceite_agent.py scripts/aceite_agent.py
  cp aceite.yml .github/workflows/aceite.yml
  git add .github/workflows/aceite.yml scripts/aceite_agent.py
  git commit -m "chore: adicionar DocuData aceite"

Secrets necessários no repositório do projeto (GitHub Secrets):
  DOCUDATA_API_URL  — ex: https://docudata-backend.railway.app

As variáveis FUNCIONALIDADE_ID, PROJECT_ID e TESTES_E2E são injetadas
automaticamente pelo workflow aceite.yml via github.event.client_payload.

IMPORTANTE: aceite.yml deve estar no default branch (main/master) do repo
do projeto para que repository_dispatch funcione (ver Pitfall 2 do RESEARCH).

Este agente é propositalmente best-effort: nunca falha o CI do projeto.
"""
import os
import subprocess
import json
import urllib.request
import urllib.error

API_URL           = os.environ.get("DOCUDATA_API_URL", "").rstrip("/")
FUNCIONALIDADE_ID = os.environ.get("FUNCIONALIDADE_ID", "")
PROJECT_ID        = os.environ.get("PROJECT_ID", "")
TESTES_E2E_JSON   = os.environ.get("TESTES_E2E", "[]")

# Guard: sem configuração mínima, encerrar silenciosamente
if not API_URL or not FUNCIONALIDADE_ID:
    print("[aceite] Aviso: DOCUDATA_API_URL ou FUNCIONALIDADE_ID não configurado — continuando")
    raise SystemExit(0)


def run_cmd(cmd: list) -> tuple:
    """Roda comando com timeout, retorna (returncode, stdout+stderr)."""
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


def gate_resultado(cmd) -> str:
    """Executa gate e mapeia resultado para passou|falhou|erro|sem_cobertura."""
    if cmd is None:
        return "sem_cobertura"
    try:
        rc, _ = run_cmd(cmd)
        return "passou" if rc == 0 else "falhou"
    except Exception as e:
        print(f"[aceite] Aviso: gate com erro ({e})")
        return "erro"


# Obter commit SHA do HEAD atual do repo do projeto (per RESEARCH Pitfall 3)
# Não usar GITHUB_SHA — em repository_dispatch aponta para o DocuData, não o repo do projeto
commit_sha = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    capture_output=True,
    text=True,
).stdout.strip() or "unknown"

# Detectar runtime (heurística best-effort)
has_package_json = os.path.exists("package.json")
has_requirements = os.path.exists("requirements.txt") or os.path.exists("pyproject.toml")

# Parsear lista de testes E2E (passada como JSON pelo workflow)
try:
    testes_e2e = json.loads(TESTES_E2E_JSON) if TESTES_E2E_JSON else []
    if not isinstance(testes_e2e, list):
        testes_e2e = []
except (json.JSONDecodeError, ValueError):
    testes_e2e = []

# Construir lista de gates (5 fixos per D-04)
gates = [
    {
        "nome": "build",
        "resultado": gate_resultado(
            ["npm", "run", "build"] if has_package_json
            else ["pip", "install", "-e", "."] if has_requirements
            else None
        ),
    },
    {
        "nome": "testes_unitarios",
        "resultado": gate_resultado(
            ["npm", "test", "--", "--watchAll=false"] if has_package_json
            else ["pytest", "--tb=short", "-q"] if has_requirements
            else None
        ),
    },
    {
        "nome": "e2e",
        "resultado": (
            "sem_cobertura" if not testes_e2e
            else gate_resultado(["python", "-m", "pytest"] + testes_e2e)
        ),
    },
    {
        "nome": "acessibilidade",
        "resultado": "sem_cobertura",  # MVP — ferramenta não detectada
    },
    {
        "nome": "performance",
        "resultado": "sem_cobertura",  # MVP — ferramenta não detectada
    },
]

# Reportar resultados ao DocuData via urllib.request (stdlib only)
payload = {
    "funcionalidade_id": FUNCIONALIDADE_ID,
    "commit_sha": commit_sha,
    "gates": gates,
}
body = json.dumps(payload).encode()
req = urllib.request.Request(
    f"{API_URL}/ingest/aceite",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[aceite] Resultado registrado — HTTP {r.status}")
except urllib.error.HTTPError as e:
    print(f"[aceite] Aviso: falha ao registrar (HTTP {e.code}) — continuando")
except (urllib.error.URLError, TimeoutError, OSError) as e:
    print(f"[aceite] Aviso: falha ao registrar ({e}) — continuando")
