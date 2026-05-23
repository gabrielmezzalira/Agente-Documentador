import os
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from services.supabase_client import get_client

_COST_PER_INPUT_TOKEN = 0.15 / 1_000_000   # USD — Gemini 2.5 Flash
_COST_PER_OUTPUT_TOKEN = 0.60 / 1_000_000  # USD — Gemini 2.5 Flash


class GenerationState(TypedDict):
    projeto_id: str
    projeto_nome: str
    cliente: str
    tipo_doc: str
    sprint_numero: Optional[int]
    ingestion_id: Optional[str]
    gemini_api_key: str
    ingestions: list
    contexto: str
    documento: str
    input_tokens: int
    output_tokens: int


def _make_llm(api_key: str):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=4096,
        google_api_key=api_key,
    )

_PROMPTS = {
    "sprint_status": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto das ingestões abaixo, gere um Repasse Semanal da Sprint {sprint_numero} para o projeto "{projeto_nome}" (cliente: {cliente}).

Siga EXATAMENTE esta estrutura em markdown:

**DATA:** [Infira a data mais recente mencionada no contexto, ou escreva a data de hoje se não houver referência]
**TÓPICO:** [Título resumido do repasse — ex: "Avanços na Pipeline e Início da Automação"]

## Resumo da Semana

[Parágrafo narrativo: visão geral do que foi feito na sprint, sentimento geral, maior conquista ou maior bloqueio, contexto do foco da equipe. Escreva de forma que o cliente ou diretor entenda o estado do projeto lendo apenas este parágrafo.]

## Principais Pontos

- [Funcionalidade/artefato/etapa concluída] — **Concluído**
- [Funcionalidade/artefato/etapa em progresso] — **Em andamento**
- [Se houver bloqueio] — **Bloqueado** — [motivo breve]

(Use os status: Concluído, Em andamento, Em validação, Bloqueado, Cancelado)

## Decisões Tomadas

- [Decisão técnica ou de escopo tomada nesta sprint]
- [Mudanças de rota, escolhas técnicas, alinhamentos com cliente que impactam o futuro]

## Próximos Passos

- [Ação prioritária para a próxima semana]
- [O que precisa estar pronto até o próximo repasse]

Atenciosamente,
Gerente de Dados — CITi · Centro de Informática, UFPE

---
Contexto das ingestões da Sprint {sprint_numero}:
{contexto}""",

    "sprint_retro": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto das ingestões abaixo, gere uma Ata de Reunião da Sprint {sprint_numero} para o projeto "{projeto_nome}" (cliente: {cliente}).

Siga EXATAMENTE esta estrutura em markdown:

**DATA:** [Infira a data mais recente mencionada no contexto, ou escreva a data de hoje]
**TÓPICO:** [Tema central da reunião — ex: "Alinhamento de Cronograma e Validação do Tratamento"]
**ANDAMENTO:** [Uma frase descrevendo o estado geral do desenvolvimento nesta sprint.]

**PARTICIPANTES – CARGO:**
- [Nome inferido do contexto] – [Cargo/Papel] (se não houver nomes: Gerente de Dados – CITi; Analista de Dados – CITi; Representante – {cliente})

## Tópicos discutidos

1. **[Nome do Tópico]:** [Resumo narrativo do ponto central da discussão e argumentos principais.]
2. **[Nome do Tópico]:** [Resumo.]

## Decisões tomadas

- [Decisão concreta com verbo no infinitivo: Manter, Iniciar, Cancelar, Adiar]
- [Alinhamentos que impactam o futuro do projeto — esta é a parte mais crítica: se o cliente concordou com algo, deve constar aqui]

## Outcomes da reunião

- [Resultado estratégico conquistado — ex: "Alinhamento de expectativas sobre a entrega final"]
- [Entendimento compartilhado gerado pela reunião]

## Outputs da reunião

- [Entregável tangível gerado — ex: "Novo cronograma atualizado", "Lista de acessos pendentes enviada ao cliente"]

## Conclusão

[Parágrafo executivo de fechamento: se alguém não ler a ata toda, este parágrafo deve resumir como está o projeto e qual é o foco imediato agora.]

Atenciosamente,
Gerente de Dados — CITi · Centro de Informática, UFPE

---
Contexto das ingestões da Sprint {sprint_numero}:
{contexto}""",

    "decisoes": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto abaixo, gere um Log de Decisões Técnicas completo do projeto "{projeto_nome}" (cliente: {cliente}).

O documento deve ter o seguinte formato em markdown:

## Log de Decisões Técnicas — {projeto_nome}

Para cada decisão identificada, use este formato:

**Sprint X — [Decisão tomada]**
Motivo: [justificativa da decisão]

Liste em ordem cronológica por sprint. Inclua decisões técnicas, de escopo, de arquitetura e alinhamentos com o cliente que impactam o projeto.

Contexto de todas as ingestões do projeto:
{contexto}""",

    "ata_reuniao": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base na transcrição ou documento de reunião abaixo, gere uma Ata de Reunião formal para o projeto "{projeto_nome}" (cliente: {cliente}).

Siga EXATAMENTE esta estrutura em markdown:

**DATA:** [Infira a data da reunião do contexto, ou escreva a data de hoje se não houver referência]
**TÓPICO:** [Tema central da reunião — ex: "Alinhamento de Pipeline e Validação de Dados"]
**ANDAMENTO:** [Uma frase objetiva descrevendo o estado geral do projeto no momento da reunião]

**PARTICIPANTES – CARGO:**
- [Nome identificado] – [Cargo/Papel] (se não houver nomes explícitos: Gerente de Dados – CITi; Analista de Dados – CITi; Representante do Cliente – {cliente})

## Tópicos discutidos

1. **[Nome do Tópico]:** [Resumo narrativo do ponto central discutido, argumentos apresentados e conclusão parcial do tópico.]
2. **[Nome do Tópico]:** [Resumo narrativo.]

(Liste todos os tópicos relevantes identificados na transcrição)

## Decisões tomadas

- [Decisão com verbo no infinitivo: Manter, Iniciar, Cancelar, Adiar, Priorizar — esta é a parte mais crítica da ata]
- [Se o cliente concordou com algo ou validou uma entrega, deve constar aqui explicitamente]

## Outcomes da reunião

- [Resultado estratégico conquistado pela reunião — ex: "Alinhamento de expectativas sobre o escopo da entrega 3"]
- [Entendimento compartilhado gerado — algo que agora todos sabem e antes estava implícito]

## Outputs da reunião

- [Entregável tangível gerado ou acordado — ex: "Novo cronograma atualizado", "Lista de pendências enviada ao cliente", "Documento de requisitos aprovado"]

## Conclusão

[Parágrafo executivo de fechamento: se alguém não ler a ata inteira, este parágrafo deve resumir o estado atual do projeto e o foco imediato após esta reunião. Escreva de forma que cliente e gestão entendam o que foi decidido e o que vem a seguir.]

Atenciosamente,
Gerente de Dados — CITi · Centro de Informática, UFPE

---
Transcrição / documento da reunião:
{contexto}""",

    "completo": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto das ingestões abaixo, gere um Cronograma de Entregas Contínuas completo do projeto "{projeto_nome}" (cliente: {cliente}).

Siga EXATAMENTE esta estrutura em markdown:

**DATA:** [Data mais recente encontrada no contexto]
**TÓPICO:** Alinhamento de Cronograma e Planejamento de Entregas — {projeto_nome}

## Objetivos deste Documento

[Parágrafo curto: explique que este documento dá transparência total sobre o andamento do projeto, serve como "contrato" de entregas mostrando o que já foi concluído e o plano para as próximas semanas, e será atualizado a cada nova entrega.]

## O Ritmo: Demonstrações e Rituais

- **Frequência:** [Infira do contexto, ou sugira: Semanal]
- **Canal:** [Infira do contexto, ou sugira: Reunião de 30min via Google Meet]
- **Dia/Hora:** [Infira do contexto, ou indique: A definir com o cliente]
- **Correções Críticas (Hotfixes):** Serão tratadas com prioridade e comunicadas imediatamente.

## Cronograma de Entregas (Roadmap)

### Entregas Concluídas ✅

| Task/Tarefa | Descrição | Status |
|---|---|---|
| [Tarefa concluída extraída do contexto] | [Descrição breve do que foi feito] | Entregue |

### Próximas Entregas ⏳

| Task/Tarefa | Descrição | Status |
|---|---|---|
| [Próxima tarefa inferida do contexto] | [Descrição breve] | A Fazer |
| [Tarefa futura] | [Descrição breve] | Em andamento |

## Alinhamento de Expectativas (Regras do Jogo)

- **[Subtítulo relevante ao projeto — ex: O que é uma "Entrega"?]:** [Explicação importante para o cliente entender o processo de entrega. Diferencie "demonstrar que funciona" de "colocar no ar".]

## Condições e Dependências (O que precisamos de você)

- **[Dependência identificada no contexto]:** [Descrição clara do que o cliente ou time precisa providenciar para o projeto avançar. Se não houver dependências claras no contexto, mencione acessos, validações ou aprovações típicas de projetos de dados.]

Atenciosamente,
Gerente de Dados — CITi · Centro de Informática, UFPE

---
Contexto de todas as ingestões do projeto:
{contexto}""",
}


def buscar_ingestions(state: GenerationState) -> dict:
    client = get_client()
    tipo_doc = state["tipo_doc"]

    if tipo_doc == "ata_reuniao":
        response = (
            client.table("ingestions")
            .select("*")
            .eq("id", state["ingestion_id"])
            .execute()
        )
    elif tipo_doc in ("sprint_status", "sprint_retro"):
        response = (
            client.table("ingestions")
            .select("*")
            .eq("project_id", state["projeto_id"])
            .eq("sprint_number", state["sprint_numero"])
            .execute()
        )
    else:
        response = (
            client.table("ingestions")
            .select("*")
            .eq("project_id", state["projeto_id"])
            .order("sprint_number", desc=False)
            .execute()
        )

    return {"ingestions": response.data or []}


def compilar_contexto(state: GenerationState) -> dict:
    partes = []
    for ing in state["ingestions"]:
        content = ing.get("extracted_content") or {}
        sprint = ing.get("sprint_number", "?")
        nome = ing.get("file_name", "arquivo")

        tarefas = ", ".join(content.get("tarefas") or [])
        decisoes = ", ".join(content.get("decisoes") or [])
        problemas = ", ".join(content.get("problemas") or [])
        proximos = ", ".join(content.get("proximos_passos") or [])

        partes.append(
            f"--- Sprint {sprint} | {nome} ---\n"
            f"Resumo: {content.get('resumo', '')}\n"
            f"Tarefas: {tarefas}\n"
            f"Decisoes: {decisoes}\n"
            f"Problemas: {problemas}\n"
            f"Contexto do cliente: {content.get('contexto_cliente', '')}\n"
            f"Proximos passos: {proximos}"
        )

    contexto = "\n\n".join(partes) if partes else "Nenhuma ingestão encontrada para este projeto/sprint."
    return {"contexto": contexto}


async def gerar_documento(state: GenerationState) -> dict:
    template = _PROMPTS[state["tipo_doc"]]
    prompt = ChatPromptTemplate.from_template(template)
    llm = _make_llm(state["gemini_api_key"])

    formatted = await prompt.ainvoke({
        "projeto_nome": state["projeto_nome"],
        "cliente": state["cliente"],
        "sprint_numero": state.get("sprint_numero"),
        "contexto": state["contexto"],
    })
    response = await llm.ainvoke(formatted)

    usage = getattr(response, "usage_metadata", None) or {}
    in_tok = usage.get("input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0

    return {
        "documento": response.content,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
    }


async def salvar_documento(state: GenerationState) -> dict:
    client = get_client()
    in_tok = state.get("input_tokens", 0) or 0
    out_tok = state.get("output_tokens", 0) or 0
    cost = in_tok * _COST_PER_INPUT_TOKEN + out_tok * _COST_PER_OUTPUT_TOKEN
    print(f"[salvar_documento] tokens in={in_tok} out={out_tok} cost=${cost:.6f}")
    response = (
        client.table("generated_docs")
        .insert({
            "project_id": state["projeto_id"],
            "doc_type": state["tipo_doc"],
            "sprint_number": state.get("sprint_numero"),
            "content": state["documento"],
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": round(cost, 8),
        })
        .execute()
    )
    if not response.data:
        raise RuntimeError("Failed to save generated document")
    return {}


_builder = StateGraph(GenerationState)
_builder.add_node("buscar_ingestions", buscar_ingestions)
_builder.add_node("compilar_contexto", compilar_contexto)
_builder.add_node("gerar_documento", gerar_documento)
_builder.add_node("salvar_documento", salvar_documento)

_builder.add_edge(START, "buscar_ingestions")
_builder.add_edge("buscar_ingestions", "compilar_contexto")
_builder.add_edge("compilar_contexto", "gerar_documento")
_builder.add_edge("gerar_documento", "salvar_documento")
_builder.add_edge("salvar_documento", END)

generation_graph = _builder.compile()
