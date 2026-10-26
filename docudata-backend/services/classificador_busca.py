"""Embeddings das tasks e busca de tasks concluídas parecidas (pgvector)."""
import asyncio
import hashlib
import math
import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from services.classificador_regua import IDX, K_PARECIDAS

EMBED_MODELO = os.environ.get("CLASSIFICADOR_EMBED_MODELO", "models/gemini-embedding-001")
EMBED_DIM = 768


def _vetor_str(vetor: list[float]) -> str:
    """PostgREST/pgvector esperam o vetor como string '[x,y,...]', nunca lista."""
    if not all(math.isfinite(x) for x in vetor):
        raise ValueError("Embedding contém valores não finitos (NaN/inf)")
    return "[" + ",".join(repr(float(x)) for x in vetor) + "]"


def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


async def gerar_embedding(api_key: str, texto: str) -> list[float]:
    emb = GoogleGenerativeAIEmbeddings(model=EMBED_MODELO, google_api_key=api_key)
    vetor = await asyncio.to_thread(emb.embed_query, texto, output_dimensionality=EMBED_DIM)
    if len(vetor) != EMBED_DIM:
        raise ValueError(f"Embedding com {len(vetor)} dimensões; esperado {EMBED_DIM}")
    return list(vetor)


def salvar_embedding(client, task_id: str, texto: str, vetor: list[float]) -> None:
    h = hash_texto(texto)
    atual = client.table("task_embeddings").select("hash_texto,modelo").eq("task_id", task_id).execute().data or []
    if atual and atual[0].get("hash_texto") == h and atual[0].get("modelo") == EMBED_MODELO:
        return
    client.table("task_embeddings").upsert(
        {"task_id": task_id, "embedding": _vetor_str(vetor), "hash_texto": h, "modelo": EMBED_MODELO},
        on_conflict="task_id",
    ).execute()


def buscar_parecidas(client, vetor: list[float], k: int = K_PARECIDAS) -> list[dict]:
    achadas = client.rpc("buscar_tasks_parecidas", {"consulta": _vetor_str(vetor), "n": k}).execute().data or []
    if not achadas:
        return []
    ids = [a["task_id"] for a in achadas]
    linhas = (
        client.table("task_aprendizado")
        .select("task_id,nivel_real,tempo_normalizado_s")
        .in_("task_id", ids)
        .execute()
        .data
        or []
    )
    por_id = {r["task_id"]: r for r in linhas}
    saida = []
    for a in achadas:
        r = por_id.get(a["task_id"])
        if r is None:
            continue
        saida.append({
            "task_id": a["task_id"],
            "similaridade": a["similaridade"],
            "nivel_real": r["nivel_real"],
            "tempo_normalizado_s": r["tempo_normalizado_s"],
        })
    return saida


def nivel_das_parecidas(parecidas: list[dict]) -> float | None:
    """Média do nível (em degraus) ponderada pela similaridade; similaridade <= 0 não conta."""
    pesos = [(p["similaridade"], IDX[p["nivel_real"]]) for p in parecidas if p["similaridade"] > 0]
    total = sum(w for w, _ in pesos)
    if total <= 0:
        return None
    return sum(w * i for w, i in pesos) / total
