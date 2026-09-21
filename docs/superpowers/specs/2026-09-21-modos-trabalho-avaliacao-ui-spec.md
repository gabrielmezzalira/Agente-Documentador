# UI-SPEC — Modos de Trabalho e de Avaliação (Entrega 1, Onda 2)

> Gerado via feature-flow-lean Etapa 7, tier PADRÃO. Não regenera design system:
> o frontend não tem `design-system/MASTER.md` nem `DESIGN.md` formal, mas tem
> convenção de facto (inline `style={{}}`, tokens repetidos) já mapeada na Etapa 0
> e reaproveitada aqui sem geração nova (`gates_reusados`).

## Fonte de verdade

O contrato de UI já está integralmente especificado, com código exato, em
`docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1.md`,
Tasks 9-12 (Onda 2). Este documento não repete esse código — registra as
decisões de design que o plano assume, para auditoria da Etapa 11.

## Paleta e tokens reaproveitados (sem mudança)

- Verde primário `#22c55e` / escuro `#166534` — ações positivas, chip "OK".
- Cinzas `#f4f4f7` `#f7f7fa` (fundos) `#9696a0` `#b8b8c0` (texto secundário/borda).
- Alerta `#dc2626` — erro, pendência crítica.
- Aviso `#fffbeb` fundo / `#fbbf24` borda — pendência não bloqueante.
- Botões: `btnPrimary`, `btnGhost` (tokens já existentes em `page.tsx`/`SprintCard.tsx`).
- Chip: mesmo padrão visual do chip de status de sprint já usado em `SprintCard.tsx`.

## Componentes novos (Tasks 9-12)

| Componente | Onde | Padrão reaproveitado |
|---|---|---|
| Chip "N/M" avaliação semanal | `SprintCard.tsx` (Task 10) | Mesmo componente de chip de status já usado no card — cor verde se completo, âmbar se pendente, reusa a paleta de aviso |
| Seção "Modos de Trabalho e de Avaliação" | `page.tsx`, aba Configurações (Task 11) | Segue o padrão de outras seções de config já existentes na mesma aba: título + descrição curta + controles + histórico de mudança abaixo, mesmos `btnPrimary`/`btnGhost` |
| WIP config (RF-A5, read-only por enquanto) | mesma seção da Task 11 | Campo somente leitura com o mesmo estilo de "chip informativo" — não introduz padrão novo |
| Seção "Extrato de pontos" | `PainelTab.tsx` (Task 12) | Tabela simples, mesmo padrão de outras listagens do Painel (linha por evento, coluna de sinal +/-, mesma paleta verde/vermelho para ganho/desconto) |

## Estados de UI obrigatórios

- Loading: reaproveita o padrão existente de spinner/skeleton já usado nas outras
  seções de `page.tsx` e `PainelTab.tsx` (não inventar um novo).
- Erro: mensagem inline com `#dc2626`, mesmo padrão de erro de fetch já usado no arquivo.
- Vazio: "Extrato de pontos" vazio (sprint sem eventos) mostra texto neutro
  ("Nenhum evento de pontuação registrado nesta sprint"), sem ilustração nova.

## Dependências

Nenhuma lib nova — `package.json` já cobre tudo (`react-markdown`, `recharts`,
sem necessidade de tabela/CSV para o escopo de Tasks 9-12; export CSV não está
no escopo desta Entrega 1 conforme plano).

## Acessibilidade mínima (WCAG AA)

- Chip N/M: não depender só de cor — incluir o texto "N/M avaliados" (já no plano).
- Campos de config (modo de trabalho/avaliação): `<label>` associado a cada select/input.
- Tabela de extrato: `<th scope="col">` nos cabeçalhos, contraste texto/fundo AA
  (paleta já validada em uso no resto do app).
- Foco visível nos novos controles interativos — reaproveita o outline padrão do navegador
  já em uso no restante do app (nenhum componente remove `outline`).

## Motion (input para Etapa 9)

Nenhuma animação nova necessária — chip, seção de config e tabela de extrato
são elementos estáticos. Única transição pertinente: abrir/fechar a seção de
histórico de mudança de modo (Task 11) pode reaproveitar a mesma transição de
altura/opacidade já usada em outras seções colapsáveis do app, se existir; caso
contrário, renderização condicional simples sem animação (não introduzir motion novo
para um toggle de baixa frequência de uso).
