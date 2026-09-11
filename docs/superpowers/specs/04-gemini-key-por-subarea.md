# Spec 04 — Chave Gemini global configurável pela aplicação

**Prioridade:** alta · **Depende de:** 03 · **Bloqueia:** 07

## Objetivo

Hoje a chave do Gemini está associada ao projeto e armazenada em `projects.gemini_api_key`. Isso cria dois problemas principais:

1. a aplicação trata uma credencial de infraestrutura como se fosse configuração de cada projeto;
2. o segredo fica persistido em texto plano no registro do projeto e pode acabar sendo lido, alterado ou apagado por fluxos que não deveriam ter acesso a ele.

Com a existência de `subarea` e com as credenciais do agente já separadas da configuração dos projetos, a chave do Gemini passa a ser uma **configuração global da aplicação**.

A partir desta spec:

- existe **uma única chave Gemini ativa para toda a aplicação**;
- `dados`, `dev` e qualquer futura subárea usam a mesma chave;
- nenhum projeto guarda, recebe ou informa chave Gemini;
- a chave pode ser cadastrada ou substituída em uma tela global de configurações no frontend;
- o frontend **nunca recebe a chave atual de volta**;
- o backend é o único responsável por ler, criptografar, descriptografar e utilizar a chave;
- o valor persistido no banco **não pode ficar em texto plano**;
- `projects.gemini_api_key` permanece fisicamente no banco por enquanto, mas deixa de ser utilizada por todo o código.

---

# Decisões de arquitetura

## Fonte de verdade

A chave configurada pela aplicação deve ficar em um armazenamento global de configurações do backend, e não em `projects` nem em variável de ambiente específica de subárea.

A fonte de verdade será uma configuração global persistida no banco.

A chave **não deve ser salva em texto plano**. O backend deve criptografar o segredo antes do `INSERT`/`UPDATE` e descriptografá-lo somente no momento em que precisar inicializar o cliente Gemini.

A chave usada para criptografar os segredos da aplicação deve continuar sendo uma variável de ambiente do backend, por exemplo:

```env
DOCUDATA_SECRETS_KEY=<fernet-key>
```

Essa chave é infraestrutura do servidor e **não pode ser configurável pelo frontend**.

> Não reutilizar `DOCUDATA_APP_SECRET`, chave do agente ou qualquer outra credencial de autenticação como chave de criptografia. São responsabilidades diferentes e o comprometimento de uma credencial não deve comprometer automaticamente as demais.

Se a base já tiver, após a Spec 03, uma estrutura global apropriada para armazenar configurações/segredos da aplicação, ela deve ser reutilizada em vez de criar uma segunda implementação paralela. Caso não exista, implementar a tabela descrita nesta spec.

## Por que não usar `GEMINI_API_KEY` diretamente no `.env`

A variável de ambiente não deve ser a fonte de verdade da chave Gemini nesta spec porque a chave precisa poder ser alterada pelo frontend e continuar válida após restart, redeploy ou múltiplos workers do backend.

Editar `.env` ou `os.environ` em runtime não é persistência confiável e deve ser evitado.

## Sem chave por subárea

`subarea` continua existindo normalmente no domínio dos projetos, mas **não participa da resolução da chave Gemini**.

Não criar:

```text
GEMINI_API_KEY_DADOS
GEMINI_API_KEY_DEV
```

Nem fazer mapeamentos como:

```python
{"dados": "...", "dev": "..."}
```

Todos os fluxos Gemini devem chamar o mesmo helper global.

---

# Escopo

## 1. Persistência segura da configuração global

### 1.1. Criar tabela global de configurações, caso ainda não exista equivalente

Criar migration para uma tabela como:

```sql
create table if not exists app_settings (
    key text primary key,
    encrypted_value text not null,
    display_hint text null,
    updated_at timestamptz not null default now()
);
```

Para a Gemini API Key, usar:

```text
key = "gemini_api_key"
```

Exemplo conceitual do registro:

```text
key:             gemini_api_key
encrypted_value: gAAAAAB...
display_hint:    ••••••••A1b2
updated_at:      2026-08-24T...
```

### 1.2. Segurança da tabela

Se estiver usando Supabase/Postgres com RLS:

- habilitar RLS em `app_settings`;
- não criar policy que permita leitura/escrita direta pelo browser;
- acesso ao segredo deve acontecer exclusivamente através do backend;
- usar a credencial server-side já adotada pelo backend para acessar a tabela.

O frontend nunca deve acessar `app_settings` diretamente.

### 1.3. Não armazenar a chave em `display_hint`

`display_hint` deve conter somente uma representação segura, por exemplo os últimos 4 caracteres:

```text
••••••••A1b2
```

Nunca salvar prefixo + sufixo suficiente para reconstrução ou identificação indevida da chave.

---

## 2. Serviço central de segredo Gemini

Criar:

```text
docudata-backend/services/gemini_key.py
```

Esse arquivo passa a ser a **única fonte de acesso à chave Gemini** no backend.

Nenhum router ou serviço deve acessar diretamente `app_settings` para obter a chave.

### 2.1. Responsabilidades

O serviço deve concentrar:

- obtenção da chave de criptografia do backend;
- criptografia do segredo;
- descriptografia do segredo;
- leitura da chave Gemini global;
- atualização/substituição da chave Gemini global;
- leitura do status da configuração sem revelar a chave;
- erros de domínio relacionados a ausência ou configuração inválida da chave.

### 2.2. Dependência de criptografia

Preferencialmente usar `cryptography.fernet.Fernet` por ser simples, autenticado e suficiente para esse caso.

Caso `cryptography` ainda não esteja nas dependências do backend, adicioná-la ao arquivo de dependências utilizado pelo projeto.

A env var deve conter uma chave Fernet válida.

Exemplo para gerar localmente:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Depois:

```bash
export DOCUDATA_SECRETS_KEY="<valor-gerado>"
```

### 2.3. API interna esperada

A implementação pode adaptar detalhes ao padrão já existente no projeto, mas deve oferecer semanticamente algo equivalente a:

```python
class GeminiApiKeyNotConfigured(Exception):
    pass


class GeminiApiKeyStorageError(Exception):
    pass


def get_gemini_api_key() -> str:
    """Retorna a chave Gemini global descriptografada.

    Levanta GeminiApiKeyNotConfigured se nenhuma chave estiver cadastrada.
    Nunca retorna string vazia.
    """
    ...


def set_gemini_api_key(api_key: str) -> None:
    """Valida, criptografa e substitui a chave Gemini global."""
    ...


def get_gemini_api_key_status() -> dict:
    """Retorna somente metadados seguros sobre a configuração."""
    ...
```

### 2.4. Regras de `get_gemini_api_key()`

1. buscar `app_settings.key = "gemini_api_key"`;
2. se não existir, levantar `GeminiApiKeyNotConfigured`;
3. obter `DOCUDATA_SECRETS_KEY`;
4. descriptografar `encrypted_value`;
5. garantir que o resultado não seja vazio;
6. retornar a chave somente em memória para o chamador.

Não fazer log da chave.

Não incluir a chave em mensagens de exceção.

Não retornar a chave em responses HTTP.

### 2.5. Regras de `set_gemini_api_key()`

- aplicar `.strip()`;
- rejeitar valor vazio;
- não aceitar `null`;
- criptografar antes de persistir;
- fazer `upsert` do registro global;
- atualizar `display_hint`;
- atualizar `updated_at`;
- nunca retornar o segredo salvo.

Não é necessário validar a chave fazendo uma chamada real ao Gemini durante o `PUT`. A troca da configuração não deve depender de rede externa, consumir quota ou falhar por indisponibilidade temporária do Gemini.

Validação funcional da credencial acontece naturalmente no primeiro fluxo que efetivamente usa o Gemini.

### 2.6. Cache

**Não adicionar cache nesta primeira implementação.**

A leitura de uma única linha de configuração antes de uma operação Gemini é pequena comparada ao custo da própria chamada ao modelo e evita problemas de invalidação entre múltiplos workers/processos quando a chave for trocada pelo frontend.

Se futuramente houver necessidade comprovada de cache, implementar cache compartilhado ou TTL explícito em spec separada.

---

## 3. Tratamento HTTP centralizado

A ausência da chave global é uma condição operacional conhecida e deve resultar em erro amigável, nunca em stacktrace para o cliente.

Adicionar tratamento equivalente a:

```text
422 Unprocessable Entity
```

Com mensagem clara, por exemplo:

```json
{
  "detail": "A chave Gemini da aplicação ainda não está configurada. Configure-a em Configurações antes de usar recursos de IA."
}
```

Preferir um exception handler central para `GeminiApiKeyNotConfigured`, em vez de repetir o mesmo `try/except` em todos os routers.

Exemplo conceitual:

```python
@app.exception_handler(GeminiApiKeyNotConfigured)
async def gemini_key_not_configured_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "A chave Gemini da aplicação ainda não está configurada. Configure-a em Configurações antes de usar recursos de IA."
        },
    )
```

Erros internos de criptografia ou corrupção de configuração não devem revelar detalhes da chave nem stacktrace ao cliente.

---

## 4. Endpoints globais de configuração

Criar um router global, preferencialmente:

```text
docudata-backend/routers/settings.py
```

Registrar o router no app principal seguindo o mesmo padrão dos routers atuais.

Os endpoints devem usar a mesma proteção/autenticação server-side já adotada pela aplicação para rotas administrativas. **Não criar endpoint público para alteração da chave.**

Se já existir uma dependency comum para validar `X-Docudata-Key` ou a credencial equivalente introduzida nas specs anteriores, reutilizá-la.

### 4.1. Consultar status

```http
GET /settings/gemini
```

Response quando configurada:

```json
{
  "configured": true,
  "key_hint": "••••••••A1b2",
  "updated_at": "2026-08-24T12:00:00Z"
}
```

Response quando ainda não configurada:

```json
{
  "configured": false,
  "key_hint": null,
  "updated_at": null
}
```

Esse endpoint **nunca** retorna a chave real nem o valor criptografado.

### 4.2. Cadastrar ou substituir chave

Usar semântica de substituição da configuração global:

```http
PUT /settings/gemini/api-key
```

Payload:

```json
{
  "api_key": "<nova-chave>"
}
```

Response sugerida:

```json
{
  "configured": true,
  "key_hint": "••••••••A1b2",
  "updated_at": "2026-08-24T12:00:00Z"
}
```

Regras:

- `api_key` obrigatória;
- rejeitar string vazia ou somente espaços com `422`;
- substituir a chave anterior de forma atômica;
- não retornar a chave real;
- não colocar a chave em logs;
- não aceitar alteração por query string;
- não aceitar chave via `GET`.

### 4.3. Não criar endpoint de leitura da chave

Não deve existir algo como:

```http
GET /settings/gemini/api-key
```

que devolva o segredo.

O status é suficiente para o frontend.

### 4.4. Remoção da chave

Esta spec **não exige endpoint para apagar/desabilitar a chave**.

O objetivo do frontend é cadastrar ou substituir a chave. Evitar um `DELETE` reduz o risco de indisponibilidade acidental de todos os recursos Gemini.

Se remoção explícita se tornar necessária, tratar em spec separada com confirmação apropriada.

---

## 5. Schemas do backend

Em `models/schemas.py` ou no arquivo equivalente utilizado pelo projeto:

### Remover

De `ProjectCreate`:

```text
gemini_api_key
```

De `ProjectResponse`:

```text
has_api_key
```

Também remover qualquer schema específico da antiga atualização por projeto, como:

```text
ApiKeyUpdate
```

caso ainda exista.

### Adicionar

Schemas equivalentes a:

```python
class GeminiApiKeyUpdate(BaseModel):
    api_key: str = Field(min_length=1)


class GeminiApiKeyStatus(BaseModel):
    configured: bool
    key_hint: str | None = None
    updated_at: datetime | None = None
```

O nome exato pode seguir as convenções existentes do repositório.

---

## 6. Remover completamente a chave do domínio de projeto

Em `routers/projects.py`:

- apagar `PATCH /projects/{project_id}/api-key`;
- apagar `ApiKeyUpdate`, caso esteja definido nesse arquivo;
- remover qualquer lógica que leia, salve, atualize, masque ou reporte `gemini_api_key`;
- remover `has_api_key` da função `_sanitize` ou equivalente;
- respostas de projeto não devem mais indicar estado de chave Gemini.

Após a mudança:

```http
PATCH /projects/{id}/api-key
```

deve resultar em **404 de rota**, não `405`.

Criar projeto passa a ser completamente independente de Gemini.

Exemplo válido:

```json
{
  "name": "Projeto XPTO",
  "client": "CITi",
  "subarea": "dev"
}
```

---

## 7. Substituir toda leitura de chave por projeto

Hoje alguns fluxos fazem algo equivalente a:

```python
api_key = project.get("gemini_api_key") or ""
```

Isso deixa de existir.

Todos os fluxos Gemini devem passar a fazer:

```python
api_key = get_gemini_api_key()
```

A chamada não recebe `project_id` nem `subarea`.

### Arquivos conhecidos que precisam ser atualizados

- `routers/ingest.py`
- `routers/generate.py`
- `routers/enrich.py`
- `routers/commit_ingest.py`
- `routers/sprint_docs.py`

Além desses arquivos, fazer uma busca global no repositório para garantir que não ficou nenhum uso antigo.

Executar buscas equivalentes a:

```bash
rg -n "gemini_api_key|has_api_key|updateApiKey|apiKeyInput|GEMINI_API_KEY_DADOS|GEMINI_API_KEY_DEV" .
```

E também conferir todos os pontos de instanciação do cliente Gemini:

```bash
rg -n "ChatGoogleGenerativeAI|google_api_key" docudata-backend
```

### Ajuste dos SELECTs de projeto

Queries de projeto que buscavam `gemini_api_key` exclusivamente para inicializar Gemini não devem mais selecionar essa coluna.

Exemplo:

Antes:

```python
.select("id,name,gemini_api_key,subarea")
```

Depois, selecionar somente os campos realmente usados pelo fluxo:

```python
.select("id,name,subarea")
```

ou menos, se `subarea` também não for necessária naquele endpoint.

**Não adicionar `subarea` apenas para descobrir a chave.**

### `routers/enrich.py`

Se existir `_get_api_key`, alterar para usar a configuração global ou remover a função se ela deixar de agregar valor.

Evitar helpers que ainda recebam projeto somente para retornar a chave.

### `routers/sprint_docs.py`

Se `_project_or_404` atualmente retorna a chave junto com o projeto, remover essa responsabilidade.

`_project_or_404` deve somente validar/carregar o projeto.

A obtenção da chave global deve acontecer separadamente quando o fluxo realmente for chamar Gemini.

---

## 8. Construção dos clientes Gemini

Todos os locais que constroem algo como:

```python
ChatGoogleGenerativeAI(
    ...,
    google_api_key=api_key,
)
```

devem receber `api_key` de `get_gemini_api_key()`.

Importante:

- resolver a chave **uma vez por operação** e reutilizar dentro daquele fluxo;
- não fazer uma consulta ao banco para cada prompt/chamada interna dentro do mesmo request;
- não associar a chave ao projeto;
- não associar a chave à subárea.

Se um service já centraliza a criação do LLM, preferir colocar a resolução da chave nesse service em vez de duplicar lógica nos routers.

O objetivo final é ter o menor número possível de pontos no código que conheçam detalhes da credencial.

---

# Frontend

## 9. Remover configuração Gemini dos projetos

### `app/projects/new/page.tsx`

Remover completamente:

- input "Chave de API do Gemini";
- state `apiKey`;
- validações ligadas a esse campo;
- `gemini_api_key` enviado para `createProject`;
- qualquer texto dizendo que a chave pertence ao projeto.

Criar projeto deve funcionar sem qualquer configuração Gemini no formulário.

### `app/projects/[id]/page.tsx`

Remover completamente:

- `apiKeyInput`;
- `apiKeyMsg`;
- `project.has_api_key`;
- bloco exibido quando `!project.has_api_key`;
- formulário para cadastrar chave do projeto;
- formulário para trocar chave do projeto;
- chamada `updateApiKey`;
- mensagens relacionadas a chave por projeto.

A página de projeto não deve mais saber que existe uma API key Gemini.

---

## 10. Criar uma configuração global no frontend

Criar uma página global de configurações, preferencialmente:

```text
app/settings/page.tsx
```

Se já houver uma página global de configurações na aplicação, adicionar a seção Gemini nela em vez de criar uma rota paralela.

Adicionar acesso a essa página pela navegação principal, de acordo com o padrão visual atual da aplicação.

### 10.1. Card "Gemini"

A tela deve ter uma seção/card com:

```text
Gemini
Chave utilizada pelos recursos de IA de toda a aplicação.
```

### Estado não configurado

Exibir algo como:

```text
Chave não configurada
```

E um campo:

```text
Nova chave Gemini
[********************************]

[Salvar chave]
```

### Estado configurado

Exibir algo como:

```text
Chave configurada
••••••••A1b2
Atualizada em 24/08/2026 às 12:00

[Alterar chave]
```

Ao clicar em `Alterar chave`, mostrar o input para uma **nova** chave.

Nunca preencher o input com a chave atual.

### 10.2. Regras de segurança/UX do campo

Usar:

```tsx
type="password"
```

Preferencialmente com:

```tsx
autoComplete="new-password"
```

Regras:

- o valor existente nunca vem do backend;
- após salvar com sucesso, limpar o state do input;
- não persistir a chave em `localStorage`, `sessionStorage`, cookies ou URL;
- não colocar a chave em toast/log de erro;
- desabilitar o botão durante o request;
- exibir feedback claro de sucesso/erro;
- permitir substituir a chave sem precisar conhecer a anterior.

Opcionalmente, pode existir botão local de mostrar/ocultar o valor **somente enquanto o usuário está digitando a nova chave**. Isso não implica recuperar a chave atual.

### 10.3. Estado inicial

Ao carregar a página:

```http
GET /settings/gemini
```

Usar somente:

```text
configured
key_hint
updated_at
```

---

## 11. Atualizar `app/lib/api.ts`

### Remover

- `updateApiKey` ligado a projeto;
- `gemini_api_key` de `CreateProjectPayload`;
- `has_api_key` da interface `Project`;
- quaisquer tipos antigos referentes a chave por projeto.

### Adicionar

Tipos equivalentes a:

```ts
export interface GeminiApiKeyStatus {
  configured: boolean;
  key_hint: string | null;
  updated_at: string | null;
}
```

Funções equivalentes a:

```ts
export async function getGeminiApiKeyStatus(): Promise<GeminiApiKeyStatus>

export async function updateGeminiApiKey(
  apiKey: string,
): Promise<GeminiApiKeyStatus>
```

`updateGeminiApiKey` deve chamar:

```http
PUT /settings/gemini/api-key
```

Nunca deve existir função frontend para obter a chave real.

---

# Compatibilidade e migração

## 12. Não remover `projects.gemini_api_key` do banco ainda

A coluna:

```text
projects.gemini_api_key
```

continua existindo no schema por enquanto.

Porém:

- não deve ser lida;
- não deve ser escrita;
- não deve ser retornada;
- não deve influenciar nenhum fluxo;
- não deve ser usada como fallback.

Não fazer:

```python
get_gemini_api_key() or project.get("gemini_api_key")
```

A nova configuração global precisa ser a única fonte de verdade.

O `DROP COLUMN` fica explicitamente em backlog para uma migration posterior, depois que a mudança estiver validada em produção.

### Motivo

Separar "parar de usar" de "apagar dados antigos" reduz risco de rollback e torna a implantação reversível.

---

## 13. Não migrar automaticamente uma chave antiga de projeto

Não escolher arbitrariamente uma das antigas `projects.gemini_api_key` como chave global.

Podem existir projetos com valores diferentes, então uma migration automática não teria como determinar corretamente qual segredo deve se tornar a credencial global.

Após o deploy, a chave global deve ser explicitamente configurada pela pessoa responsável através da nova tela de Configurações ou do novo endpoint administrativo.

Até isso acontecer, endpoints que dependem de Gemini retornam o `422` amigável descrito nesta spec.

Endpoints que não usam Gemini continuam funcionando normalmente.

---

# Testes automatizados

## 14. Testes do serviço de segredo

Criar testes unitários para `services/gemini_key.py` cobrindo pelo menos:

### Sem chave cadastrada

`get_gemini_api_key()`:

- consulta a configuração;
- não encontra registro;
- levanta `GeminiApiKeyNotConfigured`.

### Chave cadastrada

- persistir segredo via `set_gemini_api_key("fake-gemini-key")`;
- confirmar que o valor salvo no repositório/tabela **não é igual** a `fake-gemini-key`;
- confirmar que `get_gemini_api_key()` retorna `fake-gemini-key` após descriptografia.

### Troca de chave

- salvar `key-1`;
- salvar `key-2`;
- confirmar que apenas `key-2` é retornada.

### Hint

- confirmar que `get_gemini_api_key_status()` retorna somente o hint esperado;
- confirmar que a resposta não contém a chave completa.

### Secret key do backend ausente/inválida

- comportamento deve ser controlado;
- nenhuma resposta deve revelar o segredo criptografado ou a chave Gemini.

---

## 15. Testes dos endpoints de configuração

### `GET /settings/gemini`

Sem chave:

```json
{
  "configured": false,
  "key_hint": null,
  "updated_at": null
}
```

Com chave:

```json
{
  "configured": true,
  "key_hint": "••••••••...",
  "updated_at": "..."
}
```

Confirmar que nenhum campo contém a chave real.

### `PUT /settings/gemini/api-key`

Cobrir:

- salva primeira chave;
- substitui chave existente;
- rejeita string vazia;
- rejeita somente espaços;
- exige a autenticação já utilizada pela aplicação;
- nunca devolve a chave real no response.

---

## 16. Atualizar testes dos fluxos Gemini

Atualizar os testes que hoje montam mocks de projeto com:

```python
{"gemini_api_key": "..."}
```

para não dependerem mais disso.

O mock de projeto deve conter somente os campos realmente necessários ao endpoint.

Mockar a resolução global da chave, por exemplo:

```python
get_gemini_api_key() -> "global-test-key"
```

ou mockar o armazenamento seguro equivalente.

### Verificação principal

Para os fluxos:

- `POST /ingest`
- `POST /generate`
- `POST /enrich`
- `POST /ingest/commit`
- todos os `/sprint-docs/*` que usam Gemini

mockar `ChatGoogleGenerativeAI` e confirmar que:

```python
google_api_key == "global-test-key"
```

### Projetos de subáreas diferentes

Criar pelo menos:

```text
Projeto A → subarea = dados
Projeto B → subarea = dev
```

Executar fluxo Gemini para ambos e confirmar que os dois usam exatamente:

```text
global-test-key
```

A subárea não pode alterar a chave escolhida.

---

## 17. Teste de chave não configurada

Para cada família principal de endpoint Gemini, garantir que a ausência da configuração global resulte em:

```text
HTTP 422
```

com mensagem amigável semelhante a:

```text
A chave Gemini da aplicação ainda não está configurada.
```

Não pode resultar em:

- `500` por `None`;
- erro de descriptografia vazando stacktrace;
- tentativa de instanciar Gemini com `google_api_key=""`;
- fallback para `projects.gemini_api_key`.

---

# Busca obrigatória de referências antigas

Antes de considerar a implementação concluída, executar uma busca global no backend e frontend.

Exemplo:

```bash
rg -n \
  "gemini_api_key|has_api_key|updateApiKey|apiKeyInput|apiKeyMsg|GEMINI_API_KEY_DADOS|GEMINI_API_KEY_DEV" \
  docudata-backend docudata-frontend
```

Os únicos usos aceitáveis de `gemini_api_key` após esta spec são:

1. o identificador da configuração global, por exemplo `app_settings.key = "gemini_api_key"`;
2. a coluna legada `projects.gemini_api_key` em migration/schema histórico;
3. testes explicitamente verificando que o legado não é mais utilizado.

Não deve restar código de aplicação lendo ou escrevendo a coluna do projeto.

---

# Critérios de aceite

- [ ] Existe **uma única chave Gemini ativa para toda a aplicação**.
- [ ] Projetos `dados` e `dev` usam a mesma chave global.
- [ ] A chave global pode ser cadastrada pelo frontend.
- [ ] A chave global pode ser substituída pelo frontend sem informar a chave anterior.
- [ ] O frontend nunca recebe a chave atual em texto plano.
- [ ] A chave não é salva em `localStorage`, `sessionStorage`, cookie ou URL.
- [ ] A chave persistida no banco está criptografada.
- [ ] `DOCUDATA_SECRETS_KEY` permanece somente no ambiente do backend.
- [ ] A API nunca inclui a chave Gemini em logs, responses ou mensagens de erro.
- [ ] `GET /settings/gemini` informa apenas status, hint e data de atualização.
- [ ] `PUT /settings/gemini/api-key` cadastra/substitui a chave global.
- [ ] A rota de alteração da configuração exige a autenticação já utilizada pela aplicação.
- [ ] `PATCH /projects/{id}/api-key` não existe mais e retorna 404 de rota.
- [ ] `ProjectCreate` não possui `gemini_api_key`.
- [ ] `ProjectResponse` não possui `has_api_key`.
- [ ] Criar projeto sem qualquer informação Gemini funciona normalmente.
- [ ] `POST /ingest`, `POST /generate`, `POST /enrich`, `POST /ingest/commit` e `/sprint-docs/*` usam `get_gemini_api_key()` ou abstração central equivalente.
- [ ] Nenhum desses fluxos lê `projects.gemini_api_key`.
- [ ] Nenhum desses fluxos escolhe chave com base em `subarea`.
- [ ] Sem chave global configurada, endpoints que usam Gemini retornam `422` amigável.
- [ ] Endpoints que não usam Gemini continuam funcionando mesmo sem chave configurada.
- [ ] `projects.gemini_api_key` continua existindo fisicamente no banco, mas está sem uso.
- [ ] Não existe fallback silencioso para a antiga chave por projeto.
- [ ] Testes confirmam que projetos `dados` e `dev` recebem a mesma `google_api_key` ao instanciar `ChatGoogleGenerativeAI`.
- [ ] Testes confirmam que a chave armazenada não está em texto plano.
- [ ] `pytest` passa.
- [ ] `npm run build` passa.
- [ ] Busca global não encontra referências frontend restantes a `has_api_key`, `apiKeyInput`, `apiKeyMsg` ou `updateApiKey`.

---

# Como testar manualmente

## 1. Configurar chave de criptografia do backend

```bash
export DOCUDATA_SECRETS_KEY="<fernet-key-valida>"
```

Para gerar uma chave local:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 2. Subir a aplicação sem chave Gemini global cadastrada

Criar um projeto normalmente:

```bash
PROJ=$(curl -s -X POST http://localhost:8000/projects \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name":"Teste Dev","client":"CITi","subarea":"dev"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
```

Esperado: projeto criado normalmente.

---

## 3. Confirmar que endpoint sem Gemini continua funcionando

```bash
curl -i -X POST http://localhost:8000/docs/manual \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -H "Content-Type: application/json" \
  -d "{\"projeto_id\":\"$PROJ\",\"doc_type\":\"log_decisoes\",\"content\":\"teste\"}"
```

Esperado:

```text
201
```

---

## 4. Confirmar erro amigável antes de configurar Gemini

```bash
curl -i -X POST http://localhost:8000/generate \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -H "Content-Type: application/json" \
  -d "{\"projeto_id\":\"$PROJ\",\"tipo_doc\":\"log_decisoes\"}"
```

Esperado:

```text
422
```

Com mensagem semelhante a:

```text
A chave Gemini da aplicação ainda não está configurada.
```

---

## 5. Cadastrar a chave global

```bash
curl -i -X PUT http://localhost:8000/settings/gemini/api-key \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"<chave-real-ou-fake>"}'
```

Esperado:

```text
200
```

Response semelhante a:

```json
{
  "configured": true,
  "key_hint": "••••••••xxxx",
  "updated_at": "..."
}
```

A chave completa não pode aparecer na resposta.

---

## 6. Consultar status

```bash
curl -s http://localhost:8000/settings/gemini \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET"
```

Esperado:

```json
{
  "configured": true,
  "key_hint": "••••••••xxxx",
  "updated_at": "..."
}
```

---

## 7. Trocar a chave

```bash
curl -i -X PUT http://localhost:8000/settings/gemini/api-key \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"<segunda-chave>"}'
```

Esperado:

- `200`;
- novo `key_hint`;
- próxima operação Gemini utiliza a segunda chave;
- não é necessário restart do backend;
- não é necessário alterar projeto algum.

---

## 8. Confirmar independência de subárea

Criar também um projeto de Dados:

```bash
PROJ_DADOS=$(curl -s -X POST http://localhost:8000/projects \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name":"Teste Dados","client":"CITi","subarea":"dados"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
```

Executar um fluxo Gemini com o projeto `dev` e outro com o projeto `dados`.

Esperado: ambos usam a mesma chave global atualmente configurada.

Em ambiente automatizado, confirmar isso mockando `ChatGoogleGenerativeAI` e inspecionando `google_api_key`.

---

## 9. Validar frontend

Na tela global de Configurações:

1. abrir com chave ainda não cadastrada;
2. confirmar estado "Chave não configurada";
3. cadastrar uma chave;
4. confirmar que o input é limpo após sucesso;
5. recarregar a página;
6. confirmar que aparece somente o hint, não a chave;
7. clicar em "Alterar chave";
8. salvar outro valor;
9. confirmar atualização do hint/data;
10. abrir um projeto e confirmar que não existe mais seção de chave Gemini.

---

# Fora de escopo

Esta spec não inclui:

- `DROP COLUMN projects.gemini_api_key`;
- chave Gemini diferente por subárea;
- chave Gemini diferente por projeto;
- rotação automática de credenciais;
- histórico de versões da chave;
- auditoria completa de quem alterou a chave, caso a aplicação ainda não tenha identidade individual de usuário;
- botão para apagar/desabilitar a chave;
- validação online da chave no momento do cadastro;
- cache distribuído da configuração;
- mudança das regras de `subarea`.

Esses itens podem ser tratados separadamente se houver necessidade.

---

# Backlog explícito após estabilização

Depois que essa mudança estiver validada em produção por um período seguro:

1. criar migration separada para `DROP COLUMN projects.gemini_api_key`;
2. remover referências históricas que não forem mais necessárias;
3. avaliar auditoria de alterações da chave (`updated_by`) quando houver identidade de usuário apropriada;
4. avaliar integração com secret manager dedicado caso a infraestrutura evolua para isso.

---

# Resultado esperado da arquitetura

Ao final da implementação, o fluxo deve ser conceitualmente:

```text
Frontend / Configurações
        │
        │ PUT nova chave
        ▼
Backend /settings/gemini/api-key
        │
        │ criptografa com DOCUDATA_SECRETS_KEY
        ▼
app_settings
        │
        │ encrypted_value
        ▼

Qualquer endpoint que usa IA
        │
        ▼
get_gemini_api_key()
        │
        │ lê + descriptografa
        ▼
ChatGoogleGenerativeAI(google_api_key=<chave-global>)
```

Projetos participam somente como contexto funcional da operação:

```text
project.id
project.subarea
project.client
...
```

A credencial Gemini não pertence mais a esse domínio.
