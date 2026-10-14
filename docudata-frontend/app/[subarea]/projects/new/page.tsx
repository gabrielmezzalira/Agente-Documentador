"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { createProject, type Subarea } from "../../../lib/api";
import { ds } from "../../../lib/ds";
import { Button, Card, Chip, ErrorNotice, Field, Input, Textarea } from "../../../components/ds";

const LABEL: Record<Subarea, string> = { dados: "Dados", dev: "Dev", produto: "Produto" };

export default function NewProject() {
  const router = useRouter();
  const { subarea } = useParams<{ subarea: Subarea }>();
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [description, setDescription] = useState("");
  const [squad, setSquad] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const subareaLabel = LABEL[subarea] ?? "Dados";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const project = await createProject({ name, client, subarea, description, squad: squad || undefined });
      router.push(`/${subarea}/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar projeto");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 640, display: "flex", flexDirection: "column", gap: 24 }}>
      <Link href={`/${subarea}`} style={{ fontSize: 13, color: ds.muted }}>← Projetos</Link>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
        <Chip tone="green" dot>Subárea de {subareaLabel}</Chip>
        <h1 style={{ fontSize: 38, lineHeight: 1.05, fontWeight: 700, letterSpacing: "-0.03em", color: ds.white }}>Novo projeto de {subareaLabel}</h1>
        <p style={{ fontSize: 14.5, lineHeight: 1.6, color: ds.muted }}>
          {subarea === "produto"
            ? "O projeto nasce em Produto para o discovery. Quando estiver maduro, é encaminhado para Dados ou Dev levando todo o contexto."
            : `O projeto será cadastrado automaticamente em ${subareaLabel}. Você poderá alterar essa classificação nas configurações do projeto.`}
        </p>
      </div>

      <Card style={{ padding: "26px 28px" }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <Field label="Nome do projeto" htmlFor="np-name" required>
            <Input id="np-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex: Pipeline de Vendas" required />
          </Field>
          <Field label="Cliente" htmlFor="np-client" required>
            <Input id="np-client" value={client} onChange={(e) => setClient(e.target.value)} placeholder="Ex: Empresa XYZ" required />
          </Field>
          <Field label="Squad (opcional)" htmlFor="np-squad">
            <Input id="np-squad" value={squad} onChange={(e) => setSquad(e.target.value)} placeholder="Ex: Gabriel, Julia, Pedro" />
          </Field>
          <Field label="Descrição (opcional)" htmlFor="np-desc">
            <Textarea id="np-desc" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Breve descrição do escopo…" />
          </Field>

          {error && <ErrorNotice>{error}</ErrorNotice>}

          <div>
            <Button type="submit" variant="primary" disabled={loading}>{loading ? "Criando…" : "Criar projeto"}</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
