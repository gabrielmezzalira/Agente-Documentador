from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional
from datetime import date, datetime

from services.regua import MENSAGEM_NIVEL_INVALIDO, NIVEIS


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


ModoTrabalho = Literal["ATRIBUICAO", "PULL"]
ModoAvaliacao = Literal["PONTOS_ATRIBUIDOS", "PONTOS_RELATIVO"]


class WipConfigResponse(BaseModel):
    por_pessoa: Optional[int] = None
    por_coluna_em_andamento: Optional[int] = None


# Fonte única das subáreas aceitas em criação, listagem e busca. `ProjectSubareaUpdate`
# NÃO usa este tipo de propósito: não se entra em Produto pela troca Dados↔Dev.
Subarea = Literal["dados", "dev", "produto"]


class ProjectCreate(BaseModel):
    name: str
    client: str
    subarea: Subarea
    description: Optional[str] = None
    squad: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    # Registros anteriores à migration v3 continuam pertencendo a Dados.
    subarea: Subarea = "dados"
    description: Optional[str] = None
    squad: Optional[str] = None
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
    modo_trabalho: ModoTrabalho = "ATRIBUICAO"
    modo_avaliacao: ModoAvaliacao = "PONTOS_ATRIBUIDOS"
    pull_piso_pontos: float = 1
    pull_teto: float = 1.5
    wip_config: Optional[WipConfigResponse] = None


class ModosProjetoUpdate(BaseModel):
    """PATCH /projects/{id}/modos — RF-A1..A4. Todos os campos são opcionais;
    só o que vier preenchido é alterado (mesmo padrão de ContratoUpdate).
    modo_avaliacao não é aceito aqui: é sempre derivado de modo_trabalho
    (ver _derivar_modo_avaliacao em routers/projects.py)."""
    modo_trabalho: Optional[ModoTrabalho] = None
    pull_piso_pontos: Optional[float] = Field(default=None, gt=0)
    pull_teto: Optional[float] = Field(default=None, gt=0)


class MigrarModoRequest(BaseModel):
    """POST /projects/{id}/migrar-modo — RF-M1..M8 (Entrega 3)."""
    para: ModoTrabalho


class ConfiguracaoHistoricoResponse(BaseModel):
    id: str
    project_id: str
    campo: Literal["modo_trabalho", "modo_avaliacao"]
    valor_anterior: Optional[str] = None
    valor_novo: str
    usuario_email: str
    criado_em: datetime


class WipConfigUpdate(BaseModel):
    """PATCH /projects/{id}/wip-config. Em projeto PULL, por_pessoa é
    ignorado e forçado a 1 no servidor (RF-A5) — nunca confiar no valor que o
    cliente mandou nesse modo."""
    por_pessoa: Optional[int] = Field(default=None, ge=1)
    por_coluna_em_andamento: Optional[int] = Field(default=None, ge=1)


class PontuacaoEventoResponse(BaseModel):
    id: str
    operacional_id: str
    sprint_id: str
    projeto_id: str
    task_id: Optional[str] = None
    tipo: Literal[
        "entrega_concluida", "travamento_penalidade", "devolucao_penalidade",
        "bonus_extra", "reabertura",
    ]
    pontos: int
    descricao: Optional[str] = None
    criado_em: datetime


class ProjectSubareaUpdate(BaseModel):
    subarea: Literal["dados", "dev"]


class ProjectEncaminharRequest(BaseModel):
    destino: Literal["dados", "dev"]
    motivo: Optional[str] = Field(default=None, max_length=500)
    promover_validados: bool = False


class GeminiApiKeyUpdate(BaseModel):
    api_key: str = Field(min_length=1)


class GeminiApiKeyStatus(BaseModel):
    configured: bool
    key_hint: Optional[str] = None
    updated_at: Optional[datetime] = None


class GitHubCapabilities(BaseModel):
    enabled: bool
    configured: bool
    subareas: list[str]
    app_slug: Optional[str] = None


class GitHubConnectionSession(BaseModel):
    install_url: Optional[str] = None
    connection_token: Optional[str] = None


class GitHubRepositoryCandidate(BaseModel):
    github_repository_id: int
    full_name: str
    html_url: str
    default_branch: Optional[str] = None
    pushed_at: Optional[datetime] = None
    private: bool = False
    connection_status: Literal["available", "connected_here", "unavailable"] = "available"


class GitHubRepositoriesAvailable(BaseModel):
    repositories: list[GitHubRepositoryCandidate]
    manage_url: Optional[str] = None
    repository_scope: Literal["all", "selected", "unknown"] = "unknown"
    has_more: bool = False


class ProjectRepositoryCreate(BaseModel):
    connection_token: str = Field(min_length=1)
    repository_ids: list[int] = Field(min_length=1)


class ProjectRepositoryResponse(BaseModel):
    id: str
    project_id: str
    github_repository_id: int
    full_name: str
    html_url: str
    default_branch: Optional[str] = None
    active: bool
    permission_status: Literal["active", "revoked", "disconnected"]
    connected_at: datetime
    updated_at: datetime


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
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    source_repository_id: Optional[str] = None
    source_repository_full_name: Optional[str] = None
    source_commit_sha: Optional[str] = None
    source_branch: Optional[str] = None
    source_url: Optional[str] = None
    source_diff_stat: Optional[str] = None
    created_at: datetime


class SprintCreate(BaseModel):
    numero: Optional[int] = None  # se None, auto = max(numero)+1
    iniciada: bool = True  # False = criada só pra planejar, some da aba Sprints


class SprintHealthUpdate(BaseModel):
    status_saude: Optional[str] = None       # 'verde' | 'amarelo' | 'vermelho' | None
    plano_correcao: Optional[str] = None


class SprintResponse(BaseModel):
    id: str
    project_id: str
    numero: int
    status_saude: Optional[str] = None
    plano_correcao: Optional[str] = None
    avaliacao_completa_em: Optional[datetime] = None
    iniciada: bool = True
    created_at: datetime
    updated_at: datetime
    modo_trabalho: Optional[str] = None
    modo_avaliacao: Optional[str] = None
    hibrida: bool = False


class SprintStatusResponse(SprintResponse):
    """Sprint + agregados de mínimo obrigatório (usado pelo GET de listagem)."""
    tem_planning: bool = False
    tem_review: bool = False
    dailys_count: int = 0
    ingestions_count: int = 0          # total de ingestões da sprint (qualquer tipo)
    docs_gerados_count: int = 0        # total de generated_docs da sprint
    pendencias: list[str] = []          # subset de ['planning','review'] que estão faltando
    avaliados_count: int = 0
    elegiveis_avaliacao_count: int = 0
    previsto: int = 0
    planejado_no_inicio: int = 0
    surgiu_na_sprint: int = 0


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
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None
    autor: Optional[str] = None
    motivo: Optional[str] = None

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
    responsavel: Optional[str] = None
    sprint_alvo: Optional[str] = None
    created_at: datetime
    aprovada_em: Optional[datetime] = None
    aprovada_por: Optional[str] = None
    aprovada_por_nome: Optional[str] = None
    tem_tasks: bool = False
    meta_sprints: list[int] = []


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
    data_entrada: datetime
    data_saida: Optional[datetime] = None


# ── Tasks ────────────────────────────────────────────────────────────────────

_COLUNAS_VALIDAS = {"planejado", "em_andamento", "pendente_aprovacao", "concluida"}


class TaskCreate(BaseModel):
    project_id: str
    titulo: str
    pontos: Optional[int] = None  # ignorado: o nível vem do classificador (spec A2)
    opiniao_nivel: Optional[int] = None
    funcionalidade_id: Optional[str] = None
    sprint_id: Optional[str] = None
    operacional_id: Optional[str] = None
    descricao: Optional[str] = None
    coluna_kanban: str = "planejado"
    checklist: Optional[list[dict]] = None  # [{texto, done}]
    ordem: int = 0
    extra: bool = False  # task concedida além do que a pessoa tinha; não entra no previsto da sprint
    requer_aprovacao: bool = False  # true: não pode ir direto pra concluida, precisa passar por pendente_aprovacao

    @field_validator("pontos", "opiniao_nivel")
    @classmethod
    def nivel_na_regua(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v

    @field_validator("coluna_kanban")
    @classmethod
    def coluna_valida(cls, v: str) -> str:
        if v not in _COLUNAS_VALIDAS:
            raise ValueError("coluna_kanban deve ser planejado | em_andamento | concluida")
        return v


_BLOQUEADO_RESOLVIDO_POR_VALIDOS = {"operacional", "gerente"}
_BLOQUEIO_TIPOS_VALIDOS = {"interno", "cliente"}


class TaskUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    pontos: Optional[int] = None
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
    bloqueio_tipo: Optional[str] = None
    extra: Optional[bool] = None
    requer_aprovacao: Optional[bool] = None

    @field_validator("pontos")
    @classmethod
    def pontos_na_regua(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v

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

    @field_validator("bloqueio_tipo")
    @classmethod
    def bloqueio_tipo_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _BLOQUEIO_TIPOS_VALIDOS:
            raise ValueError("bloqueio_tipo deve ser interno | cliente")
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
    pontos_legado: Optional[int] = None
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
    bloqueio_tipo: Optional[str] = None
    entrou_em_andamento_em: Optional[datetime] = None
    travado_automatico: bool = False
    travado_override: bool = False
    travado_override_por: Optional[str] = None
    travado_override_em: Optional[datetime] = None
    extra: bool = False
    prevista_no_inicio: bool = False
    surgiu_na_sprint: bool = False
    created_at: datetime
    updated_at: datetime
    entrou_na_fila_em: Optional[datetime] = None
    pull_em: Optional[datetime] = None
    atribuida_manualmente: bool = False
    motivo_atribuicao_manual: Optional[str] = None
    ordem_fila: Optional[int] = None
    requer_aprovacao: bool = False
    nivel_travado_em: Optional[datetime] = None
    classificacao_status: Optional[str] = None
    justificativa_nivel: Optional[str] = None
    faltando: Optional[list[str]] = None


class ReclassificarResponse(BaseModel):
    task_id: str
    nivel_final: int
    status: str
    justificativa_nivel: Optional[str] = None
    motivo_revisao: Optional[str] = None


class RevisaoNivelRequest(BaseModel):
    nivel: int
    motivo: str = Field(..., min_length=3)

    @field_validator("nivel")
    @classmethod
    def nivel_na_regua(cls, v: int) -> int:
        if v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v


class OpiniaoNivelRequest(BaseModel):
    nivel: int

    @field_validator("nivel")
    @classmethod
    def nivel_na_regua(cls, v: int) -> int:
        if v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v


class RejeitarTaskRequest(BaseModel):
    """POST /tasks/{id}/rejeitar — devolve uma task de pendente_aprovacao
    pra planejado, sem responsável. Ver spec, §4."""
    motivo: str = Field(..., min_length=1)
    autor: Optional[str] = None


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


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str = Field(..., min_length=6)


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
    resposta_6: Optional[int] = Field(default=None, ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
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
    resposta_6: Optional[int] = None
    resposta_7: int
    reaproveitada_de: Optional[str] = None
    criado_em: datetime
    editavel_ate: datetime


class AvaliacaoGerenteEdicao(BaseModel):
    resposta_1: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_2: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_3: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_4: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_5: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_7: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_obrigatorio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o motivo da edição")
        return v


class AvaliacaoHistoricoItem(BaseModel):
    id: str
    operacional_id: str
    operacional_nome: str
    sprint_id: str
    sprint_numero: Optional[int] = None
    projeto_id: Optional[str] = None
    projeto_nome: str
    modo_trabalho: str
    avaliador_nome: str
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: Optional[int] = None
    resposta_7: int
    criado_em: datetime
    total_edicoes: int
    ultima_edicao_em: Optional[datetime] = None
    ultima_edicao_por: Optional[str] = None


class AvaliacaoEdicaoItem(BaseModel):
    id: str
    editor_nome: str
    antes: dict
    depois: dict
    motivo: str
    criado_em: datetime


class AvaliacaoAnteriorResponse(BaseModel):
    avaliacao_id: str
    project_name: str
    criado_em: datetime
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: Optional[int] = None
    resposta_7: int


class PendenciaAvaliacaoResponse(BaseModel):
    operacional_id: str
    nome: str
    ultima_avaliacao_outro_projeto: Optional[AvaliacaoAnteriorResponse] = None


class ElegivelResponse(BaseModel):
    """RF-C7 (Entrega 2): todo operacional vinculado ao projeto no momento da
    consulta, com contagem de tasks na sprint (0 é válido) e se já tem
    avaliação registrada — auditoria de quem entra no denominador da
    Avaliação Semanal."""
    operacional_id: str
    nome: str
    tasks_na_sprint: int
    avaliado: bool


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
    janela_parcial: bool
    arquetipo_usado: str


class PerformanceProjetoResponse(BaseModel):
    projeto_id: str
    projeto_nome: str
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []


class PerformanceResponse(BaseModel):
    projetos: list[PerformanceProjetoResponse] = []


# ── Metodologia (documento interno, Líder/Gerente) ───────────────────────────

class MetodologiaResponse(BaseModel):
    titulo: str
    conteudo: str
    restrito: bool = False


class MetodologiaItem(BaseModel):
    slug: str
    titulo: str
    resumo: str


class SpiPorOperacionalDoProjetoResponse(BaseModel):
    operacional_id: str
    nome: str
    spi: Optional[float] = None
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


class ExclusaoAprendizadoPayload(BaseModel):
    excluida: bool
    motivo: Optional[str] = None

    @field_validator("motivo")
    @classmethod
    def _motivo_limpo(cls, v):
        v = (v or "").strip()
        return v or None

    @model_validator(mode="after")
    def _motivo_obrigatorio(self):
        if self.excluida and not self.motivo:
            raise ValueError("Informe o motivo da exclusão")
        return self


class MetaUpdate(BaseModel):
    funcionalidade_ids: list[str]


class MetaResponse(BaseModel):
    sprint_id: str
    funcionalidade_ids: list[str]


class MetaEvento(BaseModel):
    funcionalidade_id: Optional[str] = None
    titulo: Optional[str] = None
    acao: str
    pessoa_nome: Optional[str] = None
    criado_em: str


class AcompGerente(BaseModel):
    nome: str
    email: Optional[str] = None


class AcompKpis(BaseModel):
    projetos: int
    criticos: int
    atencao: int
    sem_dados: int
    saudaveis: int
    features_entregues: Optional[int] = None
    features_entregues_var: Optional[int] = None
    spi_medio: Optional[float] = None
    spi_medio_var: Optional[float] = None
    metas_batidas: int
    metas_fechadas: int
    projetos_sem_meta: int
    tasks_travadas: int


class AcompFilaItem(BaseModel):
    projeto_id: str
    nome: Optional[str] = None
    gerente: str
    status: str
    motivos: list[str]


class AcompMapaSprint(BaseModel):
    rel: int
    numero: Optional[int] = None
    spi: Optional[float] = None
    meta_total: int = 0
    meta_entregues: int = 0
    meta_batida: Optional[bool] = None
    parcial: bool = False


class AcompMapaProjeto(BaseModel):
    projeto_id: str
    nome: Optional[str] = None
    sprints: list[AcompMapaSprint]


class AcompPonto(BaseModel):
    projeto_id: str
    nome: Optional[str] = None
    pct_prazo: float
    pct_escopo: float
    travadas: int
    status: str


class AcompDispersao(BaseModel):
    pontos: list[AcompPonto]
    sem_datas: int
    sem_funcionalidades: int = 0


class AcompPorGerente(BaseModel):
    nome: str
    email: Optional[str] = None
    projetos: int
    criticos: int
    atencao: int
    metas_batidas: int
    metas_fechadas: int


class AcompProjetoStatus(BaseModel):
    id: str
    nome: Optional[str] = None
    status: str
    motivos: list[str]
    diagnostico: str


class AcompanhamentoResponse(BaseModel):
    subarea: str
    filtro_gerente: Optional[str] = None
    gerentes: list[AcompGerente]
    kpis: AcompKpis
    fila: list[AcompFilaItem]
    mapa: list[AcompMapaProjeto]
    dispersao: AcompDispersao
    por_gerente: list[AcompPorGerente]
    projetos: list[AcompProjetoStatus]


class AcompSinal(BaseModel):
    codigo: str
    texto: str


class AcompDetalheProjeto(BaseModel):
    id: str
    nome: Optional[str] = None
    cliente: Optional[str] = None
    gerente: Optional[str] = None


class AcompNumeros(BaseModel):
    spi_atual: Optional[float] = None
    spi_ultima_fechada: Optional[float] = None
    sem_funcionalidades: bool = False
    pct_prazo: Optional[float] = None
    pct_escopo: Optional[float] = None
    prazo_sem_dados: bool
    travadas: int
    p85_horas: Optional[float] = None


class AcompSprintRef(BaseModel):
    id: str
    numero: int
    fechada: bool


class AcompMetaFunc(BaseModel):
    id: str
    id_funcional: Optional[str] = None
    titulo: Optional[str] = None
    status: Optional[str] = None
    aprovada: bool
    pct_tasks: Optional[float] = None
    planejada_na_sprint: bool


class AcompMeta(BaseModel):
    total: int
    entregues: int
    batida: Optional[bool] = None
    funcionalidades: list[AcompMetaFunc]


class AcompForaDaMeta(BaseModel):
    id: str
    id_funcional: Optional[str] = None
    titulo: Optional[str] = None


class AcompSprintLinha(BaseModel):
    numero: int
    previsto: float
    realizado: float
    spi: Optional[float] = None
    meta_batida: Optional[bool] = None


class AcompPessoa(BaseModel):
    operacional_id: str
    nome: Optional[str] = None
    realizado: float
    piso: Optional[float] = None
    abaixo: Optional[bool] = None


class AcompTime(BaseModel):
    sprint_numero: Optional[int] = None
    mediana_squad: Optional[float] = None
    mediana_subarea: Optional[float] = None
    pessoas: list[AcompPessoa]


class AcompDetalheResponse(BaseModel):
    projeto: AcompDetalheProjeto
    status: str
    diagnostico: str
    sinais: list[AcompSinal]
    numeros: AcompNumeros
    sprint_atual: Optional[AcompSprintRef] = None
    proximas_sprints: list[AcompSprintRef]
    meta: AcompMeta
    planejadas_fora_da_meta: list[AcompForaDaMeta]
    sprints: list[AcompSprintLinha]
    time: AcompTime
