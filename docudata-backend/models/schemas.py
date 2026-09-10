from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
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
    valor_projeto: Optional[float] = None
    gemini_api_key: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    squad: Optional[str] = None
    valor_projeto: Optional[float] = None
    valor_por_ponto: Optional[float] = None
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
    arquetipo: str = "padrao"


class GerenteEmailUpdate(BaseModel):
    gerente_email: Optional[str] = None


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
    created_at: datetime


class SprintCreate(BaseModel):
    numero: Optional[int] = None  # se None, auto = max(numero)+1
    iniciada: bool = True  # False = criada só pra planejar orçamento, some da aba Sprints


class SprintHealthUpdate(BaseModel):
    status_saude: Optional[str] = None       # 'verde' | 'amarelo' | 'vermelho' | None
    plano_correcao: Optional[str] = None


class SprintResponse(BaseModel):
    id: str
    project_id: str
    numero: int
    status_saude: Optional[str] = None
    plano_correcao: Optional[str] = None
    pontos_orcamento: Optional[int] = None
    avaliacao_completa_em: Optional[datetime] = None
    iniciada: bool = True
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
    pontos_usados: int = 0
    faturamento_previsto: Optional[float] = None


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
    arquetipo: Optional[Literal["padrao", "consultoria_discovery"]] = None
    valor_projeto: Optional[float] = None


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
    github_login: Optional[str] = None
    github_email: Optional[str] = None


class OperacionalUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    papel: Optional[str] = None
    ativo: Optional[bool] = None
    github_login: Optional[str] = None
    github_email: Optional[str] = None


class OperacionalResponse(BaseModel):
    id: str
    project_id: str
    nome: str
    email: Optional[str] = None
    papel: Optional[str] = None
    ativo: bool
    github_login: Optional[str] = None
    github_email: Optional[str] = None
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
    extra: bool = False  # task concedida além do que a pessoa tinha; não consome orçamento

    @field_validator("coluna_kanban")
    @classmethod
    def coluna_valida(cls, v: str) -> str:
        if v not in _COLUNAS_VALIDAS:
            raise ValueError("coluna_kanban deve ser planejado | em_andamento | concluida")
        return v


_BLOQUEADO_RESOLVIDO_POR_VALIDOS = {"operacional", "gerente"}


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
    bloqueado_manual: Optional[bool] = None
    bloqueado_por: Optional[str] = None
    bloqueado_resolvido_por: Optional[str] = None
    extra: Optional[bool] = None

    @field_validator("coluna_kanban")
    @classmethod
    def coluna_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _COLUNAS_VALIDAS:
            raise ValueError("coluna_kanban deve ser planejado | em_andamento | concluida")
        return v

    @field_validator("bloqueado_resolvido_por")
    @classmethod
    def bloqueado_resolvido_por_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _BLOQUEADO_RESOLVIDO_POR_VALIDOS:
            raise ValueError("bloqueado_resolvido_por deve ser operacional | gerente")
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
    bloqueado_manual: bool = False
    bloqueado_em: Optional[datetime] = None
    bloqueado_por: Optional[str] = None
    bloqueado_resolvido_por: Optional[str] = None
    bloqueado_resolvido_em: Optional[datetime] = None
    entrou_em_andamento_em: Optional[datetime] = None
    travado_automatico: bool = False
    travado_override: bool = False
    travado_override_por: Optional[str] = None
    travado_override_em: Optional[datetime] = None
    extra: bool = False
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


# ── Sprint orçamento ─────────────────────────────────────────────────────────

class SprintOrcamentoUpdate(BaseModel):
    pontos_orcamento: int = Field(..., ge=0)


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


# ── Auth / RBAC (Phase 16) ─────────────────────────────────────────────────

_CARGOS_VALIDOS = {"lider", "gerente", "operacional"}


class LoginRequest(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    nome: str
    cargo: str


class MeResponse(BaseModel):
    nome: str
    email: str
    cargo: str


class OperacionalSemContaResponse(BaseModel):
    operacional_id: str
    nome: str
    project_id: str
    project_name: str


class SignupClaimRequest(BaseModel):
    operacional_id: str
    email: str
    senha: str = Field(..., min_length=6)
    github_login: str = Field(..., min_length=1)
    github_email: str = Field(..., min_length=1)


class SignupNovoRequest(BaseModel):
    nome: str
    email: str
    senha: str = Field(..., min_length=6)
    github_login: str = Field(..., min_length=1)
    github_email: str = Field(..., min_length=1)


# ── Avaliação do Gerente (Phase 17) ─────────────────────────────────────────

_RESPOSTA_MIN, _RESPOSTA_MAX = 0, 5


class AvaliacaoGerenteCreate(BaseModel):
    operacional_id: str
    sprint_id: str
    resposta_1: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_2: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_3: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_4: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_5: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_6: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_7: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    reaproveitada_de: Optional[str] = None


class AvaliacaoGerenteResponse(BaseModel):
    id: str
    operacional_id: str
    gerente_id: str
    sprint_id: str
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: int
    resposta_7: int
    reaproveitada_de: Optional[str] = None
    criado_em: datetime
    editavel_ate: datetime


class AvaliacaoAnteriorResponse(BaseModel):
    avaliacao_id: str
    project_name: str
    criado_em: datetime
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: int
    resposta_7: int


class PendenciaAvaliacaoResponse(BaseModel):
    operacional_id: str
    nome: str
    ultima_avaliacao_outro_projeto: Optional[AvaliacaoAnteriorResponse] = None


class PontuacaoOperacionalSprintResponse(BaseModel):
    id: str
    operacional_id: str
    sprint_id: str
    projeto_id: str
    sprint_fim: datetime
    gerente_media: Optional[float] = None
    gerente_pergunta6: Optional[int] = None
    entrega_pontos_concluidos: int
    entrega_pontos_alocados: int
    qualidade_reaberturas: int
    qualidade_tasks_concluidas: int
    autonomia_bloqueios_resolvidos_proprio: int
    autonomia_bloqueios_totais: int
    arquetipo: Optional[str] = None
    finalizado_em: datetime


class ConfirmarAvaliacaoResponse(BaseModel):
    sprint_id: str
    # None quando o Líder reabre o fechamento — a sprint volta a ficar em aberto.
    avaliacao_completa_em: Optional[datetime] = None
    pontuacao_travada_count: int = 0


class BaselineEvolucaoCreate(BaseModel):
    operacional_id: str
    ciclo: str
    observacoes: Optional[str] = None


class BaselineEvolucaoResponse(BaseModel):
    id: str
    operacional_id: str
    ciclo: str
    data_snapshot: datetime
    nota_inicial: Optional[float] = None
    observacoes: Optional[str] = None


class SpiPorProjetoResponse(BaseModel):
    projeto_id: str
    spi: Optional[float] = None


class SpiOperacionalResponse(BaseModel):
    operacional_id: str
    spi: Optional[float] = None
    por_projeto: list[SpiPorProjetoResponse] = []


# ── Qualidade de commit via IA (Phase 19) ────────────────────────────────────

class AvaliacaoQualidadeCommit(BaseModel):
    nota: int = Field(ge=0, le=10, description="Nota de 0 a 10 avaliando a qualidade tecnica da entrega deste commit")
    evidencia: str = Field(description="Frase curta explicando o motivo da nota — nunca uma lista de pendencias a corrigir")


# ── Ranking de Performance (Phase 19) ────────────────────────────────────────

class PerformanceOperacionalResponse(BaseModel):
    email: str
    nome: str
    score_final: float
    entrega: Optional[float] = None
    gerente: Optional[float] = None
    qualidade: Optional[float] = None
    autonomia: Optional[float] = None
    evolucao: Optional[float] = None
    janela_parcial: bool
    arquetipo_usado: str


class PerformanceResponse(BaseModel):
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []


# ── Metodologia (documento interno, Líder/Gerente) ───────────────────────────

class MetodologiaResponse(BaseModel):
    titulo: str
    conteudo: str
    restrito: bool = False


class MetodologiaItem(BaseModel):
    slug: str
    titulo: str
    resumo: str


class SpiEvolucaoOperacionalResponse(BaseModel):
    operacional_id: str
    nome: str
    spi: Optional[float] = None
    evolucao: Optional[float] = None
    sprints_avaliadas: int
    pontos_penalizados: int


class OperacionalDisponivelResponse(BaseModel):
    """Pessoa já cadastrada em outro projeto, oferecida para vínculo sem redigitar."""
    nome: str
    email: Optional[str] = None
    papel: Optional[str] = None
    github_login: Optional[str] = None
    github_email: Optional[str] = None
    projetos: list[str] = []


# ── Pedido de task extra ─────────────────────────────────────────────────────

class SolicitacaoTaskCreate(BaseModel):
    operacional_id: str
    sugestao: Optional[str] = None


class SolicitacaoTaskResolve(BaseModel):
    status: Literal["atendida", "recusada"]


class SolicitacaoTaskResponse(BaseModel):
    id: str
    project_id: str
    sprint_id: Optional[str] = None
    operacional_id: str
    operacional_nome: Optional[str] = None
    sugestao: Optional[str] = None
    status: str
    criado_em: datetime
    respondido_em: Optional[datetime] = None


class RedistribuirPontosRequest(BaseModel):
    """Encolhe proporcionalmente as tasks já existentes na sprint para caber
    `pontos_novos`, em vez de simplesmente recusar a task nova."""
    sprint_id: str
    pontos_novos: int


# ── Painel de pessoas com acesso ao sistema ──────────────────────────────────

class PessoaResponse(BaseModel):
    id: str
    nome: str
    email: str
    cargo: str
    projetos: list[str] = []
    created_at: Optional[datetime] = None


class PessoaCargoUpdate(BaseModel):
    cargo: Literal["owner", "lider", "gerente", "operacional"]
