# Spec 12 — Discovery: reuniões, requisitos cumulativos e contexto compartilhado

**Prioridade:** alta · **Depende de:** nada obrigatório (a Spec 11 cria a subárea `produto` e o encaminhamento; isto funciona em qualquer subárea) · **Bloqueia:** UI da aba Requisitos, opções de solução, documentos de Discovery
**Origem:** integração com o Agente Diagnóstico (plano: `Agente-Diagnostico/PLANO_INTEGRACAO_DOCUDATA.md`). Decisões do usuário em 2026-10-12.

## Problema

O Discovery acontece em várias reuniões de natureza diferente (contexto da empresa, entrevista técnica, validação…). Cada uma acrescenta pedaços de um escopo maior.
Hoje cada reunião do Agente Diagnóstico termina isolada. É preciso um **registro único e cumulativo**: o que se descobre em cada reunião vira **requisitos** que ganham
evidências ao longo do tempo, são revisados por pessoas e, depois de validados, viram o escopo do Delivery. Todo agente deve poder ler o contexto inteiro.

## Escopo

### 1. Modelo de dados (migration v9; tabelas **próprias**, aditivas)
Não alterar `ingestions` (tem `sprint_number NOT NULL`; Discovery não tem sprint) nem `funcionalidades` (continua sendo o escopo **validado**).
SQL entregue como bloco comentado + preflight, idempotente, sem `DROP`. Todas as FKs para `projects` com `ON DELETE CASCADE`.

- `discovery_reunioes`: `id`, `project_id`, `tipo` (`contexto_empresa`|`entrevista_tecnica`|`validacao`|`outra`), `origem` (`agente_diagnostico`|`manual`),
  `fonte_session_id uuid` (único quando não nulo → idempotência), `ocorrida_em`, `conteudo_estruturado jsonb` (resumo, decisões, problemas, contexto do cliente,
  áreas cobertas, red flags, perguntas respondidas), `analise_status` (`pendente`|`ok`|`falhou`), `analise_erro text` (mensagem genérica, sem payload), `created_at`.
- `discovery_transcricoes`: `reuniao_id` (único, FK), `conteudo text`, `tamanho int`, `redigida boolean`, `expira_em timestamptz NULL`, `created_at`.
  Tabela separada de propósito: nunca entra em listagem nem `select("*")`.
- `requisitos`: `id`, `project_id`, `codigo` (RQ-001, único por projeto), `titulo`, `descricao`,
  `tipo` (`funcional`|`dados`|`integracao`|`nao_funcional`|`regra_negocio`), `lente` (`produto`|`dados`|NULL), `criterios_aceite text[]` (Dado/Quando/Então),
  `prioridade_sugerida` (`must`|`should`|`could`|`wont`), `justificativa`, `status` (`proposto`|`em_revisao`|`validado`|`rejeitado`), `motivo_decisao`,
  `possivel_duplicata_de uuid NULL`, `conflito boolean`, `revisado_por`, `validado_por`, `funcionalidade_id uuid NULL`, `created_at`, `updated_at`.
- `requisito_evidencias`: `id`, `requisito_id`, `reuniao_id`, `trecho text`, `speaker`, `confianca` (0–1), `created_at`. Muitas reuniões ↔ muitos requisitos.
- `requisito_transicoes`: `id`, `requisito_id`, `campo`, `de`, `para`, `autor`, `motivo`, `timestamp` (mesmo desenho de `transicoes_status`).
- Índices só onde há query real: `(project_id, status)` em `requisitos`; `(requisito_id)` em evidências; `(project_id, ocorrida_em DESC)` em reuniões.

### 2. Entrada de reuniões (serviço a serviço)
`POST /discovery/reunioes` protegido por **chave de serviço dedicada** (`DOCUDATA_DISCOVERY_KEY`, comparação em tempo constante; **não** reusar `DOCUDATA_APP_SECRET`).
- Corpo: `docudata_project_id`, `fonte_session_id`, `tipo`, `ocorrida_em`, `conteudo_estruturado`, `transcricao` (texto inteiro, opcional).
- O projeto é **carregado no servidor** e validado (existência; a subárea vem do banco, nunca do corpo).
- **Idempotente** por `fonte_session_id`: reenviar devolve a reunião existente (200) sem duplicar reunião, transcrição, requisitos nem chamada Gemini.
- **Limites antes de carregar tudo:** corpo máximo (transcrição ≤ 2 MB, `413` acima), rate limit como nos demais ingests. Texto delimitado e **redigido de segredos** antes de ir ao modelo e antes de gravar (§5.3 do `AGENTS.md`).
- Grava a reunião e a transcrição e dispara a análise em **segundo plano**; responde `202` com o `id` e `analise_status = pendente`.

### 3. Análise cumulativa (abordagem C: incremental + reconsolidar)
`graphs/requisitos_graph.py` (LangGraph; chave via `services/gemini_key.py`; padrão do `import_graph.py`: critérios em Dado/Quando/Então, retry com JSON endurecido, no máximo 2 tentativas).
- **Entrada:** a reunião nova (`tipo` muda o foco: contexto → processo atual, dores, atores; entrevista técnica → integrações, dados, volumetria, restrições; validação → o que foi aceito ou contestado),
  o `conteudo_estruturado`, os trechos candidatos e a **lista compacta dos requisitos existentes** (`codigo`, título, descrição curta, status, prioridade, nº de evidências).
- **Saída validada por schema:** `novos[]`, `reforcos[{codigo, trecho, confianca}]`, `conflitos[{codigo, descricao}]`, `ajustes_prioridade[{codigo, prioridade, justificativa}]`.
- **Travas anti-alucinação (obrigatórias):**
  - candidato sem `trecho` de evidência é **descartado**;
  - o `trecho` precisa existir na reunião (comparação normalizada com o `conteudo_estruturado`/transcrição); senão é descartado;
  - requisito `validado` ou `rejeitado` **nunca é alterado automaticamente**: só recebe evidência e, se houver tensão, `conflito = true`;
  - dúvida de duplicata: cria o requisito novo em `em_revisao` com `possivel_duplicata_de`; **nunca funde em silêncio**.
- **Reconsolidar:** `POST /discovery/projetos/{id}/reconsolidar` (gerente+). Reanalisa as reuniões em ordem cronológica e **propõe** fusões e prioridades como itens `proposto`;
  não altera `validado`/`rejeitado`. Usa a transcrição inteira quando existir.
- Custo contido: o prompt incremental leva resumos e requisitos compactos, nunca todas as transcrições.

### 4. Revisão, validação e promoção
Cargos do DocuData (`operacional` < `gerente` < `lider` < `owner`); checado **no backend**, derivando o `project_id` do recurso.

| Ação | Cargo mínimo | Regra |
|---|---|---|
| Listar/ver requisitos e evidências | `operacional` com acesso ao projeto | sem transcrição |
| `proposto → em_revisao` (revisar) | `operacional` | registra `revisado_por` |
| `em_revisao → validado` | `gerente` | registra `validado_por` |
| `→ rejeitado` | `gerente` | `motivo_decisao` **obrigatório** |
| reabrir (`rejeitado → proposto`) | `gerente` | motivo |
| editar título/descrição/critérios | `operacional` (antes de validar), `gerente` (sempre) | grava transição |
| **promover** `validado → funcionalidade` | `gerente` | cria a `funcionalidade` (`id_funcional`, título, descrição, critérios, prioridade) e preenche `funcionalidade_id`; idempotente |
| ler a transcrição | `gerente` | endpoint próprio, nunca em listagem, nunca em log |

Toda mudança grava `requisito_transicoes` (autor, de, para, motivo).

### 5. Contexto para os agentes
**O contexto é do projeto, não da subárea.** Quando o projeto é encaminhado de Produto para Dados/Dev (Spec 11 §6), reuniões, requisitos, evidências e este contexto
**continuam acessíveis** no destino, com os cargos do destino. O serviço de promoção `promover_requisito(requisito_id)` é único e idempotente: é usado pela rota de promoção e pelo encaminhamento (`promover_validados`).

`GET /discovery/projetos/{id}/contexto` (serviço a serviço **e** autenticado): devolve o contexto compilado — resumo por reunião (tipo, data), requisitos com status e prioridade
(inclusive os **rejeitados com motivo**, para o agente não re-sugerir), conflitos e dúvidas abertas. **Sem transcrição bruta.** Tamanho limitado (resumos, não trechos).
`services/discovery_contexto.py` é a única função que compila isso; os grafos futuros (opções de solução, documentos) só leem por ela.

### 6. Transcrição inteira — política
Guardada em `discovery_transcricoes`; só `gerente`+ lê; teto de 2 MB; redigida de segredos; fora de listagens e logs. `expira_em` existe e é nulo por padrão:
**o prazo de retenção é decisão do time** (LGPD), sem job de descarte nesta spec.

## Não faz parte

- UI da aba Requisitos (spec seguinte).
- Opções de solução, documentos de Discovery (diagnóstico, desenho da solução, business case, PRD) e BPMN.
- O lado do Agente Diagnóstico (cliente, vínculo de projeto, envio no encerramento): plano no repositório do Agente.
- Job de retenção/descarte de transcrição; busca semântica; qualquer troca de modelo.
- Alterar `ingestions`, `funcionalidades` existentes ou o motor de score.

## Riscos

- Alucinação de requisito; duplicação a cada reunião; deriva do modelo incremental → travas do §3 e o botão de reconsolidar.
- Dado pessoal (transcrição inteira) → política do §6, acesso `gerente`+, redação e teto.
- Chave de serviço aceitando projeto errado → projeto carregado no servidor; chave dedicada, rotacionável.
- Reenvio duplicando → idempotência por `fonte_session_id` e promoção idempotente.
- Custo Gemini crescendo → contexto compacto; análise em segundo plano com `analise_status` e retentativa explícita.
- Colisão com a Spec 10 → migration v9 só depois de conferir a numeração.

## Ações humanas externas (o agente NÃO faz)

1. Rodar preflight e migration v9 no SQL Editor do Supabase.
2. Definir `DOCUDATA_DISCOVERY_KEY` no Railway (valor forte e novo; nunca no chat) e entregar o mesmo valor ao Agente.
3. Decidir o **prazo de retenção** da transcrição.
4. Confirmar se `operacional` enxerga a aba de Requisitos (a spec da UI depende disso).

## Testes (mocks; sem Supabase nem Gemini reais)

RBAC por cargo e por projeto (operacional não valida; sem acesso ao projeto = 403/404); chave de serviço ausente/errada = 401; idempotência por `fonte_session_id`;
`413` acima do teto; redação de segredos; grafo: descarta candidato sem evidência e com trecho inexistente, reforça requisito existente sem duplicar, marca duplicata duvidosa,
não altera `validado`/`rejeitado`; transições e `motivo` obrigatório na rejeição; promoção cria `funcionalidade` uma vez; `contexto` sem transcrição e com rejeitados;
reconsolidar só propõe. Semente: ao menos um teste por módulo novo.

## Critérios de aceite

- [ ] Migration v9 comentada, idempotente, aditiva, com preflight e rollback.
- [ ] `POST /discovery/reunioes` idempotente, com limites, chave dedicada e projeto validado no servidor.
- [ ] Segunda reunião **reforça** requisito existente sem duplicá-lo; candidato sem evidência é descartado.
- [ ] Fluxo `proposto → em_revisao → validado → promovido` respeita os cargos; rejeitar exige motivo; tudo em `requisito_transicoes`.
- [ ] Promoção cria a `funcionalidade` uma única vez, ligando `funcionalidade_id`.
- [ ] Transcrição nunca aparece em listagem nem log; só `gerente`+ a lê.
- [ ] `GET .../contexto` entrega o contexto cumulativo sem transcrição bruta.
- [ ] Após o encaminhamento (Spec 11 §6), requisitos, reuniões e contexto seguem acessíveis no destino; `promover_requisito` é compartilhado com o encaminhamento.
- [ ] `python -m pytest` verde; `git diff --check` limpo; gates externos reportados como pendentes.
