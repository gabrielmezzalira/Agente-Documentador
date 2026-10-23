# docudata-backend/scripts/spike_embedding.py
"""Teste rápido (Rodada A2): qual modelo de embedding do Gemini responde com
a chave global atual e com que dimensão. Não grava nada. Uso:
    cd <pasta com o .env>/docudata-backend && python3 <caminho>/scripts/spike_embedding.py
O .env vem de ENV_FILE (se definido) ou é procurado a partir do diretório atual.
Precisa de SUPABASE_URL, SUPABASE_SERVICE_KEY e DOCUDATA_SECRETS_KEY no ambiente."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import find_dotenv, load_dotenv

_env = os.environ.get("ENV_FILE") or find_dotenv(usecwd=True)
if not _env:
    print("aviso: nenhum .env encontrado")
load_dotenv(_env or None)

from langchain_google_genai import GoogleGenerativeAIEmbeddings  # noqa: E402

from services.gemini_key import get_gemini_api_key  # noqa: E402

CANDIDATOS = ["models/gemini-embedding-001", "models/text-embedding-004"]
TEXTO = "Criar endpoint de login com JWT e tela de autenticação"


def main() -> int:
    try:
        chave = get_gemini_api_key()
    except Exception as exc:  # noqa: BLE001 — nunca imprime a mensagem (pode conter segredo)
        print(
            f"FALHOU ao obter a chave: {type(exc).__name__}. "
            "Dica: defina SUPABASE_URL, SUPABASE_SERVICE_KEY e DOCUDATA_SECRETS_KEY (ou ENV_FILE)"
        )
        return 1
    for modelo in CANDIDATOS:
        # embed_query aceita output_dimensionality (langchain-google-genai 4.1.1);
        # o construtor não tem campo de dimensão, então o fallback é sem dimensão.
        for dim in (768, None):
            try:
                emb = GoogleGenerativeAIEmbeddings(model=modelo, google_api_key=chave)
                vetor = (
                    emb.embed_query(TEXTO, output_dimensionality=dim)
                    if dim
                    else emb.embed_query(TEXTO)
                )
                print(f"OK modelo={modelo} dim_pedida={dim} dim_recebida={len(vetor)}")
                return 0
            except Exception as exc:  # noqa: BLE001 — é um teste exploratório
                msg = str(exc)
                if chave:
                    msg = msg.replace(chave, "***")
                print(f"FALHOU modelo={modelo} dim={dim}: {type(exc).__name__}: {msg[:200]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
