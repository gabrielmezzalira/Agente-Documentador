"""Backfill (Rodada B1, entrega 1): recalcula o status de todas as
funcionalidades a partir das tasks. Idempotente; não imprime segredos. Uso:
    cd <pasta com o .env>/docudata-backend && python3 <caminho>/scripts/status_funcionalidade_backfill.py [--dry-run]
O .env vem de ENV_FILE (se definido) ou é procurado a partir do diretório atual."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(os.environ.get("ENV_FILE") or find_dotenv(usecwd=True) or None)

from services.status_funcionalidade import sincronizar_status, status_derivado  # noqa: E402
from services.supabase_client import get_client  # noqa: E402
from services.supabase_paginacao import ler_tudo  # noqa: E402


def main(dry_run: bool = False, client=None) -> dict:
    client = client or get_client()
    funcs = ler_tudo(lambda: client.table("funcionalidades").select("id, status").order("id"))
    ajustadas = 0
    for f in funcs:
        if dry_run:
            tasks = client.table("tasks").select("coluna_kanban, extra").eq("funcionalidade_id", f["id"]).execute().data or []
            novo = status_derivado(tasks)
            if novo and novo != f["status"] and not (f["status"] == "em_ajuste" and novo == "em_andamento"):
                ajustadas += 1
        elif sincronizar_status(client, f["id"], "backfill"):
            ajustadas += 1
    print(f"{'simulação: ' if dry_run else ''}{ajustadas} de {len(funcs)} funcionalidades ajustadas")
    return {"ajustadas": ajustadas, "total": len(funcs)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    main(dry_run=ap.parse_args().dry_run)
