"""Schemas do domínio Discovery (Spec 12): reuniões, requisitos e saída do modelo."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

TipoReuniao = Literal["contexto_empresa", "entrevista_tecnica", "validacao", "outra"]
TipoRequisito = Literal["funcional", "dados", "integracao", "nao_funcional", "regra_negocio"]
Lente = Literal["produto", "dados"]
Prioridade = Literal["must", "should", "could", "wont"]
StatusRequisito = Literal["proposto", "em_revisao", "validado", "rejeitado"]
StatusAnalise = Literal["pendente", "ok", "falhou"]


# ---- entrada de reuniões (serviço a serviço) ----
class ReuniaoIngestRequest(BaseModel):
    docudata_project_id: str = Field(min_length=1)
    fonte_session_id: str = Field(min_length=8, max_length=64)
    tipo: TipoReuniao = "outra"
    ocorrida_em: Optional[datetime] = None
    conteudo_estruturado: dict = Field(default_factory=dict)
    transcricao: Optional[str] = None


class ReuniaoIngestResponse(BaseModel):
    id: str
    analise_status: StatusAnalise
    duplicada: bool = False


class ReuniaoResponse(BaseModel):
    id: str
    project_id: str
    tipo: TipoReuniao
    origem: str
    fonte_session_id: Optional[str] = None
    ocorrida_em: Optional[datetime] = None
    analise_status: StatusAnalise
    created_at: datetime


# ---- requisitos ----
class EvidenciaResponse(BaseModel):
    id: str
    requisito_id: str
    reuniao_id: str
    trecho: str
    speaker: Optional[str] = None
    confianca: Optional[float] = None
    created_at: datetime


class TransicaoRequisitoResponse(BaseModel):
    id: str
    requisito_id: str
    campo: str
    de: str
    para: str
    autor: Optional[str] = None
    motivo: Optional[str] = None
    timestamp: datetime


class RequisitoResponse(BaseModel):
    id: str
    project_id: str
    codigo: str
    titulo: str
    descricao: Optional[str] = None
    tipo: TipoRequisito
    lente: Optional[Lente] = None
    criterios_aceite: list[str] = Field(default_factory=list)
    prioridade_sugerida: Prioridade
    justificativa: Optional[str] = None
    status: StatusRequisito
    motivo_decisao: Optional[str] = None
    possivel_duplicata_de: Optional[str] = None
    conflito: bool = False
    revisado_por: Optional[str] = None
    validado_por: Optional[str] = None
    funcionalidade_id: Optional[str] = None
    n_evidencias: int = 0


class RequisitoDetalheResponse(RequisitoResponse):
    evidencias: list[EvidenciaResponse] = Field(default_factory=list)
    transicoes: list[TransicaoRequisitoResponse] = Field(default_factory=list)


class RequisitoPatch(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=3, max_length=200)
    descricao: Optional[str] = Field(default=None, max_length=4000)
    criterios_aceite: Optional[list[str]] = None
    prioridade_sugerida: Optional[Prioridade] = None
    status: Optional[StatusRequisito] = None
    motivo: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("criterios_aceite")
    @classmethod
    def _limpar_criterios(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        limpos = [c.strip() for c in v if c and c.strip()]
        if not limpos:
            raise ValueError("Informe ao menos um critério de aceite")
        return limpos

    @model_validator(mode="after")
    def _ao_menos_um_campo(self):
        campos = self.model_dump(exclude_none=True, exclude={"motivo"})
        if not campos:
            raise ValueError("Nenhum campo para alterar")
        return self


# ---- saída estruturada do modelo (grafo de requisitos) ----
class NovoRequisito(BaseModel):
    titulo: str
    descricao: str = ""
    tipo: TipoRequisito = "funcional"
    lente: Optional[Lente] = None
    criterios_aceite: list[str] = Field(default_factory=list)
    prioridade_sugerida: Prioridade = "should"
    justificativa: str = ""
    trecho: str
    speaker: Optional[str] = None
    confianca: float = 0.5


class Reforco(BaseModel):
    codigo: str
    trecho: str
    speaker: Optional[str] = None
    confianca: float = 0.5


class Conflito(BaseModel):
    codigo: str
    descricao: str


class AjustePrioridade(BaseModel):
    codigo: str
    prioridade: Prioridade
    justificativa: str = ""


class SaidaAnalise(BaseModel):
    novos: list[NovoRequisito] = Field(default_factory=list)
    reforcos: list[Reforco] = Field(default_factory=list)
    conflitos: list[Conflito] = Field(default_factory=list)
    ajustes_prioridade: list[AjustePrioridade] = Field(default_factory=list)
