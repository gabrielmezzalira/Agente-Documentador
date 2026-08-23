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

-- Phase 9: Revisor Diário
CREATE TABLE IF NOT EXISTS revisoes_diarias (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data_revisao        date        NOT NULL,
    achados             jsonb       NOT NULL DEFAULT '[]',
    relatorio_gerente   text        NOT NULL DEFAULT '',
    relatorio_tecnico   text        NOT NULL DEFAULT '',
    commits_analisados  int         NOT NULL DEFAULT 0,
    diff_chars_total    int         NOT NULL DEFAULT 0,
    created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_revisoes_diarias_project_created
    ON revisoes_diarias (project_id, created_at DESC);

-- Se a tabela já existe, rode:
-- CREATE TABLE IF NOT EXISTS revisoes_diarias ( ... );
-- CREATE INDEX IF NOT EXISTS idx_revisoes_diarias_project_created ON revisoes_diarias (project_id, created_at DESC);

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
