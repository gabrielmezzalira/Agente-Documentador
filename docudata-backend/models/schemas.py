from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime


class ConteudoEstruturado(BaseModel):
    """Schema de extracao de conhecimento de projetos de dados."""

    resumo: str = Field(description="Descricao do que foi trabalhado nesta entrega")
    tarefas: list[str] = Field(description="Lista de tarefas identificadas no arquivo")
    decisoes: list[str] = Field(description="Decisoes tecnicas tomadas nesta sprint")
    problemas: list[str] = Field(description="Problemas e bloqueios identificados")
    contexto_cliente: str = Field(description="Informacoes sobre o cliente ou requisitos de negocio")
    proximos_passos: list[str] = Field(description="Lista de proximos passos identificados")
    tecnologias: list[str] = Field(description="Tecnologias, ferramentas e stacks mencionadas no documento (ex: Python, K-means, Supabase, FastAPI)")
    tecnologias_removidas: list[str] = Field(default_factory=list, description="Tecnologias explicitamente removidas neste commit: pacote deletado de requirements.txt/package.json, diretorio inteiro excluido, imports completamente removidos de todos os arquivos. So inclua se a remocao for explicita e completa no diff — nunca infira.")


class Achado(BaseModel):
    severidade: str = Field(description="CRITICA | ALTA | MEDIA | BAIXA")
    confianca: str = Field(description="ALTA | MEDIA | BAIXA")
    referencia: str = Field(description="arquivo:linha — ex: routers/painel.py:47")
    descricao_tecnica: str
    descricao_gerente: str


class RevisaoEstruturada(BaseModel):
    achados: list[Achado]
    relatorio_gerente: str
    relatorio_tecnico: str


class ProjectCreate(BaseModel):
    name: str
    client: str
    description: Optional[str] = None
    squad: Optional[str] = None
    budget_usd: Optional[float] = None
    gemini_api_key: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    squad: Optional[str] = None
    budget_usd: Optional[float] = None
    has_api_key: bool = False
    is_delivered: bool = False
    created_at: datetime
    last_ingestion_at: Optional[datetime] = None
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = None
    periodo_garantia_dias: Optional[int] = None
    has_github_config: bool = False
    gerente_email: Optional[str] = None


class GerenteEmailUpdate(BaseModel):
    gerente_email: Optional[str] = None


class ProjectCostResponse(BaseModel):
    project_id: str
    total_usd: float
    budget_usd: Optional[float] = None
    input_tokens: int
    output_tokens: int


class UsageBucket(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    count: int


class UsageItem(BaseModel):
    source: str          # "ingestion" | "generated_doc"
    id: str
    label: str
    created_at: datetime
    input_tokens: int
    output_tokens: int
    cost_usd: float


class ProjectUsageResponse(BaseModel):
    project_id: str
    month: str          # formato YYYY-MM
    total_usd: float
    input_tokens: int
    output_tokens: int
    breakdown: dict[str, UsageBucket] = {}
    items: list[UsageItem] = []
    truncated: bool = False


class IngestResponse(BaseModel):
    status: str          # "ok" | "error"
    sprint: int
    tentativas: int = 0  # expose for LangSmith correlation


class GenerateRequest(BaseModel):
    projeto_id: str
    tipo_doc: str        # repasse_semanal | retrospectiva | log_decisoes | documentacao_final | ata_reuniao | adr | onboarding | planning | daily | review
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
    tipo_documentacao: Optional[str] = None
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


class FuncionalidadeCreate(BaseModel):
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str = "should"
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None

    @field_validator("criterios_aceite")
    @classmethod
    def criterios_nao_vazios(cls, v: list[str]) -> list[str]:
        filtered = [c for c in v if c.strip()]
        if not filtered:
            raise ValueError("Ao menos um critério de aceite é obrigatório")
        return filtered

    @field_validator("prioridade")
    @classmethod
    def prioridade_valida(cls, v: str) -> str:
        if v not in {"must", "should", "could", "wont"}:
            raise ValueError("prioridade deve ser must | should | could | wont")
        return v


class FuncionalidadeUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    criterios_aceite: Optional[list[str]] = None
    prioridade: Optional[str] = None
    status: Optional[str] = None
    status_cliente: Optional[str] = None
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None
    data_aprovacao_cliente: Optional[date] = None
    autor: Optional[str] = None
    motivo: Optional[str] = None
    testes_e2e: Optional[list[str]] = None

    @field_validator("criterios_aceite")
    @classmethod
    def criterios_nao_vazios(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        filtered = [c for c in v if c.strip()]
        if not filtered:
            raise ValueError("Ao menos um critério de aceite é obrigatório")
        return filtered

    @field_validator("prioridade")
    @classmethod
    def prioridade_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in {"must", "should", "could", "wont"}:
            raise ValueError("prioridade deve ser must | should | could | wont")
        return v


class FuncionalidadeResponse(BaseModel):
    id: str
    project_id: str
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str
    status: str
    status_cliente: str
    data_aprovacao_cliente: Optional[date] = None
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None
    testes_e2e: list[str] = []
    created_at: datetime


class TransicaoStatusResponse(BaseModel):
    id: str
    funcionalidade_id: str
    campo: str
    de: str
    para: str
    autor: Optional[str] = None
    timestamp: datetime
    motivo: Optional[str] = None
    duracao_fase_anterior_segundos: Optional[int] = None


class FuncionalidadeProposta(BaseModel):
    id_funcional: str
    titulo: str
    descricao: Optional[str] = None
    criterios_aceite: list[str]
    prioridade: str = "should"


class ImportPropostaResponse(BaseModel):
    propostas: list[FuncionalidadeProposta]


class ImportConfirmarItem(BaseModel):
    proposta: FuncionalidadeProposta
    confirmed: bool


class ImportConfirmarRequest(BaseModel):
    project_id: str
    itens: list[ImportConfirmarItem]


class ContratoUpdate(BaseModel):
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = Field(default=None, ge=0)
    periodo_garantia_dias: Optional[int] = Field(default=None, ge=0)


class ExecucaoAceitePayload(BaseModel):
    funcionalidade_id: str
    commit_sha: str
    gates: list[dict]


class ExecucaoAceiteResponse(BaseModel):
    id: str
    funcionalidade_id: str
    project_id: str
    commit_sha: str
    gates: list[dict]
    disparado_em: datetime
    concluido_em: Optional[datetime] = None


class BoletimCreate(BaseModel):
    project_id: str
    sprint_numero: Optional[int] = None
    funcionalidade_ids: list[str]


class BoletimPatch(BaseModel):
    status: str
    retorno_tipo: Optional[str] = None


class BoletimResponse(BaseModel):
    id: str
    project_id: str
    sprint_numero: Optional[int] = None
    funcionalidade_ids: list[str]
    status: str
    retorno_tipo: Optional[str] = None
    conteudo: str
    criado_em: datetime
    enviado_em: Optional[datetime] = None
    retorno_em: Optional[datetime] = None


class ResumoSemanalRequest(BaseModel):
    project_id: str


# ── Operacionais ────────────────────────────────────────────────────────────

class OperacionalCreate(BaseModel):
    project_id: str
    nome: str
    email: Optional[str] = None
    papel: Optional[str] = None  # texto livre: "Front", "Back", "Design", "Gerente"


class OperacionalUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    papel: Optional[str] = None
    ativo: Optional[bool] = None


class OperacionalResponse(BaseModel):
    id: str
    project_id: str
    nome: str
    email: Optional[str] = None
    papel: Optional[str] = None
    ativo: bool
    created_at: datetime


# ── Tasks ────────────────────────────────────────────────────────────────────

_COLUNAS_VALIDAS = {"planejado", "em_andamento", "concluida"}


class TaskCreate(BaseModel):
    project_id: str
    titulo: str
    pontos: int = Field(..., gt=0)
    funcionalidade_id: Optional[str] = None
    sprint_id: Optional[str] = None
    operacional_id: Optional[str] = None
    descricao: Optional[str] = None
    coluna_kanban: str = "planejado"
    checklist: Optional[list[dict]] = None  # [{texto, done}]
    ordem: int = 0

    @field_validator("coluna_kanban")
    @classmethod
    def coluna_valida(cls, v: str) -> str:
        if v not in _COLUNAS_VALIDAS:
            raise ValueError("coluna_kanban deve ser planejado | em_andamento | concluida")
        return v


class TaskUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    pontos: Optional[int] = Field(default=None, gt=0)
    funcionalidade_id: Optional[str] = None
    sprint_id: Optional[str] = None
    operacional_id: Optional[str] = None
    coluna_kanban: Optional[str] = None
    bloqueado: Optional[bool] = None
    motivo_bloqueio: Optional[str] = None
    checklist: Optional[list[dict]] = None
    ordem: Optional[int] = None
    autor: Optional[str] = None
    motivo: Optional[str] = None

    @field_validator("coluna_kanban")
    @classmethod
    def coluna_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _COLUNAS_VALIDAS:
            raise ValueError("coluna_kanban deve ser planejado | em_andamento | concluida")
        return v


class TaskResponse(BaseModel):
    id: str
    project_id: str
    funcionalidade_id: Optional[str] = None
    sprint_id: Optional[str] = None
    operacional_id: Optional[str] = None
    titulo: str
    descricao: Optional[str] = None
    pontos: int
    coluna_kanban: str
    bloqueado: bool
    motivo_bloqueio: Optional[str] = None
    checklist: list[dict] = []
    ordem: int
    contador_reaberturas: int = 0
    created_at: datetime
    updated_at: datetime


class TaskReordenarItem(BaseModel):
    id: str
    ordem: int


class TaskTransicaoResponse(BaseModel):
    id: str
    task_id: str
    campo: str
    de: Optional[str] = None
    para: Optional[str] = None
    autor: Optional[str] = None
    timestamp: datetime
    motivo: Optional[str] = None
    duracao_fase_anterior_segundos: Optional[int] = None


# ── Sprint baseline ──────────────────────────────────────────────────────────

class SprintBaselineUpdate(BaseModel):
    pontos_previstos: Optional[int] = Field(default=None, gt=0)
    faturamento_previsto: Optional[float] = Field(default=None, ge=0)
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    lock: bool = False


class SprintBaselineResponse(SprintResponse):
    pontos_previstos: Optional[int] = None
    faturamento_previsto: Optional[float] = None
    baseline_locked_at: Optional[datetime] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None


# ── Task sugestões ────────────────────────────────────────────────────────────

class TaskSugestaoResponse(BaseModel):
    id: str
    task_id: str
    task_titulo: str
    acao: str
    motivo: Optional[str] = None
    origem_ingestion_id: Optional[str] = None
    aceita: Optional[bool] = None
    criado_em: datetime
    task_coluna_atual: Optional[str] = None


class TaskSugestaoResolve(BaseModel):
    aceita: bool
