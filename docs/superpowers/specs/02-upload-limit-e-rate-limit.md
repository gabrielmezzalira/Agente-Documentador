# Spec 02 — Limite de upload + rate limiting

**Prioridade:** crítica · **Depende de:** nada (pode ser feita em paralelo com a 01) · **Bloqueia:** nada

## Problema

Nenhum endpoint de upload valida tamanho antes de ler o arquivo inteiro em memória
(`await arquivo.read()` em `ingest.py`, `enrich.py`, `sprint_docs.py`, `generate.py`).
E nenhum endpoint tem limite de chamadas — como cada ingestão/geração dispara uma
chamada paga ao Gemini, isso é uma porta aberta pra gasto descontrolado, seja por
abuso, seja por um script/CI mal configurado batendo em loop.

## Escopo

### 1. Limite de tamanho de upload

- Nova env var `MAX_UPLOAD_MB` (default `20` no código caso a env var não exista).
- Adicionar um middleware (ou dependency, o que for mais simples de aplicar de forma
  centralizada) que rejeita com **413** qualquer request cujo `Content-Length` exceda
  `MAX_UPLOAD_MB * 1024 * 1024`, **antes** de o handler chamar `arquivo.read()`.
- Aplique isso globalmente (middleware em `main.py`), não endpoint por endpoint —
  mais fácil de garantir cobertura completa.
- Se o `Content-Length` não vier no header (alguns clients HTTP omitem em streaming),
  não bloqueie por ausência — apenas valide quando o header existir. (Ficar 100%
  à prova de upload sem `Content-Length` exigiria leitura em chunks; fora de escopo
  agora, mas deixe um comentário no código apontando essa limitação.)

### 2. Rate limiting

- Adicionar `slowapi` ao `requirements.txt` (biblioteca já madura para FastAPI,
  baseada em `limits`).
- Nova env var `RATE_LIMIT_PER_MINUTE` (default `20` no código).
- Aplicar o limite **por IP** nos endpoints que chamam Gemini (todos que hoje
  instanciam `ChatGoogleGenerativeAI` direta ou indiretamente via grafo):
  `POST /ingest`, `POST /generate`, `POST /enrich`, `POST /ingest/commit`,
  `POST /sprint-docs/planning`, `POST /sprint-docs/daily`, `POST /sprint-docs/ata`,
  `POST /sprint-docs/review`, `POST /sprint-docs/retrospectiva`.
- Resposta ao estourar o limite: `429` com `Retry-After` (o `slowapi` já cuida disso
  por padrão, não precisa reinventar).
- **Atenção:** Railway normalmente está atrás de proxy — confirme que o IP do
  cliente é lido corretamente (`X-Forwarded-For`) e não sempre o IP do proxy, senão
  todo mundo vira "o mesmo IP" e o rate limit fica global sem querer. Configure o
  `key_func` do `slowapi` para usar `get_remote_address` considerando
  `X-Forwarded-For` quando presente.

### Não faz parte desta spec

- Rate limit por projeto/subárea (fica pra depois se virar problema real) — por
  enquanto é só por IP, simples.
- Sanitização de mensagens de erro (`detail=f"...{exc}"` vazando stacktrace) — vale
  a pena, mas não é crítico e fica de backlog explícito, não implementar agora.

## Critérios de aceite

- [ ] Upload de arquivo maior que `MAX_UPLOAD_MB` retorna `413` sem que o backend
      chegue a processar o arquivo (confirme que não há log de início de
      processamento do Gemini pra esse caso).
- [ ] Uma sequência de requests acima de `RATE_LIMIT_PER_MINUTE` no mesmo IP para um
      dos endpoints listados retorna `429` a partir da N+1ª chamada dentro da janela.
- [ ] `GET /health`, `GET /projects`, `GET /ingestions/...` (endpoints só de leitura,
      que não chamam Gemini) **não** têm rate limit aplicado — não faz sentido
      limitar leitura da mesma forma que geração paga.
- [ ] `pytest` continua passando (endpoints de teste que batem várias vezes seguidas
      no mesmo endpoint limitado podem precisar de ajuste ou de um bypass de rate
      limit em ambiente de teste — ok resolver isso desabilitando o limiter quando
      `ENV=test` ou equivalente, documente a decisão no código).

## Como testar manualmente

```bash
# upload grande — ajuste o tamanho do arquivo de teste para passar do MAX_UPLOAD_MB
dd if=/dev/urandom of=/tmp/grande.pdf bs=1M count=25
curl -i -X POST http://localhost:8000/ingest \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" \
  -F "arquivo=@/tmp/grande.pdf" -F "sprint_numero=1" -F "projeto_id=<uuid>"
# esperado: 413

# rate limit — dispare 25 requests rápidas contra um endpoint limitado e confirme 429
for i in $(seq 1 25); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/generate \
    -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" -H "Content-Type: application/json" \
    -d '{"projeto_id":"<uuid>","tipo_doc":"log_decisoes"}'
done
```
