-- DocuData — Supabase schema
-- Run this in the Supabase SQL Editor to create all three tables.

CREATE TABLE projects (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text        NOT NULL,
    client          text        NOT NULL,
    description     text,
    squad           text,           -- membros e papéis do squad do projeto
    budget_usd      float,          -- NULL = sem limite; valor em USD
    gemini_api_key  text,           -- chave por projeto; nunca exposta na API
    is_delivered    boolean     NOT NULL DEFAULT false,
    created_at      timestamptz DEFAULT now()
);

CREATE TABLE ingestions (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid        REFERENCES projects(id) ON DELETE CASCADE,
    sprint_number     int         NOT NULL,
    file_name         text,
    file_type         text,
    tipo_documentacao text        CHECK (tipo_documentacao IS NULL OR tipo_documentacao IN ('planning','daily','review','retrospectiva','commit','outro')),
    extracted_content jsonb,
    input_tokens      int         DEFAULT 0,
    output_tokens     int         DEFAULT 0,
    cost_usd          float       DEFAULT 0,
    created_at        timestamptz DEFAULT now()
);

-- Se as tabelas já existem, rode apenas os ALTERs abaixo:
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_delivered boolean NOT NULL DEFAULT false;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS budget_usd float;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS squad text;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS gemini_api_key text;
-- ALTER TABLE generated_docs ADD COLUMN IF NOT EXISTS input_tokens int DEFAULT 0;
-- ALTER TABLE generated_docs ADD COLUMN IF NOT EXISTS output_tokens int DEFAULT 0;
-- ALTER TABLE generated_docs ADD COLUMN IF NOT EXISTS cost_usd float DEFAULT 0;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS input_tokens int DEFAULT 0;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS output_tokens int DEFAULT 0;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS cost_usd float DEFAULT 0;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS tipo_documentacao text;
-- ALTER TABLE ingestions ADD CONSTRAINT ingestions_tipo_documentacao_check
--   CHECK (tipo_documentacao IS NULL OR tipo_documentacao IN ('planning','daily','review','outro'));

-- Migration v2: adicionar 'retrospectiva' e 'commit' ao tipo_documentacao
-- ALTER TABLE ingestions DROP CONSTRAINT ingestions_tipo_documentacao_check;
-- ALTER TABLE ingestions ADD CONSTRAINT ingestions_tipo_documentacao_check
--   CHECK (tipo_documentacao IS NULL OR tipo_documentacao IN ('planning','daily','review','retrospectiva','commit','outro'));

CREATE TABLE generated_docs (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    uuid        REFERENCES projects(id) ON DELETE CASCADE,
    doc_type      text        NOT NULL,
    sprint_number int,
    content       text        NOT NULL,
    input_tokens  int         DEFAULT 0,
    output_tokens int         DEFAULT 0,
    cost_usd      float       DEFAULT 0,
    created_at    timestamptz DEFAULT now()
);

-- v1.1 — Sprint como entidade + semáforo de saúde
CREATE TABLE sprints (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    numero          int         NOT NULL,
    status_saude    text        CHECK (status_saude IS NULL OR status_saude IN ('verde','amarelo','vermelho')),
    plano_correcao  text,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (project_id, numero)
);

-- Backfill — cria uma sprint para cada (project_id, sprint_number) já presente em ingestions
INSERT INTO sprints (project_id, numero)
SELECT DISTINCT project_id, sprint_number FROM ingestions
ON CONFLICT (project_id, numero) DO NOTHING;

-- Se as tabelas já existem, rode também:
-- CREATE TABLE IF NOT EXISTS sprints (
--     id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
--     project_id      uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
--     numero          int         NOT NULL,
--     status_saude    text        CHECK (status_saude IS NULL OR status_saude IN ('verde','amarelo','vermelho')),
--     plano_correcao  text,
--     created_at      timestamptz DEFAULT now(),
--     updated_at      timestamptz DEFAULT now(),
--     UNIQUE (project_id, numero)
-- );
-- INSERT INTO sprints (project_id, numero)
-- SELECT DISTINCT project_id, sprint_number FROM ingestions
-- ON CONFLICT (project_id, numero) DO NOTHING;

-- Migration v3: subárea do projeto (dados | dev)
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS subarea text NOT NULL DEFAULT 'dados';
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check
--   CHECK (subarea IN ('dados','dev'));

-- Migration v4: configuração global e criptografada da chave Gemini
-- Executar manualmente no Supabase SQL Editor. Não há policy para acesso pelo browser.
-- CREATE TABLE IF NOT EXISTS app_settings (
--     key             text        PRIMARY KEY,
--     encrypted_value text        NOT NULL,
--     display_hint    text,
--     updated_at      timestamptz NOT NULL DEFAULT now()
-- );
-- ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- Migration v5: integração aditiva com repositórios GitHub (Spec 08)
-- NÃO é executada pela aplicação. Validar em staging e aplicar manualmente com
-- backup/ponto de restauração antes do rollout. Não há DROP, backfill ou alteração
-- de linhas existentes.
-- CREATE TABLE IF NOT EXISTS project_repositories (
--     id                       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
--     project_id               uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
--     github_repository_id     bigint      NOT NULL UNIQUE,
--     installation_id          bigint      NOT NULL,
--     full_name                text        NOT NULL,
--     html_url                 text        NOT NULL,
--     default_branch           text,
--     active                   boolean     NOT NULL DEFAULT true,
--     inactive_reason          text,
--     connected_at             timestamptz NOT NULL DEFAULT now(),
--     updated_at               timestamptz NOT NULL DEFAULT now()
-- );
-- CREATE INDEX IF NOT EXISTS project_repositories_project_id_idx
--     ON project_repositories (project_id);
-- CREATE INDEX IF NOT EXISTS project_repositories_installation_id_idx
--     ON project_repositories (installation_id);
--
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS source_repository_id uuid
--     REFERENCES project_repositories(id);
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS source_repository_full_name text;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS source_commit_sha text;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS source_branch text;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS source_url text;
-- ALTER TABLE ingestions ADD COLUMN IF NOT EXISTS source_diff_stat text;
-- CREATE UNIQUE INDEX IF NOT EXISTS ingestions_repository_commit_unique_idx
--     ON ingestions (source_repository_id, source_commit_sha)
--     WHERE source_commit_sha IS NOT NULL;
--
-- CREATE TABLE IF NOT EXISTS github_webhook_deliveries (
--     delivery_id text        PRIMARY KEY,
--     event       text        NOT NULL,
--     status      text        NOT NULL,
--     attempts    int         NOT NULL DEFAULT 1,
--     last_error  text,
--     created_at  timestamptz NOT NULL DEFAULT now(),
--     updated_at  timestamptz NOT NULL DEFAULT now()
-- );
--
-- Sessões curtas persistidas garantem state e token de conexão de uso único,
-- inclusive se o Railway reiniciar entre o redirect do GitHub e a confirmação.
-- CREATE TABLE IF NOT EXISTS github_connection_sessions (
--     id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
--     project_id            uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
--     state_hash            text        NOT NULL UNIQUE,
--     connection_token_hash text        UNIQUE,
--     installation_id       bigint,
--     status                text        NOT NULL DEFAULT 'pending',
--     expires_at            timestamptz NOT NULL,
--     created_at            timestamptz NOT NULL DEFAULT now(),
--     updated_at            timestamptz NOT NULL DEFAULT now()
-- );
-- CREATE INDEX IF NOT EXISTS github_connection_sessions_project_id_idx
--     ON github_connection_sessions (project_id);
