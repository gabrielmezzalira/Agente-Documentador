-- DocuData — Supabase schema
-- Run this in the Supabase SQL Editor to create all three tables.

CREATE TABLE projects (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL,
    client      text        NOT NULL,
    description text,
    created_at  timestamptz DEFAULT now()
);

CREATE TABLE ingestions (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid        REFERENCES projects(id) ON DELETE CASCADE,
    sprint_number     int         NOT NULL,
    file_name         text,
    file_type         text,
    extracted_content jsonb,
    created_at        timestamptz DEFAULT now()
);

CREATE TABLE generated_docs (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   uuid        REFERENCES projects(id) ON DELETE CASCADE,
    doc_type     text        NOT NULL,
    sprint_number int,
    content      text        NOT NULL,
    created_at   timestamptz DEFAULT now()
);
