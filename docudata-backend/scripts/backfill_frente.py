"""Backfill da frente: classifica as tasks com `frente` nula. Sem --aplicar, só conta. Uso:
    cd <pasta com o .env>/docudata-backend && python3 <caminho>/scripts/backfill_frente.py [--aplicar]
O .env vem de ENV_FILE (se definido) ou é procurado a partir do diretório atual."""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(os.environ.get("ENV_FILE") or find_dotenv(usecwd=True) or None)

from services.frente import atualizar_frente_da_task  # noqa: E402
from services.supabase_client import get_client  # noqa: E402
from services.supabase_paginacao import ler_tudo  # noqa: E402


async def main(aplicar: bool = False, client=None, pausa: float = 0.5) -> int:
    client = client or get_client()
    tasks = ler_tudo(lambda: client.table("tasks").select("id").is_("frente", "null").order("id"))
    if not aplicar:
        print(f"simulação: {len(tasks)} tasks seriam classificadas (use --aplicar)")
        return len(tasks)
    for t in tasks:
        await atualizar_frente_da_task(t["id"])
        await asyncio.sleep(pausa)
    print(f"{len(tasks)} tasks processadas")
    return len(tasks)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    asyncio.run(main(ap.parse_args().aplicar))
