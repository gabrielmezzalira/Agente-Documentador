# Commit tracker do Agente Documentador

O tracker registra automaticamente cada `push` como uma ingestão de commit no
projeto correspondente. O script usa somente módulos da biblioteca padrão do
Python e não exige instalação de pacotes no repositório da squad.

## Instalando em um projeto de Dev

1. No Agente Documentador, acesse `/dev/projects/new` e crie o projeto da squad.
2. Copie o UUID exibido na URL do projeto. Esse será o
   `DOCUDATA_PROJECT_ID`; a subárea Dev já fica implícita nesse UUID.
3. Copie os arquivos para o repositório da squad:

   ```bash
   mkdir -p .github/workflows scripts
   cp <caminho>/docudata_agent.py scripts/docudata_agent.py
   cp <caminho>/docudata.yml .github/workflows/docudata.yml
   ```

4. Em **Settings → Secrets and variables → Actions**, crie estes Repository
   Secrets:

   - `DOCUDATA_API_URL`: URL pública do backend no Railway, sem uma rota no final.
   - `DOCUDATA_PROJECT_ID`: UUID do projeto de Dev criado no passo 1.
   - `DOCUDATA_APP_SECRET`: mesmo valor configurado no backend; solicite-o a quem
     administra o Railway.

5. Versione os dois arquivos e faça um `push`. A execução aparecerá na aba
   **Actions** e o commit receberá o status do Agente Documentador.

Não existe flag ou variável de "modo Dev". A instalação é igual à de Dados; o
backend identifica a subárea exclusivamente pelo `DOCUDATA_PROJECT_ID`.

Para atribuir um commit a uma sprint diferente da detectada automaticamente,
adicione o marcador `[sprint:N]` à mensagem:

```bash
git commit -m "feat: nova tela [sprint:4]"
```
