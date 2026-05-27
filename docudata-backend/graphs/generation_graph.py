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
    observacoes: Optional[str]
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

    "adr": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto acumulado de todas as ingestões abaixo, gere um conjunto de ADRs (Architecture Decision Records) para o projeto "{projeto_nome}" (cliente: {cliente}).

Gere um ADR numerado para cada decisão técnica ou arquitetural significativa identificada.
Se a seção MUDANÇAS DETECTADAS ENTRE SPRINTS indicar troca de tecnologia entre sprints consecutivas, gere um ADR dedicado para essa migração — use as ingestões intermediárias para reconstruir o contexto e o motivo da troca.

Regras:
- Um ADR por decisão — não agrupe múltiplas decisões em um único ADR
- Ordene cronologicamente pela sprint onde a decisão foi tomada
- Se não houver informação suficiente para um campo, escreva "[Não identificado no contexto]"
- Nunca invente informações

Para cada ADR use EXATAMENTE este formato:

---

## ADR-[NNN] — [Título da Decisão]

**Status:** Aceito
**Sprint:** [número]
**Data:** [data se identificada no contexto, ou N/D]

### Contexto

[O que estava acontecendo no projeto que forçou essa decisão — problema, restrição ou pressão que precisava ser resolvida.]

### Decisão

[O que foi decidido. Uma frase direta.]

### Motivo

[Por que essa opção foi escolhida. Se houver alternativas consideradas e descartadas, mencione-as.]

### Consequências

[O que muda como resultado desta decisão.]
- **Positivo:** [o que fica mais fácil ou mais robusto]
- **Negativo:** [o que é sacrificado ou fica mais difícil]
- **Neutro:** [o que precisa ser feito por causa desta decisão]

---

*Documento gerado automaticamente pelo Agente Documentador — CITi · Centro de Informática, UFPE*

---
Contexto de todas as ingestões do projeto:
{contexto}""",

    "onboarding": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto acumulado de todas as ingestões abaixo, gere um documento de Onboarding para o projeto "{projeto_nome}" (cliente: {cliente}).

Este documento é destinado a um novo gerente ou analista que vai assumir o projeto. Deve ser suficiente para que a pessoa entenda completamente o projeto sem precisar perguntar a ninguém.

IMPORTANTE: Se o contexto contiver dados de múltiplas sprints, use os dados da sprint mais recente para descrever o estado ATUAL. Dados de sprints anteriores são contexto histórico. Se a seção de MUDANÇAS DETECTADAS indicar que algo foi removido ou substituído, não inclua o item antigo como ativo.

Siga EXATAMENTE esta estrutura em markdown:

# Onboarding — {projeto_nome}
**Cliente:** {cliente}
**Data do documento:** [Data mais recente encontrada no contexto, ou data de hoje]

---

## O que é este projeto

[Parágrafo curto e direto: o que o projeto faz, qual problema resolve para o cliente, qual é o entregável principal. Alguém que nunca ouviu falar do projeto deve entender em 30 segundos.]

## Contexto do cliente

[Quem é o cliente, o que eles fazem, por que precisam deste projeto. Se identificado no contexto: urgência, visibilidade, critérios que o cliente prioriza.]

## O que já foi feito

| Sprint | Principais entregas | Estado |
|---|---|---|
| Sprint [N] | [Entregas desta sprint extraídas do contexto] | Concluído |

[Parágrafo final: onde o projeto está AGORA — o que está em andamento, o que falta, estado geral.]

## Stack atual

| Tecnologia | Para que serve neste projeto |
|---|---|
| [Tecnologia da sprint mais recente] | [Uso específico] |

[Use apenas tecnologias da sprint mais recente. Se houve troca de tecnologia, mencione apenas a atual e indique a troca em "Decisões importantes".]

## Decisões importantes que você precisa saber

- **[Decisão]:** [Por que foi tomada — sem essa informação, o novo gerente pode reverter algo por engano]

(Inclua especialmente decisões de escopo, mudanças de rota e escolhas técnicas com motivação conhecida)

## Problemas que apareceram

- **[Problema]:** [Como foi resolvido, ou status atual se ainda aberto]

## Próximos passos imediatos

[Ordem de prioridade clara do que precisa ser feito. A pessoa que acabou de entrar deve saber exatamente o que fazer na primeira semana.]

1. [Ação imediata]
2. [Segunda prioridade]

## Quem contatar

- **Time CITi:** [Nomes identificados no contexto, ou: verificar com o coordenador de dados]
- **Cliente:** [Contato do cliente se identificado no contexto, ou: verificar com o gerente anterior]

---

*Documento gerado automaticamente pelo Agente Documentador — CITi · Centro de Informática, UFPE*

---
Contexto de todas as ingestões do projeto:
{contexto}""",

    "completo": """Você é um assistente de documentação do CITi — Centro Integrado de Tecnologia da Informação (UFPE).
Com base no contexto acumulado de todas as ingestões abaixo, gere a Documentação Final do Projeto "{projeto_nome}" (cliente: {cliente}), seguindo o template oficial do CITi.

Instruções gerais:
- Preencha cada seção com o máximo de informação extraível do contexto.
- Se uma subseção não tiver dados suficientes (ex: não há modelo de IA no projeto), escreva "[Não aplicável a este projeto]" — nunca invente informações.
- Use linguagem técnica e objetiva. O documento será entregue ao cliente.
- Escreva em português.
- IMPORTANTE: Use os dados da sprint mais recente para descrever o estado ATUAL do projeto. Se a seção de MUDANÇAS DETECTADAS indicar que algo foi removido ou substituído, não inclua o item antigo como ativo — use apenas o estado mais recente.

Siga EXATAMENTE esta estrutura em markdown:

# Documentação Final do Projeto
## {projeto_nome}
**Cliente:** {cliente}
**Versão:** 1.0
**Data:** [Data mais recente encontrada no contexto]

---

## 1. Overview

[Parágrafo introdutório resumindo o projeto: o que é, qual problema resolve, qual o valor entregue ao cliente.]

### 1.1. Definição

[Descrição clara e objetiva do que é o projeto em uma ou duas frases.]

### 1.2. Escopo

[O que está dentro do escopo do projeto — funcionalidades, entregas e fronteiras. Use lista com marcadores.]

### 1.3. Dores do cliente e Objetivos

**Dores identificadas:**
- [Problema ou necessidade do cliente identificada nas ingestões]

**Objetivos do projeto:**
- [Objetivo mensurável que o projeto entrega]

### 1.4. Cronograma detalhado

| Sprint | Período | Entregas principais | Status |
|---|---|---|---|
| Sprint [N] | [Datas inferidas ou N/D] | [Tarefas da sprint extraídas do contexto] | [Concluído / Em andamento / Planejado] |

### 1.5. Responsáveis e atribuições

| Papel | Responsabilidade |
|---|---|
| Gerente de Dados — CITi | Gestão do projeto, comunicação com o cliente, entrega das sprints |
| Analista de Dados — CITi | [Responsabilidades identificadas no contexto] |
| Representante — {cliente} | Validações, fornecimento de dados e acesso aos sistemas |

---

## 2. Arquitetura da Solução

[Parágrafo descrevendo a abordagem técnica geral do projeto.]

### 2.1. Requisitos Funcionais e Não Funcionais

**Funcionais:**
- [Requisito funcional identificado no contexto]

**Não funcionais:**
- [Requisito de performance, segurança, disponibilidade ou escalabilidade identificado]

### 2.2. Tecnologias e Ferramentas do Projeto

| Tecnologia/Ferramenta | Finalidade |
|---|---|
| [Tecnologia extraída das ingestões] | [Para que é usada no projeto] |

### 2.3. Metodologia

Scrum adaptado com sprints semanais ou quinzenais. [Complemente com informações do contexto sobre frequência e formato das sprints.]

### 2.4. Rituais da Equipe e Meios de Comunicação

- **Daily / Sync:** [Frequência e canal identificados no contexto, ou: A definir]
- **Repasse semanal com cliente:** [Canal e dia identificados, ou: Google Meet — dia a definir]
- **Comunicação assíncrona:** [Ferramenta identificada no contexto, ou: WhatsApp / e-mail]

### 2.5. Decisões Estratégicas do Projeto

- [Decisão técnica ou de escopo tomada ao longo do projeto, identificada nas ingestões]

---

## 3. Projeto de Dados

[Parágrafo descrevendo como os dados são armazenados, gerenciados e processados.]

### 3.1. Estrutura de Banco de Dados

[Descreva as tabelas, coleções ou estruturas de dados identificadas no contexto. Se não houver detalhe, descreva o banco de dados usado e seu propósito.]

### 3.2. Diagrama de Fluxo de Dados / Data Lineage

[Descreva em texto o fluxo: fonte dos dados → transformações → destino/saída. Use setas (→) para representar o fluxo.]

Exemplo extraído do contexto:
[Fonte de dados] → [Processamento/ETL] → [Destino ou visualização]

### 3.3. Automações

- [Automação identificada no contexto — ex: pipeline agendado, trigger, job recorrente]

---

## 4. Qualidade de Dados

[Parágrafo introdutório sobre a abordagem de qualidade adotada no projeto.]

### 4.1. Dicionário de Dados

| Campo | Tipo | Descrição | Regra de negócio |
|---|---|---|---|
| [Campo identificado no contexto] | [Tipo] | [Descrição] | [Regra se houver] |

### 4.2. Arquitetura de Pipeline de ETL

[Descreva as etapas de extração, transformação e carga identificadas no contexto.]

- **Extração:** [Fonte e método]
- **Transformação:** [Limpeza, normalização, cálculos aplicados]
- **Carga:** [Destino final dos dados tratados]

### 4.3. Regras de Qualidade de Dados

- [Regra de validação identificada — ex: campos obrigatórios, formatos esperados, tratamento de nulos]

### 4.4. Credenciais dos Dados (ENVs e Keys)

As credenciais de acesso aos sistemas e bancos de dados estão armazenadas como variáveis de ambiente e não são expostas neste documento. [Liste os sistemas que requerem credenciais, sem expor valores.]

---

## 5. Design de Interfaces

[Descreva como as partes do sistema se comunicam entre si e com sistemas externos.]

### 5.1. Formatos de Estruturas de Dados

[Descreva os formatos de dados trocados entre componentes — ex: JSON, CSV, DataFrame, API response.]

### 5.2. Protocolos e Especificações das APIs

[Liste APIs externas ou internas usadas, com endpoint principal e finalidade, se identificados no contexto.]

---

## 6. Documentação de Modelo

[Inclua esta seção apenas se o projeto envolver modelo preditivo ou agente de IA. Caso contrário: "Não aplicável a este projeto."]

### 6.1. Definição do Modelo de Ciência de Dados

[Descreva o tipo de modelo, o problema que resolve e o output esperado.]

### 6.2. Algoritmos e Parâmetros

[Liste algoritmos usados e principais hiperparâmetros ou configurações.]

### 6.3. Métricas de Desempenho e Testes

[Liste as métricas de avaliação usadas e os resultados obtidos, se disponíveis no contexto.]

---

## 7. Interface do Usuário

[Inclua se o projeto tiver frontend ou dashboard. Caso contrário: "Não aplicável a este projeto."]

### 7.1. Fluxos de Trabalho e Interação

[Descreva o fluxo principal do usuário dentro do sistema.]

### 7.2. Modelos de Telas Principais

[Descreva as telas ou visualizações principais em texto — ex: Dashboard de vendas com filtros por período e região.]

### 7.3. User Stories

- **Como** [tipo de usuário], **quero** [ação], **para** [benefício].

---

## 8. Deploy

### 8.1. Organização do Deploy

[Descreva onde e como o projeto é deployado — ex: cloud, on-premise, ferramenta de BI, script agendado.]

| Componente | Ambiente | Tecnologia |
|---|---|---|
| [Componente] | [Produção / Homologação] | [Tecnologia identificada] |

### 8.2. Manutenção do Deploy

[Descreva a frequência e responsável pela manutenção. Ex: manutenção quinzenal pelo time CITi, com comunicação prévia ao cliente.]

---

## 9. Glossário

| Termo | Definição |
|---|---|
| [Termo técnico identificado no contexto] | [Definição clara para o cliente] |

---

*Documento gerado automaticamente pelo Agente Documentador — CITi · Centro de Informática, UFPE*

---
Contexto de todas as ingestões do projeto:
{contexto}""",
}


def _detect_changes(ingestions: list) -> str:
    """Compare consecutive sprints to track exactly when each technology change happened."""
    sprints = sorted({ing.get("sprint_number", 0) for ing in ingestions})
    if len(sprints) < 2:
        return ""

    def get_techs(sprint_num: int) -> set[str]:
        result: set[str] = set()
        for ing in ingestions:
            if ing.get("sprint_number") == sprint_num:
                for t in (ing.get("extracted_content") or {}).get("tecnologias") or []:
                    result.add(t.lower())
        return result

    changes_by_transition: list[tuple] = []
    prev_techs = get_techs(sprints[0])
    for i in range(1, len(sprints)):
        curr_techs = get_techs(sprints[i])
        added = curr_techs - prev_techs
        removed = prev_techs - curr_techs
        if added or removed:
            changes_by_transition.append((sprints[i - 1], sprints[i], added, removed))
        prev_techs = curr_techs

    if not changes_by_transition:
        return ""

    lines = [
        "--- MUDANÇAS DETECTADAS ENTRE SPRINTS ---",
        "ATENÇÃO PARA O MODELO: Use o estado da sprint mais recente como ESTADO ATUAL.",
    ]
    for s_from, s_to, added, removed in changes_by_transition:
        parts = [f"Sprint {s_from} → Sprint {s_to}:"]
        if added:
            parts.append(f"adicionado: {', '.join(sorted(added))}")
        if removed:
            parts.append(f"removido: {', '.join(sorted(removed))}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


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
    elif tipo_doc in ("sprint_status", "sprint_retro", "decisoes"):
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

    changes = _detect_changes(state["ingestions"])
    if changes:
        partes.append(changes)

    contexto = "\n\n".join(partes) if partes else "Nenhuma ingestão encontrada para este projeto/sprint."
    return {"contexto": contexto}


async def gerar_documento(state: GenerationState) -> dict:
    template = _PROMPTS[state["tipo_doc"]]
    prompt = ChatPromptTemplate.from_template(template)
    llm = _make_llm(state["gemini_api_key"])

    contexto = state["contexto"]
    obs = (state.get("observacoes") or "").strip()
    if obs:
        contexto = contexto + f"\n\n--- Observações adicionais do gerente ---\n{obs}"

    formatted = await prompt.ainvoke({
        "projeto_nome": state["projeto_nome"],
        "cliente": state["cliente"],
        "sprint_numero": state.get("sprint_numero"),
        "contexto": contexto,
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
