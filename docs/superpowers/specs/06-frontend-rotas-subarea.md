# Spec 06 — Frontend: rotas separadas por subárea

**Prioridade:** alta · **Depende de:** 01, 03, 05 · **Bloqueia:** nada

## Problema

O frontend hoje tem uma única árvore de rotas (`/`, `/projects/new`, `/projects/[id]`)
sem noção de subárea. Precisamos que Dev enxergue só projetos de Dev, Dados só de
Dados, sem autenticação — ou seja, a separação é de **navegação**, não de permissão.

## Escopo

### 1. Nova estrutura de rotas

Mover as páginas existentes para dentro de um segmento dinâmico `[subarea]`:

```
app/
  page.tsx                        <- NOVO: seletor "Dados" ou "Dev"
  [subarea]/
    layout.tsx                    <- NOVO: valida subarea, mostra qual está ativa
    page.tsx                      <- era app/page.tsx (lista de projetos)
    projects/
      new/page.tsx                <- era app/projects/new/page.tsx
      [id]/page.tsx                <- era app/projects/[id]/page.tsx
```

- `app/page.tsx` (raiz) vira uma tela simples com dois links/cartões: "Dados" →
  `/dados`, "Dev" → `/dev`. Sem lógica além de navegação.
- `app/[subarea]/layout.tsx` valida que `subarea` é `"dados"` ou `"dev"` (se não for,
  `notFound()`), e renderiza um cabeçalho fixo mostrando a subárea ativa com um link
  pra trocar (volta pra `/`).
- Todo componente movido para dentro de `[subarea]/...` passa a ler `subarea` via
  `useParams()` (client component) e usa esse valor em toda chamada à API.

### 2. `app/lib/api.ts`

Toda função que hoje bate em `/projects` ou `/search` ganha `subarea` como parâmetro
obrigatório e propaga como query string, refletindo a spec 05:
```ts
export async function listProjects(subarea: "dados" | "dev"): Promise<Project[]> { ... }
export async function searchStack(q: string, subarea: "dados" | "dev"): Promise<StackSearchResponse> { ... }
export async function createProject(payload: {..., subarea: "dados" | "dev"}): Promise<Project> { ... }
```
Endpoints que já recebem `project_id` (a maioria) não mudam de assinatura.

### 3. Links internos

Todo `<Link href="/projects/...">` e `router.push(...)` dentro das páginas movidas
precisa virar `` `/${subarea}/projects/...` ``, usando o `subarea` do `useParams()`.
Confira especialmente `ProjectCard` (link pro dashboard do projeto) e o botão "Novo
projeto" da listagem.

### 4. Criação de projeto

`app/[subarea]/projects/new/page.tsx`: o formulário passa a mandar `subarea: params.subarea`
junto no `createProject(...)` — o usuário não escolhe a subárea no formulário, ela
já vem da rota em que ele está.

### 5. Não fazer nesta spec

- Não duplicar componentes (`SprintCard`, `DocTypeCard`, etc.) — eles continuam
  compartilhados, só passam a viver logicamente "dentro" da árvore `[subarea]` por
  causa de onde são importados, não precisam ser copiados.
- Não adicionar nenhuma diferença visual/de comportamento entre Dados e Dev além do
  filtro de dados e do rótulo no cabeçalho — os dois usam exatamente os mesmos tipos
  de documento, mesmos formulários, mesmo fluxo.

## Critérios de aceite

- [ ] `http://localhost:3000/` mostra o seletor Dados/Dev, sem lista de projetos.
- [ ] `http://localhost:3000/dev` mostra só projetos com `subarea=dev`.
- [ ] `http://localhost:3000/dados` mostra só projetos com `subarea=dados`.
- [ ] `http://localhost:3000/qualquercoisa` (subárea inválida) dá 404.
- [ ] Criar projeto a partir de `/dev/projects/new` cria com `subarea: "dev"` sem que
      o usuário precise selecionar nada relacionado a isso no formulário.
- [ ] Navegar para o dashboard de um projeto a partir da listagem de Dev leva pra
      `/dev/projects/{id}`, e o mesmo projeto não aparece navegável a partir de
      `/dados`.
- [ ] `npm run build` sem erro de tipo.
- [ ] Teste manual completo de um fluxo: criar projeto em `/dev` → submeter um
      Planning → gerar o doc → confirmar que ele não aparece em nenhuma lista de
      `/dados`.

## Como testar manualmente

1. `npm run dev`, abrir `http://localhost:3000`.
2. Clicar em "Dev", criar um projeto novo, confirmar URL final `/dev/projects/<uuid>`.
3. Voltar pra `/`, clicar em "Dados", confirmar que o projeto criado em Dev não
   aparece na lista.
4. Repetir criando um projeto em "Dados" e confirmar o inverso.
