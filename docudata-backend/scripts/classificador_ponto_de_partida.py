"""Ponto de partida do classificador (Rodada A2): transforma as tasks já
concluídas em exemplos de aprendizado (tempo limpo, embedding, sinais) e
recalcula tudo. Pode ser reexecutado sem duplicar; também regera embeddings
cujo modelo difere do EMBED_MODELO atual (trocar o modelo = mudar o env e
rodar de novo). Não imprime segredos nem mensagens de exceção. Uso:
    cd <pasta com o .env>/docudata-backend && python3 <caminho>/scripts/classificador_ponto_de_partida.py [--limite N]
O .env vem de ENV_FILE (se definido) ou é procurado a partir do diretório atual."""
import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphs import classificacao_graph as grafo  # noqa: E402
from services import classificador_busca as busca  # noqa: E402
from services.classificador_aprendizado import recalcular_tudo  # noqa: E402
from services.classificador_regua import SINAIS, texto_da_task  # noqa: E402
from services.classificador_tempo import tempo_limpo  # noqa: E402
from services.regua import converter_pontos_legado  # noqa: E402
from services.supabase_paginacao import ler_tudo  # noqa: E402

_PROGRESSO_A_CADA = 25


async def _sinais(api_key: str, texto: str) -> dict | None:
    """{sinal: nota} com evidência validada; None quando o modelo falha."""
    try:
        s = await grafo._invocar_sinais(api_key, grafo.montar_mensagens_sinais(texto))
        if not isinstance(s, grafo.SaidaSinais):
            return None
    except Exception as exc:  # noqa: BLE001 — só o nome da classe, nunca a mensagem
        print(f"  sinais falhou: {type(exc).__name__}")
        return None
    notas = grafo.validar_notas_sinais(s, texto)
    return {n: notas[n]["nota"] for n in SINAIS}


async def _embedar(client, api_key: str, task_id: str, texto: str) -> bool:
    try:
        vetor = await busca.gerar_embedding(api_key, texto)
        busca.salvar_embedding(client, task_id, texto, vetor)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  embedding falhou: {type(exc).__name__}")
        return False


async def processar(client, api_key: str, *, limite: int | None = None) -> dict:
    concluidas = ler_tudo(lambda: client.table("tasks").select("*").eq("coluna_kanban", "concluida").order("id"))
    com_exemplo = {r["task_id"] for r in ler_tudo(lambda: client.table("task_aprendizado").select("task_id").order("task_id"))}
    modelos = {r["task_id"]: r.get("modelo") for r in ler_tudo(lambda: client.table("task_embeddings").select("task_id, modelo").order("task_id"))}

    pendentes = [t for t in concluidas if t["id"] not in com_exemplo or modelos.get(t["id"]) != busca.EMBED_MODELO]
    if limite is not None:
        pendentes = pendentes[:limite]

    cont = {"processadas": 0, "puladas": 0, "falhas": 0, "reembedadas": 0}
    for i, task in enumerate(pendentes, 1):
        if i % _PROGRESSO_A_CADA == 0:
            print(f"progresso: {i}/{len(pendentes)} {cont}")
        texto = texto_da_task(task.get("titulo") or "", task.get("descricao"), task.get("checklist"))
        novo = task["id"] not in com_exemplo
        if novo:
            transicoes = ler_tudo(
                lambda: client.table("task_transicoes").select("campo, de, para, timestamp, bloqueio_tipo")
                .eq("task_id", task["id"]).order("timestamp")
            )
            tempo = tempo_limpo(transicoes, task)
            if tempo is None:
                cont["puladas"] += 1
                continue
        if not await _embedar(client, api_key, task["id"], texto):
            cont["falhas"] += 1
        elif not novo:
            cont["reembedadas"] += 1
        if not novo:
            continue
        sinais = await _sinais(api_key, texto)
        if sinais is None:
            cont["falhas"] += 1
        client.table("task_aprendizado").upsert({
            "task_id": task["id"],
            "classificacao_id": None,
            "nivel_sugerido": converter_pontos_legado(task.get("pontos") or 1),
            "operacional_id": task.get("operacional_id"),
            "gerente_id": None,
            "opiniao_operacional": None,
            "sinais": sinais,
            "tempo_bruto_s": tempo["tempo_bruto_s"],
            "tempo_limpo_s": tempo["tempo_limpo_s"],
            "reaberta": tempo["reaberta"],
            "concluida_em": tempo["concluida_em"],
        }, on_conflict="task_id").execute()
        cont["processadas"] += 1

    recalcular_tudo(client)
    return cont


def main() -> int:
    from dotenv import find_dotenv, load_dotenv

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limite", type=int, default=None, help="máximo de tasks a tratar nesta execução")
    args = ap.parse_args()

    env = os.environ.get("ENV_FILE") or find_dotenv(usecwd=True)
    if not env:
        print("aviso: nenhum .env encontrado")
    load_dotenv(env or None)

    from services.gemini_key import get_gemini_api_key
    from services.supabase_client import get_client

    try:
        client = get_client()
        api_key = get_gemini_api_key()
        resultado = asyncio.run(processar(client, api_key, limite=args.limite))
    except Exception as exc:  # noqa: BLE001
        print(f"FALHOU: {type(exc).__name__}")
        return 1
    print(f"concluído: {resultado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
