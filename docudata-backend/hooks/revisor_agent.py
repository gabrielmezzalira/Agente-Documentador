#!/usr/bin/env python3
"""
DocuData Revisor Diário
Instalação no repositório do projeto:
  mkdir -p .github/workflows scripts
  cp <caminho>/revisor_agent.py scripts/revisor_agent.py
  cp <caminho>/revisor.yml     .github/workflows/revisor.yml
  git add .github/workflows/revisor.yml scripts/revisor_agent.py
  git commit -m "chore: adicionar DocuData revisor diário"

Variáveis de ambiente (GitHub Secrets):
  DOCUDATA_API_URL      — ex: https://docudata-backend.railway.app
  DOCUDATA_PROJECT_ID   — UUID do projeto no DocuData

Este agente é propositalmente best-effort: nunca falha o CI.
Roda diariamente às 08:00 UTC (05:00 BRT) via cron do GitHub Actions.
"""
import os, subprocess, json
import urllib.request, urllib.error
from datetime import date

API_URL    = os.environ.get("DOCUDATA_API_URL", "").rstrip("/")
PROJECT_ID = os.environ.get("DOCUDATA_PROJECT_ID", "")

LIMITE_CHARS = 100_000

def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True).stdout.strip()

def http_json(url, method="GET", data=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return {}, e.code
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as e:
        print(f"[revisor] Aviso: requisição indisponível ({e}) — continuando")
        return {}, 0

if not API_URL or not PROJECT_ID:
    print("[revisor] Aviso: DOCUDATA_API_URL ou DOCUDATA_PROJECT_ID não configurado — continuando")
    raise SystemExit(0)

# 1. Listar commits das últimas 24h (excluindo merges)
commits_raw = git("log", "--since=24 hours ago", "--no-merges", "--pretty=%H|%s")

# 2. Guard: encerrar silenciosamente se não houve commits
if not commits_raw.strip():
    print("[revisor] Nenhum commit nas últimas 24h — encerrando")
    raise SystemExit(0)

# 3. Parsear linhas de commit
linhas = [l for l in commits_raw.strip().splitlines() if l.strip()]
commits = [l.split("|", 1) for l in linhas if "|" in l]
commits_analisados = len(commits)
lista_msgs = [partes[1] if len(partes) > 1 else "" for partes in commits]

# 4. Agregar diffs de cada commit
diffs = []
total_chars = 0
for hash_, _ in commits:
    diff = git("show", hash_, "--unified=3", "--no-color")
    total_chars += len(diff)
    diffs.append(diff)

diff_agregado = "\n".join(diffs)
diff_chars_total = total_chars
if len(diff_agregado) > LIMITE_CHARS:
    diff_agregado = diff_agregado[:LIMITE_CHARS] + "\n[DIFF TRUNCADO EM 100k CHARS]"

# 5. Guard adicional: diff vazio após agregação
if not diff_agregado.strip():
    print("[revisor] Diff vazio após agregação — encerrando")
    raise SystemExit(0)

# 6. Enviar ao backend
data_revisao = date.today().isoformat()
payload = {
    "project_id":        PROJECT_ID,
    "data_revisao":      data_revisao,
    "diff_agregado":     diff_agregado,
    "commits_analisados": commits_analisados,
    "diff_chars_total":  diff_chars_total,
    "lista_commits":     lista_msgs,
}
_, status = http_json(f"{API_URL}/ingest/revisao", method="POST", data=payload)

# 7. Log de resultado
if status == 201:
    print(f"[revisor] Revisão diária registrada — {commits_analisados} commits analisados")
else:
    print(f"[revisor] Aviso: falha ao registrar (HTTP {status}) — continuando")
