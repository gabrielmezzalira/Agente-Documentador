from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConteudoEstruturado(BaseModel):
    """Schema de extracao de conhecimento de projetos de dados."""

    resumo: str = Field(description="Descricao do que foi trabalhado nesta entrega")
    tarefas: list[str] = Field(description="Lista de tarefas identificadas no arquivo")
    decisoes: list[str] = Field(description="Decisoes tecnicas tomadas nesta sprint")
    problemas: list[str] = Field(description="Problemas e bloqueios identificados")
    contexto_cliente: str = Field(description="Informacoes sobre o cliente ou requisitos de negocio")
    proximos_passos: list[str] = Field(description="Lista de proximos passos identificados")


class ProjectCreate(BaseModel):
    name: str
    client: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    created_at: datetime


class IngestResponse(BaseModel):
    status: str          # "ok" | "error"
    sprint: int
    tentativas: int = 0  # expose for LangSmith correlation
