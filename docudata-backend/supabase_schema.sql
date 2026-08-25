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

-- Phase 7: Funcionalidades, Transições de Status e campos de contrato em projects
CREATE TABLE IF NOT EXISTS funcionalidades (
    id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              uuid        REFERENCES projects(id) ON DELETE CASCADE,
    id_funcional            text        NOT NULL,
    titulo                  text        NOT NULL,
    descricao               text,
    criterios_aceite        text[]      NOT NULL DEFAULT '{}',
    prioridade              text        NOT NULL DEFAULT 'should',
    status                  text        NOT NULL DEFAULT 'nao_iniciada',
    status_cliente          text        NOT NULL DEFAULT 'nao_enviado',
    data_aprovacao_cliente  date,
    responsavel             text,
    sprint_alvo             text,
    testes_e2e              text[]      NOT NULL DEFAULT '{}',
    created_at              timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transicoes_status (
    id                              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    funcionalidade_id               uuid        REFERENCES funcionalidades(id) ON DELETE CASCADE,
    campo                           text        NOT NULL,
    de                              text        NOT NULL,
    para                            text        NOT NULL,
    autor                           text,
    timestamp                       timestamptz DEFAULT now(),
    motivo                          text,
    duracao_fase_anterior_segundos  integer
);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS data_inicio              date;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS data_fim_contratada      date;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tolerancia_desvio_pontos integer DEFAULT 20;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS periodo_garantia_dias    integer DEFAULT 30;

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

-- Phase 10: Composer de Planning
CREATE TABLE IF NOT EXISTS planning_rascunhos (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_numero int         NOT NULL,
    step_atual    int         NOT NULL DEFAULT 1,
    dados_json    jsonb       NOT NULL DEFAULT '{}',
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now(),
    UNIQUE (project_id, sprint_numero)
);

-- Se a tabela já existe, rode apenas:
-- CREATE TABLE IF NOT EXISTS planning_rascunhos (
--     id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
--     project_id    uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
--     sprint_numero int         NOT NULL,
--     step_atual    int         NOT NULL DEFAULT 1,
--     dados_json    jsonb       NOT NULL DEFAULT '{}',
--     created_at    timestamptz DEFAULT now(),
--     updated_at    timestamptz DEFAULT now(),
--     UNIQUE (project_id, sprint_numero)
-- );

-- Phase 11: Suíte de Verificação de Aceite
-- Migration incremental: executar no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS execucoes_aceite (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    funcionalidade_id uuid        NOT NULL REFERENCES funcionalidades(id) ON DELETE CASCADE,
    project_id        uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    commit_sha        text        NOT NULL,
    gates             jsonb       NOT NULL DEFAULT '[]'::jsonb,
    disparado_em      timestamptz NOT NULL DEFAULT now(),
    concluido_em      timestamptz
);

CREATE INDEX IF NOT EXISTS idx_execucoes_aceite_project
    ON execucoes_aceite (project_id, disparado_em DESC);

CREATE INDEX IF NOT EXISTS idx_execucoes_aceite_func
    ON execucoes_aceite (funcionalidade_id, disparado_em DESC);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS github_token text,
    ADD COLUMN IF NOT EXISTS github_repo  text;

ALTER TABLE funcionalidades
    ADD COLUMN IF NOT EXISTS testes_e2e text[] NOT NULL DEFAULT '{}';

-- Se as tabelas já existem, rode os ALTERs acima individualmente no SQL Editor.

-- Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal
-- Migration incremental: executar no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS boletins_aceite (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_numero       int,
    funcionalidade_ids  text[]      NOT NULL DEFAULT '{}',
    status              text        NOT NULL DEFAULT 'rascunho'
                                    CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'ajuste')),
    retorno_tipo        text        CHECK (retorno_tipo IS NULL OR retorno_tipo IN ('bug', 'mudanca_escopo')),
    conteudo            text        NOT NULL DEFAULT '',
    criado_em           timestamptz NOT NULL DEFAULT now(),
    enviado_em          timestamptz,
    retorno_em          timestamptz
);

CREATE INDEX IF NOT EXISTS idx_boletins_aceite_project
    ON boletins_aceite (project_id, criado_em DESC);

-- Planning Redesign: sprint_funcionalidades
-- Vincula funcionalidades a sprints com tasks e status de conclusão.
-- Migration incremental: executar no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS sprint_funcionalidades (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    sprint_id         uuid        NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    funcionalidade_id uuid        NOT NULL REFERENCES funcionalidades(id) ON DELETE CASCADE,
    status            text        NOT NULL DEFAULT 'em_andamento'
                                  CHECK (status IN ('em_andamento', 'concluida')),
    tasks             jsonb       NOT NULL DEFAULT '[]',
    created_at        timestamptz DEFAULT now(),
    UNIQUE (sprint_id, funcionalidade_id)
);

CREATE INDEX IF NOT EXISTS idx_sprint_funcionalidades_sprint
    ON sprint_funcionalidades (sprint_id);

CREATE INDEX IF NOT EXISTS idx_sprint_funcionalidades_func
    ON sprint_funcionalidades (funcionalidade_id);
