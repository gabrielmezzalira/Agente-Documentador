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
    tecnologias: list[str] = Field(description="Tecnologias, ferramentas e stacks mencionadas no documento (ex: Python, K-means, Supabase, FastAPI)")


class ProjectCreate(BaseModel):
    name: str
    client: str
    description: Optional[str] = None
    budget_usd: Optional[float] = None
    gemini_api_key: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    budget_usd: Optional[float] = None
    has_api_key: bool = False
    is_delivered: bool = False
    created_at: datetime
    last_ingestion_at: Optional[datetime] = None


class ProjectCostResponse(BaseModel):
    project_id: str
    total_usd: float
    budget_usd: Optional[float] = None
    input_tokens: int
    output_tokens: int


class IngestResponse(BaseModel):
    status: str          # "ok" | "error"
    sprint: int
    tentativas: int = 0  # expose for LangSmith correlation


class GenerateRequest(BaseModel):
    projeto_id: str
    tipo_doc: str        # sprint_status | sprint_retro | decisoes | completo | ata_reuniao
    sprint_numero: Optional[int] = None
    ingestion_id: Optional[str] = None
    observacoes: Optional[str] = None


class GenerateResponse(BaseModel):
    id: str
    doc_type: str
    sprint_number: Optional[int] = None
    content: str
    created_at: datetime


class IngestionResponse(BaseModel):
    id: str
    project_id: str
    sprint_number: int
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    extracted_content: Optional[dict] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    created_at: datetime


class SprintCreate(BaseModel):
    numero: Optional[int] = None  # se None, auto = max(numero)+1


class SprintHealthUpdate(BaseModel):
    status_saude: Optional[str] = None       # 'verde' | 'amarelo' | 'vermelho' | None
    plano_correcao: Optional[str] = None


class SprintResponse(BaseModel):
    id: str
    project_id: str
    numero: int
    status_saude: Optional[str] = None
    plano_correcao: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SprintStatusResponse(SprintResponse):
    """Sprint + agregados de mínimo obrigatório (usado pelo GET de listagem)."""
    tem_planning: bool = False
    tem_review: bool = False
    dailys_count: int = 0
    ingestions_count: int = 0          # total de ingestões da sprint (qualquer tipo)
    docs_gerados_count: int = 0        # total de generated_docs da sprint
    pendencias: list[str] = []          # subset de ['planning','review'] que estão faltando


class SprintDocResponse(BaseModel):
    """Resposta unificada dos endpoints /sprint-docs/* — devolve a ingestão criada e o doc gerado."""
    ingestion_id: str
    doc_id: str
    doc_type: str           # planning | daily | review
    sprint_number: int
    content: str            # markdown gerado
    created_at: datetime


class ManualDocCreate(BaseModel):
    """Payload pra criar um doc manualmente (sem chamar o LLM)."""
    projeto_id: str
    doc_type: str
    sprint_numero: Optional[int] = None
    content: str


class TechTimelineEntry(BaseModel):
    tecnologia: str
    introduzida_em: int
    abandonada_em: Optional[int] = None   # None = ainda em uso


class TechTimelineResponse(BaseModel):
    em_uso_atual: list[str]
    timeline: list[TechTimelineEntry]
