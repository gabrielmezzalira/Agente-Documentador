# B1 · Entrega 3 (revisada) — Dashboard de acompanhamento (BI)

Data: 2026-10-28 · Base: `main` 7bb2677 (entregas 1 e 2 da B1 em produção)
Complementa: `docs/superpowers/specs/2026-10-28-acompanhamento-projetos-design.md`. Esta spec **substitui a seção 5 (tela `/acompanhamento`)** e **redefine a entrega 3** daquela spec.

## Contexto

A tela `/acompanhamento` da entrega 2 é uma lista de cards por gerente. O líder testou e não gostou: está feia e não serve para análise. Ele quer um dashboard no estilo BI que responda, em 10 segundos:
1. **Como está a saúde geral da carteira?**
2. **Quais projetos precisam de mim?**

O eixo de tempo é a **sprint de cada projeto**. Quando o dashboard compara projetos, usa a posição relativa da sprint: atual, −1, −2, até −5.

Layout aprovado no navegador (mockups `layout-combinado.html` e `detalhe-projeto.html` em `.superpowers/brainstorm/`).

## Decisões

| Tema | Decisão |
|---|---|
| Rota | Continua `/acompanhamento`, com o mesmo item de menu e só para líder e owner. A tela atual é substituída. |
| Filtros | Subárea (Dados/Dev) e gerente (Todos ou um gerente). Ficam no topo e valem para todos os blocos. |
| Status do projeto | `critico`, `atencao`, `saudavel` ou `sem_dados` (regras na seção 2). Define a cor e a ordem da fila. |
| SPI da sprint | O mesmo de `routers/metricas.py::get_spi`: realizado sem extras ÷ previsto. Sem previsto, `None`, e o mapa de calor mostra "sem dado". |
| Sprint relativa | Para cada projeto, a sprint atual é a de maior `numero` com `iniciada = true`. As colunas −1…−5 são as sprints iniciadas anteriores, pelo `numero` em ordem decrescente. |
| Features entregues numa sprint | Funcionalidades do projeto com `aprovada_em` dentro da janela da sprint. A janela vai do início da sprint (`data_inicio` 00:00 UTC) até o fechamento (`avaliacao_completa_em`), ou até agora na sprint atual. Sem `data_inicio`, o início é o fechamento da sprint anterior; sem nenhum dos dois, a sprint não conta (`None`). |
| Variação "vs sprint anterior" | Só para features entregues e SPI médio. Compara, em cada projeto, a sprint atual com a −1 e soma ou tira a média na carteira. Tasks travadas mostram só o valor atual. |
| Piso por pessoa | É calculado **ao vivo**, sem foto de fechamento, para entrar já no bloco "Time". Usa a regra da spec original: 0,5 × máx(mediana do squad na sprint −1, mediana da subárea no trimestre civil anterior), com o realizado sem extras. O trimestre de cada sprint é o da data de fechamento; sem fechamento, o da `data_fim`. A foto do fechamento fica para depois, só se o número precisar ser congelado. |
| Diagnóstico | Texto montado por regras, sem IA, a partir dos mesmos sinais do status (seção 2). |
| Dado faltando | Nunca vira zero que parece resultado. Mostra "sem dado" (cinza) e entra na fila como `sem_dados`, com o que falta preencher. |

## 1. Dashboard (`/acompanhamento`)

Os blocos ficam nesta ordem, de cima para baixo:

1. **Carteira:** 5 KPIs, considerando a última sprint de cada projeto filtrado.
   - `Projetos`: total, com o subtexto "N críticos · M atenção".
   - `Features entregues`: soma da sprint atual, com a variação ▲/▼ contra a −1.
   - `SPI médio`: média dos SPIs da sprint atual dos projetos com SPI, com a variação.
   - `Metas batidas`: "A de B" na última sprint fechada dos projetos com meta, com o subtexto "N projetos sem meta".
   - `Tasks travadas`: total atual.
2. **Precisa de você:** uma lista ordenada por gravidade (`critico` > `atencao` > `sem_dados`; dentro de cada grupo, pela quantidade de sinais). Projetos `saudavel` não aparecem.
   - Cada linha mostra a bolinha de status, o nome do projeto, o gerente (texto cinza) e um chip com os 1 ou 2 motivos principais.
   - Clicar abre o detalhe.
   - Vazia, mostra "Nenhum projeto precisa de atenção agora."
3. **Evolução por sprint:** mapa de calor com uma linha por projeto e 6 colunas (−5…atual).
   - A cor da célula é o SPI daquela sprint: ≥ 0,9 verde, 0,7–0,9 âmbar, < 0,7 vermelho, sem dado cinza.
   - Uma legenda acompanha o mapa.
   - O `title` e o `aria-label` da célula dizem `Sprint N · SPI X · meta A/B`.
   - Clicar no nome do projeto abre o detalhe.
4. **Risco de prazo:** gráfico de dispersão. Ao lado dele fica o quadro **Por gerente**.
   - **Dispersão:**
     - X = % do prazo do contrato consumido; Y = % das funcionalidades aprovadas (`calcular_bloco_a`);
     - o raio da bolha é proporcional às tasks travadas (mínimo de 4 px);
     - a diagonal de referência marca y = x;
     - projetos sem datas do contrato ficam fora do gráfico, com a nota "N projetos sem datas do contrato".
   - **Por gerente:** uma linha por gerente com nº de projetos, críticos, atenção e "metas batidas A/B". Clicar filtra o dashboard por aquele gerente.

O gráfico é desenhado em SVG à mão, sem lib nova, seguindo os gráficos de `MetricasTab.tsx`. Os tokens vêm de `app/lib/ds.ts`. Precisa de estados de carregando, vazio e erro, e de um layout que funcione em telas estreitas (blocos empilhados).

## 2. Status do projeto e motivos (backend, funções puras)

Sinais, cada um com o texto do motivo:
- `spi_critico`: SPI da sprint atual < 0,7 → "SPI X";
- `spi_caindo`: SPI < 0,9 nas 3 últimas sprints com SPI → "SPI abaixo de 0,9 há 3 sprints";
- `prazo`: regra (a) da spec original → "N% do prazo · M% entregue";
- `meta_ruim`: regra (b) da spec original → "meta da última sprint A/B";
- `travadas`: tasks travadas > 0 → "N travadas";
- `sem_meta`: sprint atual sem meta → "sem meta";
- `sem_planejamento`: nenhuma funcionalidade em `sprint_funcionalidades` da sprint atual → "sem planejamento";
- `sem_datas`: sem datas do contrato → "sem datas do contrato";
- `sem_gerente`: sem gerente → "sem gerente";
- `sem_sprint`: nenhuma sprint iniciada → "nenhuma sprint iniciada".

Status:
- **`critico`** se houver `spi_critico`, `prazo` ou `meta_ruim`, ou se houver `travadas` ≥ 5;
- senão **`atencao`** se houver `spi_caindo`, `travadas` (1 a 4) ou `sem_meta`;
- senão **`sem_dados`** se houver `sem_sprint`, `sem_planejamento`, `sem_datas` ou `sem_gerente`;
- senão **`saudavel`**.

O chip mostra os 2 primeiros motivos, nesta ordem de prioridade: `spi_critico`, `prazo`, `meta_ruim`, `travadas`, `spi_caindo`, `sem_meta`, `sem_sprint`, `sem_planejamento`, `sem_datas`, `sem_gerente`.

**Diagnóstico (para o detalhe):** começa com "Crítico." / "Atenção." / "Saudável." / "Faltam dados.". Depois vêm as frases de todos os sinais e, separada, a linha "Falta preencher: …" com os sinais `sem_*`.

## 3. Detalhe do projeto (painel lateral)

Abre por cima do dashboard, com largura de cerca de 720 px. Usa o `Modal` do design system, com Esc e foco no ×. Contém, de cima para baixo:
1. **Diagnóstico:** o texto da seção 2, com a borda na cor do status.
2. **4 números:** SPI da sprint atual, prazo × escopo, travadas e p85 do tempo limpo em 30 dias (como na entrega 2).
3. **Sprint atual e meta:** a lista das funcionalidades da meta com status, % de tasks e os selos ("aprovada", "fora do planejamento").
   - Abaixo: "Planejadas fora da meta" e o link "Histórico de mudanças da meta".
   - O botão **Definir meta** reaproveita o `DefinirMetaModal` da entrega 2.
4. **Sprint a sprint** (até 6 sprints): barras de pontos previstos × realizados. A barra de realizados leva a cor do SPI, e um ● marca as sprints com meta batida.
5. **Time · sprint atual:** uma linha por pessoa do squad com o realizado, o piso e o chip "acima" ou "abaixo do piso (X)". Sem piso, mostra "sem histórico para o piso".

## 4. Backend

- `GET /acompanhamento?subarea=&gerente_email=` (`require_role("lider")`) passa a devolver:
  - `kpis`;
  - `fila`;
  - `mapa`: por projeto, as sprints −5…atual com `numero`, `spi`, `meta_total`, `meta_entregues` e `meta_batida`;
  - `dispersao`;
  - `por_gerente`;
  - `projetos` (os dados da entrega 2, mais `status`, `sinais`, `motivos` e `diagnostico`).

  A entrega 2 ainda não tem usuários além do líder, então dá para trocar o formato da resposta sem versionar.
- `GET /acompanhamento/projetos/{id}` (`require_role("lider")`) devolve o detalhe: os dados da seção 3, com o sprint a sprint (6) e o time com o piso.
- **Piso ao vivo:** `services/piso.py`.
  - Funções puras com teste: `realizados_por_pessoa`, `mediana`, `piso` e `trimestre_de`.
  - Leitura em lote das tasks concluídas da subárea no trimestre anterior. Só é lida quando o detalhe é pedido, nunca na lista.
- **Performance:** tudo em lote, como na entrega 2 (≤100 ids por `.in_`, `ler_tudo`, nada por sprint ou por task). O mapa de calor reaproveita as tasks já carregadas para o SPI de cada sprint.

## 5. Testes

- **Backend:**
  - tabela de casos de `status` e `motivos` (cada sinal, as prioridades e a combinação);
  - textos do diagnóstico;
  - colunas da sprint relativa: projeto com menos de 6 sprints e projeto sem sprint iniciada;
  - janela de "features entregues";
  - variação vs −1;
  - piso: mediana par e ímpar, uma, duas ou nenhuma mediana, virada de trimestre;
  - forma do JSON das duas rotas;
  - 403 para gerente e operacional.
- **Frontend:** `tsc`, `npm test` e testes estruturais com os títulos dos blocos, a legenda do mapa, a nota "sem datas do contrato", o "Definir meta" no detalhe, o "abaixo do piso" e o menu só para líder e owner.

## Fora de escopo

- Visão por mês ou trimestre (o eixo é a sprint).
- Foto do fechamento e histórico congelado. O piso e o histórico são calculados ao vivo.
- O gerente acessar o dashboard.
- Exportar para PDF ou planilha.
