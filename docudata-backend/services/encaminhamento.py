"""Encaminhamento (bifurcação) de um projeto de Produto para Dados ou Dev (Spec 11 §6)."""
from typing import Any

DESTINOS_PERMITIDOS = ("dados", "dev")


class EncaminhamentoErro(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def validar_origem(subarea_origem: str) -> None:
    """Só projeto de Produto pode ser encaminhado; a origem vem do banco, nunca do corpo."""
    if subarea_origem != "produto":
        raise EncaminhamentoErro(409, "Só projetos de Produto podem ser encaminhados")


def executar_encaminhamento(
    client: Any,
    *,
    project_id: str,
    destino: str,
    motivo: str | None,
    autor_email: str,
    requisitos_promovidos: int = 0,
) -> None:
    """Chama a função SQL `encaminhar_projeto`: troca a subárea e grava o registro na mesma transação."""
    if destino not in DESTINOS_PERMITIDOS:
        raise EncaminhamentoErro(422, "Destino inválido")
    try:
        resposta = client.rpc("encaminhar_projeto", {
            "p_project_id": project_id,
            "p_destino": destino,
            "p_motivo": motivo,
            "p_autor": autor_email,
            "p_promovidos": requisitos_promovidos,
        }).execute()
    except Exception as exc:  # o detalhe real não sobe para o cliente
        if "origem_invalida" in str(exc):
            raise EncaminhamentoErro(409, "Só projetos de Produto podem ser encaminhados") from exc
        raise EncaminhamentoErro(502, "Falha ao encaminhar o projeto") from exc
    if not resposta.data:
        raise EncaminhamentoErro(502, "Falha ao encaminhar o projeto")
