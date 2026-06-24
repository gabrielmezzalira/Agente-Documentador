/**
 * Metadados dos 10 tipos de documento gerados pelo DocuData.
 *
 * Cada entrada explica o que é o doc, pra que serve, quando usar e em quais
 * insumos ele se baseia. Os campos são consumidos pelo DocTypeCard (UI) e
 * pela função docTypeLabel (rótulos curtos).
 *
 * Scope:
 *   - 'sprint'    → precisa de sprint_numero (input numérico ou seleção)
 *   - 'ingestion' → precisa de ingestion_id (seleção dentre as ingestões do projeto)
 *   - 'project'   → não precisa de input adicional (usa tudo do projeto)
 *   - 'hybrid'    → criado via modal estruturado (Planning/Daily/Review)
 */

export type DocTypeKey =
  | "sprint_status"
  | "sprint_retro"
  | "ata_reuniao"
  | "decisoes"
  | "adr"
  | "onboarding"
  | "completo"
  | "planning"
  | "daily"
  | "review";

export type DocTypeScope = "sprint" | "ingestion" | "project" | "hybrid";

export interface DocTypeMeta {
  key: DocTypeKey;
  label: string;
  icone: string;
  scope: DocTypeScope;
  o_que: string;
  pra_que: string;
  quando: string;
  fontes: string;
}

export const DOC_TYPES: Record<DocTypeKey, DocTypeMeta> = {
  sprint_status: {
    key: "sprint_status",
    label: "Repasse Semanal",
    icone: "📊",
    scope: "sprint",
    o_que: "Status executivo de uma sprint específica, com o que foi concluído, o que está em andamento e o que está bloqueado.",
    pra_que: "Comunicar progresso da sprint ao líder estratégico e ao cliente — leitura rápida com o foco do momento.",
    quando: "Ao final de cada sprint (semanal/quinzenal), ou antes de uma reunião de status com o cliente.",
    fontes: "Planning + Dailys + ingestões livres da sprint selecionada.",
  },
  sprint_retro: {
    key: "sprint_retro",
    label: "Retrospectiva",
    icone: "🔁",
    scope: "sprint",
    o_que: "Ata de reunião de retrospectiva de uma sprint, com tópicos discutidos, decisões e outputs.",
    pra_que: "Registrar de forma formal o que foi alinhado na retro, pra que decisões não se percam entre sprints.",
    quando: "Depois de uma reunião de retrospectiva da sprint.",
    fontes: "Todas as ingestões da sprint selecionada (planning, dailys, review, uploads livres).",
  },
  ata_reuniao: {
    key: "ata_reuniao",
    label: "Ata de Reunião",
    icone: "📝",
    scope: "ingestion",
    o_que: "Ata formal de uma reunião específica, com tópicos, decisões, outcomes e outputs.",
    pra_que: "Documentar decisões tomadas em reuniões importantes (alinhamento com cliente, kickoff, etc.).",
    quando: "Logo após uma reunião — você sobe a transcrição ou PDF da pauta e gera a ata.",
    fontes: "Uma ingestão específica que contenha a transcrição ou pauta da reunião.",
  },
  decisoes: {
    key: "decisoes",
    label: "Log de Decisões",
    icone: "🧭",
    scope: "project",
    o_que: "Lista cronológica de todas as decisões técnicas e de escopo tomadas ao longo do projeto.",
    pra_que: "Manter rastreabilidade do porquê das escolhas — útil em handoffs e revisões pós-projeto.",
    quando: "A qualquer momento; ideal antes de virar uma nova milestone ou quando o time vai mudar.",
    fontes: "Todas as ingestões do projeto, ordenadas por sprint.",
  },
  adr: {
    key: "adr",
    label: "ADRs",
    icone: "📐",
    scope: "project",
    o_que: "Conjunto de Architecture Decision Records — uma seção por decisão arquitetural, com contexto, motivo e consequências.",
    pra_que: "Formalizar decisões técnicas no formato de mercado (ADR), inclusive migrações de tecnologia entre sprints.",
    quando: "Quando o projeto está maduro e dá pra olhar pra trás e formalizar as escolhas técnicas.",
    fontes: "Todas as ingestões do projeto; o sistema detecta automaticamente migrações de stack entre sprints.",
  },
  onboarding: {
    key: "onboarding",
    label: "Onboarding",
    icone: "🎒",
    scope: "project",
    o_que: "Guia completo pra quem vai assumir o projeto: o que é, contexto do cliente, stack atual, decisões importantes, próximos passos.",
    pra_que: "Reduzir o tempo de ramp-up de um novo gerente ou analista entrando no projeto.",
    quando: "Antes de trocar de gerente, no início da gestão, ou pra integrar um novo analista ao projeto.",
    fontes: "Todas as ingestões do projeto. A sprint mais recente define o estado ATUAL.",
  },
  completo: {
    key: "completo",
    label: "Documentação Final",
    icone: "📚",
    scope: "project",
    o_que: "Documentação oficial completa do projeto no template do CITi: overview, arquitetura, dados, qualidade, deploy e glossário.",
    pra_que: "Entregar ao cliente como artefato final do projeto — o documento de fechamento.",
    quando: "Ao final do projeto, antes da entrega oficial ao cliente.",
    fontes: "Todas as ingestões do projeto, com prioridade pra estado da sprint mais recente.",
  },
  planning: {
    key: "planning",
    label: "Planning",
    icone: "🗓️",
    scope: "hybrid",
    o_que: "Documento de Planning de uma sprint — backlog, objetivos, responsabilidades e riscos previstos.",
    pra_que: "Formalizar o que a sprint pretende entregar e em que condições.",
    quando: "No início de cada sprint, após a reunião de planning.",
    fontes: "Formulário estruturado (descrição + itens do backlog) + PDF anexo opcional. Acessar pelo card de sprint → + Planning.",
  },
  daily: {
    key: "daily",
    label: "Daily",
    icone: "☀️",
    scope: "hybrid",
    o_que: "Registro estruturado de uma daily — o que foi feito, o que será feito e impedimentos.",
    pra_que: "Manter histórico do andamento dia a dia, com formato consistente entre dailys.",
    quando: "Após cada daily — frequência idealmente diária, mas recomendado se puder.",
    fontes: "Formulário estruturado (data + 3 perguntas) + PDF anexo opcional (ex: transcrição). Acessar pelo card de sprint → + Daily.",
  },
  review: {
    key: "review",
    label: "Review",
    icone: "🔎",
    scope: "hybrid",
    o_que: "Review de sprint comparando o que foi planejado vs. o que foi efetivamente entregue (delta).",
    pra_que: "Explicitar diferenças entre planning e execução, gerar aprendizados pra próxima sprint.",
    quando: "Ao final de cada sprint, antes da retrospectiva.",
    fontes: "Planning da sprint + dailys + ingestões livres da sprint + observações do gerente. Acessar pelo card de sprint → + Review.",
  },
};

export function docTypeLabel(key: string): string {
  return (DOC_TYPES as Record<string, DocTypeMeta>)[key]?.label ?? key;
}
