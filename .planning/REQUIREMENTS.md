# Requirements: DocuData

**Defined:** 2026-05-22
**Core Value:** O fluxo de ingestão + geração precisa funcionar de ponta a ponta — subir um arquivo, extrair conteúdo estruturado e gerar um documento útil.

## v1 Requirements

### Projetos

- [ ] **PROJ-01**: Gerente pode criar projeto com nome, cliente e descrição
- [ ] **PROJ-02**: Gerente pode visualizar lista de projetos existentes
- [ ] **PROJ-03**: Gerente pode navegar para o dashboard de um projeto específico

### Ingestão

- [ ] **INGS-01**: Gerente pode fazer upload de arquivo (DOCX, PDF, TXT, PNG, JPG, WEBP) associado a um número de sprint
- [ ] **INGS-02**: Sistema exibe feedback de sucesso ou erro após o upload
- [ ] **INGS-03**: Gerente pode visualizar histórico de ingestões do projeto agrupado por sprint (nome do arquivo, data, resumo extraído)

### Extração

- [ ] **EXTR-01**: Sistema extrai conteúdo estruturado (6 campos: resumo, tarefas, decisoes, problemas, contexto_cliente, proximos_passos) via Gemini 2.5 Flash
- [ ] **EXTR-02**: Sistema processa arquivos de texto (DOCX, TXT) extraindo texto puro
- [ ] **EXTR-03**: Sistema processa PDFs com camada de texto via pdfplumber
- [ ] **EXTR-04**: Sistema processa imagens e PDFs escaneados via Gemini 2.5 Flash (visão multimodal)

### Geração

- [ ] **GERA-01**: Gerente pode gerar documento de Status da Sprint (concluído / pendente / bloqueios) para uma sprint específica
- [ ] **GERA-02**: Gerente pode gerar Documento Completo do Projeto (visão geral, timeline, decisões, desafios, estado atual)
- [ ] **GERA-03**: Documento gerado é exibido em markdown renderizado na tela
- [ ] **GERA-04**: Gerente pode copiar o markdown gerado para o clipboard

## v2 Requirements

### Geração

- **GERA-v2-01**: Gerente pode gerar Retrospectiva da Sprint (o que funcionou / não funcionou / aprendizados)
- **GERA-v2-02**: Gerente pode gerar Log de Decisões técnicas cronológico de todo o projeto

### Acesso

- **ACES-v2-01**: Autenticação com email/senha
- **ACES-v2-02**: Isolamento de projetos por usuário

## Out of Scope

| Feature | Reason |
|---------|--------|
| Autenticação / login | Adds 1-2 days; toda a subárea usa espaço compartilhado sem isolamento validado |
| Exportação DOCX/PDF | Clipboard é suficiente; export adiciona dependências desnecessárias |
| Editor de texto no documento gerado | Transforma DocuData em Notion — gerentes querem parar de escrever, não escrever mais |
| Notificações (email, Slack) | Integração complexa sem necessidade validada |
| Busca em conteúdo ingerido | Requer infraestrutura de full-text search sem demanda validada |
| Versionamento de documentos gerados | Regenerar sob demanda é suficiente para v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROJ-01 | Phase 1 | Pending |
| PROJ-02 | Phase 1 | Pending |
| PROJ-03 | Phase 1 | Pending |
| INGS-01 | Phase 2 | Pending |
| INGS-02 | Phase 2 | Pending |
| INGS-03 | Phase 2 | Pending |
| EXTR-01 | Phase 2 | Pending |
| EXTR-02 | Phase 2 | Pending |
| EXTR-03 | Phase 2 | Pending |
| EXTR-04 | Phase 2 | Pending |
| GERA-01 | Phase 3 | Pending |
| GERA-02 | Phase 3 | Pending |
| GERA-03 | Phase 3 | Pending |
| GERA-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-22*
*Last updated: 2026-05-22 after initial definition*
