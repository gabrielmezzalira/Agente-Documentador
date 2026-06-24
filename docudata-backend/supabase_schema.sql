-- DocuData — Supabase schema
-- Run this in the Supabase SQL Editor to create all three tables.

CREATE TABLE projects (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text        NOT NULL,
    client          text        NOT NULL,
    description     text,
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
    tipo_documentacao text        CHECK (tipo_documentacao IS NULL OR tipo_documentacao IN ('planning','daily','review','outro')),
    extracted_content jsonb,
    input_tokens      int         DEFAULT 0,
    output_tokens     int         DEFAULT 0,
    cost_usd          float       DEFAULT 0,
    created_at        timestamptz DEFAULT now()
);

-- Se as tabelas já existem, rode apenas os ALTERs abaixo:
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_delivered boolean NOT NULL DEFAULT false;
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS budget_usd float;
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
