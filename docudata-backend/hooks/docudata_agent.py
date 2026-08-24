#!/usr/bin/env python3
"""
DocuData Commit Agent
Instalação no repositório do projeto:
  cp <caminho>/docudata_agent.py scripts/docudata_agent.py
Variáveis de ambiente (GitHub Secrets):
  DOCUDATA_API_URL      — ex: https://docudata-backend.railway.app
  DOCUDATA_PROJECT_ID   — UUID do projeto no DocuData
Este agente é propositalmente best-effort: nunca falha o processo do CI.
"""
import os, subprocess, re, json
import urllib.request, urllib.error

API_URL    = os.environ.get("DOCUDATA_API_URL", "").rstrip("/")
PROJECT_ID = os.environ.get("DOCUDATA_PROJECT_ID", "")

def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True).stdout.strip()

def http_json(url, method="GET", data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return {}, e.code
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        print(f"[docudata] Aviso: requisição indisponível ({e}) — continuando")
        return {}, 0

if not API_URL or not PROJECT_ID:
    print("[docudata] Aviso: DOCUDATA_API_URL ou DOCUDATA_PROJECT_ID não configurado — continuando")
    raise SystemExit(0)

# 1. Detectar sprint via DocuData (última planning ingerida)
sprint_data, status = http_json(f"{API_URL}/projects/{PROJECT_ID}/current-sprint")
sprint_number = sprint_data.get("sprint_number", 1) if status == 200 else 1

# 2. Verificar override [sprint:N] na mensagem do commit
commit_msg = git("log", "-1", "--pretty=%s")
override = re.search(r'\[sprint:(\d+)\]', commit_msg)
if override:
    sprint_number = int(override.group(1))
    print(f"[docudata] Sprint override detectado: Sprint {sprint_number}")
else:
    print(f"[docudata] Sprint detectada automaticamente: Sprint {sprint_number}")

# 3. Coletar metadados do commit
commit_hash  = git("log", "-1", "--pretty=%H")
author       = git("log", "-1", "--pretty=%an")
date         = git("log", "-1", "--pretty=%aI")
diff_stat    = git("diff", "HEAD~1", "HEAD", "--stat")
# Diff real truncado em 8000 chars para não estourar o contexto do Gemini
diff_full    = git("show", "HEAD", "--unified=3")[:8000]

# 4. Enviar para DocuData
payload = {
    "project_id":    PROJECT_ID,
    "sprint_number": sprint_number,
    "commit_hash":   commit_hash,
    "commit_message": commit_msg,
    "author":        author,
    "date":          date,
    "diff_stat":     diff_stat,
    "diff":          diff_full,
}
_, post_status = http_json(f"{API_URL}/ingest/commit", method="POST", data=payload)

if post_status == 201:
    print(f"[docudata] Commit {commit_hash[:7]} registrado na Sprint {sprint_number}")
else:
    print(f"[docudata] Aviso: falha ao registrar (HTTP {post_status}) — continuando")
