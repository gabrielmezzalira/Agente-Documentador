"""Correlação de requisições e mensagens de erro sem detalhe interno.

Toda resposta carrega um `X-Request-ID`. O corpo do erro genérico devolve o
mesmo identificador para que o usuário consiga citá-lo no suporte, enquanto o
detalhe real (tipo da exceção, rota, stack) fica apenas no log do servidor.
"""

from __future__ import annotations

import logging
import re
import traceback
import uuid
from contextvars import ContextVar, Token

from fastapi import HTTPException
from starlette.requests import Request


REQUEST_ID_HEADER = "X-Request-ID"

# Aceita o identificador do proxy/cliente só quando é curto e inofensivo:
# sem espaço, sem quebra de linha e sem caractere que permita header injection
# ou poluição do log. Qualquer coisa fora disso é substituída por um novo id.
_FORMATO_REQUEST_ID = re.compile(r"\A[A-Za-z0-9._:-]{8,64}\Z")

_LOG_REQUISICAO = logging.getLogger("docudata.request")

# ContextVar acompanha corretamente requisições concorrentes e permite que
# services/graphs registrem o mesmo request_id sem receber Request por toda a
# cadeia de chamadas.
_CONTEXTO_REQUISICAO: ContextVar[tuple[str, str, str] | None] = ContextVar(
    "docudata_contexto_requisicao", default=None
)

MENSAGEM_ERRO_INTERNO = "Erro interno no servidor. Tente novamente em instantes."


def novo_request_id() -> str:
    return uuid.uuid4().hex


def normalizar_request_id(recebido: str | None) -> str:
    """Reaproveita o id do proxy quando ele é seguro; senão gera um novo."""
    if recebido and _FORMATO_REQUEST_ID.match(recebido):
        return recebido
    return novo_request_id()


def request_id_de(request: Request) -> str:
    """Id já atribuído à requisição, ou um novo se o middleware não rodou."""
    escopo_state = request.scope.setdefault("state", {})
    request_id = escopo_state.get("request_id")
    if not request_id:
        request_id = normalizar_request_id(request.headers.get(REQUEST_ID_HEADER))
        escopo_state["request_id"] = request_id
    return request_id


def iniciar_contexto_requisicao(
    request_id: str, metodo: str, rota: str
) -> Token[tuple[str, str, str] | None]:
    """Disponibiliza metadados não sensíveis aos logs durante a requisição."""
    return _CONTEXTO_REQUISICAO.set((request_id, metodo, _rota_log_segura(rota)))


def encerrar_contexto_requisicao(
    token: Token[tuple[str, str, str] | None],
) -> None:
    _CONTEXTO_REQUISICAO.reset(token)


def _stack_sanitizada(exc: BaseException) -> str:
    """Mantém local de falha sem copiar mensagem nem linha de código.

    O formatter padrão de exceções sempre inclui `str(exc)` ao final do
    traceback. APIs externas frequentemente colocam tokens, URLs ou payloads
    nessa mensagem, então registramos apenas arquivo, linha e função.
    """
    # Mantém o log curto mesmo em exceções com cadeia profunda.
    quadros = traceback.extract_tb(exc.__traceback__)[-20:]
    if not quadros:
        return "indisponivel"
    return " > ".join(
        f"{quadro.filename.rsplit('/', 1)[-1]}:{quadro.lineno}:{quadro.name}"
        for quadro in quadros
    )


def _contexto_atual() -> tuple[str, str, str]:
    return _CONTEXTO_REQUISICAO.get() or ("fora-de-requisicao", "-", "-")


def _rota_log_segura(rota: str) -> str:
    """Evita quebra de linha/log injection sem perder a rota investigável."""
    return re.sub(r"[^A-Za-z0-9_./:{}-]", "?", rota)[:300]


def registrar_resposta(request_id: str, metodo: str, rota: str, status: int) -> None:
    """Torna qualquer X-Request-ID pesquisável sem registrar dados do cliente."""
    _LOG_REQUISICAO.info(
        "resposta request_id=%s method=%s path=%s status=%s",
        request_id,
        metodo,
        _rota_log_segura(rota),
        status,
    )


def registrar_excecao(request: Request, exc: BaseException) -> str:
    """Loga tipo da exceção + rota e devolve o request id para a resposta.

    Nunca registra corpo, cookies, headers de autorização ou o texto da
    exceção interpolado em resposta — só o suficiente para achar o erro no log.
    """
    request_id = request_id_de(request)
    _LOG_REQUISICAO.error(
        "erro_nao_tratado request_id=%s method=%s path=%s status=500 exc=%s stack=%s",
        request_id,
        request.method,
        _rota_log_segura(request.url.path),
        type(exc).__name__,
        _stack_sanitizada(exc),
    )
    return request_id


def registrar_falha_interna(escopo: str, exc: BaseException, status_code: int = 500) -> None:
    """Registra uma falha tratada com stack sanitizada e correlação opcional."""
    request_id, metodo, rota = _contexto_atual()
    _LOG_REQUISICAO.error(
        "falha_interna request_id=%s method=%s path=%s status=%s escopo=%s exc=%s stack=%s",
        request_id,
        metodo,
        rota,
        status_code,
        escopo,
        type(exc).__name__,
        _stack_sanitizada(exc),
    )


def registrar_falha_externa(
    escopo: str, exc: BaseException, status_code: int = 502
) -> None:
    """Log curto de falha em dependência externa (Gemini, GitHub, Drive, Supabase).

    Só o escopo e o tipo da exceção. O texto dessas exceções costuma embutir a
    própria credencial rejeitada ("API key AIza... not valid", "bad credentials
    ghs_..."), então nem o log recebe a mensagem original.
    """
    request_id, metodo, rota = _contexto_atual()
    _LOG_REQUISICAO.warning(
        "falha_externa request_id=%s method=%s path=%s status=%s escopo=%s exc=%s",
        request_id,
        metodo,
        rota,
        status_code,
        escopo,
        type(exc).__name__,
    )


def falha_externa(escopo: str, exc: BaseException, mensagem: str, status_code: int = 502) -> HTTPException:
    """Traduz falha de dependência externa em erro estável para o cliente.

    O texto devolvido é fixo por escopo — nunca o `str(exc)`, que costuma
    carregar URL interna, payload, nome de tabela ou trecho de credencial.
    """
    registrar_falha_externa(escopo, exc, status_code)
    return HTTPException(status_code=status_code, detail=mensagem)
