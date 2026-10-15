# Peso do Gerente, Remoção da Evolução e Ranking por Projeto — Design

Data: 2026-09-23 · Gabriel Mezzalira · DocuData

## 1. Problema

O gerente revisou notas antigas sobre o sistema de avaliação de performance e deu feedback direto sobre três pontos (mensagem do usuário, 2026-09-23):

> "der 50% de peso para o gerente"

> "outro ponto, eu quero tirar tudo relacionado a evolucao, nao vejo sentido nisso. tenho que ajustar as documentacoes do sistema de avaliacao."

> "eu quero que o ranking seja dividio por projeto, nao geral"

Um quarto ponto do mesmo print ("colocar as avaliações lado a lado pra comparar") fica fora deste plano — ver §7.

O gerente também disse "essas modificações eu quero que já altere a avaliação que eu fiz, pois eu acho que ficou injusta". Investigação nesta sessão (ver §3) mostrou que isso já acontece automaticamente assim que a migração de pesos for aplicada — não existe pontuação final travada em nenhuma tabela, ela é sempre calculada na hora.

## 2. Decisões

### 2.1 Peso do gerente = 50%, em todos os arquétipos

Tabela `pesos_arquetipo`, hoje:

| Dimensão | padrao | consultoria_discovery |
|---|---|---|
| peso_gerente | 0.35 | 0.50 |
| peso_entrega | 0.20 | 0.20 |
| peso_qualidade | 0.20 | 0.10 |
| peso_autonomia | 0.15 | 0.12 |
| peso_evolucao | 0.10 | 0.08 |

Novo (peso_gerente sobe pra 0.50 nos dois arquétipos — no 'consultoria_discovery' já estava lá; peso_evolucao zera; o que sobra de Entrega/Qualidade/Autonomia é redistribuído mantendo a proporção relativa atual entre as três, escalada pra caber no que sobrou de 1.00 menos peso_gerente, arredondado a 2 casas decimais porque a coluna no banco é `numeric(3,2)`):

| Dimensão | padrao | consultoria_discovery |
|---|---|---|
| peso_gerente | **0.50** | **0.50** |
| peso_entrega | **0.18** | **0.24** |
| peso_qualidade | **0.18** | **0.12** |
| peso_autonomia | **0.14** | **0.14** |
| peso_evolucao | **0.00** (dimensão removida, ver §2.2) | **0.00** |

Cada coluna soma 1.00 exatamente.

### 2.2 Remoção completa da dimensão "Evolução"

Confirmado com o usuário (pergunta de esclarecimento nesta sessão): é remoção **completa**, não só zerar o peso. Tudo isto sai:

- A pergunta 6 do questionário semanal do gerente ("Evoluiu em relação a onde estava no começo do ciclo?") — o questionário passa de 7 para **6 perguntas**.
- O peso da dimensão Evolução no score final (já coberto em §2.1).
- A tela/endpoint de SPI-evolução (`GET /projects/{id}/spi-evolucao`, coluna "Evolução" na aba Métricas).
- O endpoint de baseline-evolução (`POST /baseline-evolucao`) por completo.
- Toda a documentação viva do sistema de avaliação (`docs/metodologia-performance.md`, `docs/acompanhamento-publico.md`, `docs/guia-do-sistema.md`).

O campo `resposta_6` (banco: `avaliacoes_gerente.resposta_6`) e `gerente_pergunta6` (banco: `pontuacao_operacional_sprint.gerente_pergunta6`) **não são removidos** do banco — só deixam de ser exigidos/computados. Motivo: preservar a leitura de dado histórico (avaliações antigas já têm resposta_6 real) sem migração destrutiva, seguindo a convenção já estabelecida no projeto (nenhuma migração até hoje faz `DROP COLUMN`/`DROP TABLE`). `resposta_6` vira opcional no create/update; nenhuma tela nova volta a pedir essa pergunta.

Especificamente NÃO removido: a coluna `gerente_pergunta6` em `pontuacao_operacional_sprint`, a coluna `resposta_6` em `avaliacoes_gerente`, a tabela `baseline_evolucao` (fica órfã, sem nenhum endpoint que escreva nela daqui pra frente).

### 2.3 Ranking dividido por projeto, não mais cross-projeto

Hoje `GET /performance` (tela `/performance`, Líder-only) junta a performance de uma pessoa em **todos os projetos** em que ela atua numa única entrada, com cada dimensão sendo a média simples entre os projetos (`services/performance.py::listar_pessoas_ativas` agrupa só por e-mail, ignorando o projeto).

Novo: o ranking passa a ser **por projeto**. Uma pessoa que atua em dois projetos aparece duas vezes — uma entrada por projeto, cada uma calculada só com os dados daquele projeto, sem nenhuma média cross-projeto.

**Achado arquitetural que simplifica a implementação:** as funções que calculam cada dimensão (`calcular_ranking_pessoa`, `_calcular_janela`, `_entrega_por_projeto`, `_gerente_por_projeto`, `_autonomia_por_projeto`, `_qualidade_por_projeto`, `_media_cross_projeto`) já operam "por projeto primeiro, depois agrega" — eram genéricas o bastante pra já funcionar corretamente com uma pessoa presente em um projeto só. A única coisa que faz a agregação ser cross-projeto hoje é a função de agrupamento de entrada, `listar_pessoas_ativas`, que junta `operacional_ids` de todos os projetos de uma pessoa antes de mandar pro cálculo. Substituindo essa função por uma que agrupa por (projeto, e-mail) em vez de só e-mail, o resto do motor de cálculo funciona sem nenhuma mudança.

## 3. Achado arquitetural — por que não precisa reabrir nenhuma sprint

`pontuacao_operacional_sprint` (a tabela travada no fechamento de cada sprint) **não tem coluna `score_final`** — ela só guarda os números crus por dimensão (`gerente_media`, `entrega_pontos_*`, `qualidade_*`, `autonomia_*`). O `score_final` ponderado é calculado **na hora**, a cada `GET /performance`, lendo `pesos_arquetipo` fresco (`services/performance.py::_score_final`).

Consequência: assim que a migração SQL de pesos (§2.1) for aplicada em produção, **todo ranking — inclusive de sprints já fechadas — reflete os pesos novos automaticamente no próximo carregamento da tela**. Não existe, e não precisa existir, nenhum mecanismo de "recálculo": reabrir (`DELETE /avaliacoes/{sprint_id}/confirmar`) e refechar uma sprint não muda o score_final que ela já não guardava. Isso resolve diretamente a reclamação do usuário sobre a avaliação que ele já fez ter ficado injusta — a correção é automática, sem ação manual.

Um teste de integração no plano de implementação prova essa afirmação (congela uma linha de `pontuacao_operacional_sprint`, muda `pesos_arquetipo`, chama o cálculo de ranking de novo, confirma que o score mudou).

Existe uma coisa **diferente** de "recalcular com pesos novos" que continua fora deste plano: o gerente reabrir uma sprint específica porque quer **re-responder** o questionário (mudar uma nota que ele deu). Isso já é possível pelo fluxo existente (reabrir + editar avaliação dentro de 48h + refechar) e não faz parte desta entrega — se o usuário quiser fazer isso para uma sprint específica, ele nomeia qual depois.

## 4. Modelo de dados

### 4.1 `pesos_arquetipo` (migração manual, UPDATE)

Ver valores exatos em §2.1. Migração faz `UPDATE pesos_arquetipo SET ... WHERE arquetipo = '...'` para as duas linhas.

### 4.2 `avaliacoes_gerente.resposta_6` — vira opcional

```sql
ALTER TABLE avaliacoes_gerente ALTER COLUMN resposta_6 DROP NOT NULL;
```

O `CHECK (resposta_6 BETWEEN 0 AND 5)` já existente permite `NULL` por padrão no Postgres — não precisa recriar a constraint.

### 4.3 `PerformanceResponse` — passa a ser aninhada por projeto

Hoje:
```python
class PerformanceResponse(BaseModel):
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []
```

Novo:
```python
class PerformanceProjetoResponse(BaseModel):
    projeto_id: str
    projeto_nome: str
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []

class PerformanceResponse(BaseModel):
    projetos: list[PerformanceProjetoResponse] = []
```

`PerformanceOperacionalResponse` perde o campo `evolucao`.

### 4.4 `SpiEvolucaoOperacionalResponse` → `SpiPorOperacionalDoProjetoResponse`

Perde o campo `evolucao`. Endpoint muda de `GET /projects/{id}/spi-evolucao` para `GET /projects/{id}/spi`.

### 4.5 Removidos por completo

`BaselineEvolucaoCreate`, `BaselineEvolucaoResponse` (schemas), `POST /baseline-evolucao` (endpoint), `criar_baseline_evolucao` (função).

## 5. API — endpoints afetados

| Endpoint | Mudança |
|---|---|
| `GET /performance` | Resposta muda de plana pra aninhada por projeto (§4.3) |
| `GET /projects/{id}/spi-evolucao` | Renomeado pra `GET /projects/{id}/spi`; resposta perde `evolucao` |
| `POST /baseline-evolucao` | Removido |
| `POST /avaliacoes` | `resposta_6` vira opcional no body |

## 6. Frontend

- `AvaliacaoSemanalModal.tsx`: questionário de 6 perguntas (a pergunta de evolução sai da lista); payload não manda mais `resposta_6`.
- `MetricasTab.tsx`: tabela "Entrega e evolução por pessoa" perde a coluna Evolução e é renomeada pra "Entrega por pessoa".
- `performance/page.tsx`: reescrito pra renderizar uma seção por projeto (nome do projeto como cabeçalho), cada uma com as mesmas 3 janelas de hoje; dimensão "Evolução" sai da lista de dimensões exibidas por pessoa.
- `api.ts`: tipos e funções ajustados pros pontos acima (`getSpiDoProjeto` no lugar de `getSpiEvolucaoProjeto`, `PerformanceResponse` aninhado, `resposta_6` opcional).

## 7. Fora de escopo (deferido)

- **Comparação lado a lado das notas do gerente por operacional/squad** ("colocar as avaliações lado a lado pra comparar, pra ter parâmetro de nota"). Feature própria, plano futuro — não implementar, não deixar stub, não referenciar como TODO no código desta entrega.
- **Automação de reabrir/refechar uma sprint específica.** Não é necessária pra este plano (§3) e não deve ser criada.
- **Editar uma avaliação já enviada por uma UI dedicada** ("deixar uma forma pra editar a avaliação e salvar, e dps fechar") — o backend já aceita upsert dentro de 48h; não existe hoje uma tela que reabra uma avaliação já respondida pra edição, e este plano não cria uma.
- **O bug do alerta de atraso não isentar entrega quando só havia uma task e o cliente não respondeu** (nota separada do usuário sobre a métrica de Entrega não poder ser excluída da conta, só zerada/não descontada) — problema real, mas de uma dimensão diferente (Entrega, não Gerente/Evolução/Ranking), não faz parte desta entrega.

## 8. Testes (cobertura mínima, detalhada no plano de implementação)

- Migração de pesos: soma de cada arquétipo é exatamente 1.00.
- `_score_final` sem a chave "evolucao" no mapa de pesos: dimensões disponíveis continuam normalizando corretamente quando falta uma dimensão.
- Prova de que o score muda ao vivo quando `pesos_arquetipo` muda, sem reabrir nenhuma sprint (§3).
- `resposta_6` ausente no `POST /avaliacoes` continua criando/atualizando a avaliação normalmente (422 não deve mais acontecer por falta desse campo).
- Ranking por projeto: pessoa ativa em um projeto só aparece só naquele projeto; pessoa ativa em dois projetos aparece duas vezes, com notas potencialmente diferentes (prova de que não há mais média cross-projeto).
- Grep final: nenhuma ocorrência de "evolucao"/"evolução" ligada a essa dimensão de nota sobra em código ou documentação viva.
