"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { createProject, type Subarea } from "../../../lib/api";

export default function NewProject() {
  const router = useRouter();
  const { subarea } = useParams<{ subarea: Subarea }>();
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [description, setDescription] = useState("");
  const [squad, setSquad] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const subareaLabel = subarea === "dev" ? "Dev" : "Dados";
  const subareaColor = subarea === "dev" ? "#1d4ed8" : "#15803d";
  const subareaBackground = subarea === "dev" ? "#eff6ff" : "#ecfdf3";

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
    <main style={{ maxWidth: 520, margin: "0 auto", padding: "52px 24px" }}>
      <Link href={`/${subarea}`} style={{ fontSize: 13, color: "#9696a0", display: "inline-flex", alignItems: "center", gap: 6 }}>
        ← Projetos
      </Link>

      <span style={{ display: "inline-flex", marginTop: 28, padding: "5px 9px", borderRadius: 999, color: subareaColor, background: subareaBackground, fontSize: 11, fontWeight: 750 }}>
        Subárea de {subareaLabel}
      </span>
      <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116", marginTop: 12, marginBottom: 6 }}>
        Novo projeto de {subareaLabel}
      </h1>
      <p style={{ color: "#737380", marginBottom: 36, fontSize: 14, lineHeight: 1.55 }}>
        O projeto será cadastrado automaticamente em {subareaLabel}. Você poderá alterar essa classificação nas configurações do projeto.
      </p>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        <div>
          <label style={labelStyle}>Nome do projeto *</label>
          <input style={inputStyle} value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex: Pipeline de Vendas" required />
        </div>

        <div>
          <label style={labelStyle}>Cliente *</label>
          <input style={inputStyle} value={client} onChange={(e) => setClient(e.target.value)} placeholder="Ex: Empresa XYZ" required />
        </div>

        <div>
          <label style={labelStyle}>
            Squad{" "}
            <span style={{ color: "#b8b8c0", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(opcional)</span>
          </label>
          <input style={inputStyle} value={squad} onChange={(e) => setSquad(e.target.value)} placeholder="Ex: Gabriel, Julia, Pedro" />
        </div>

        <div>
          <label style={labelStyle}>
            Descrição{" "}
            <span style={{ color: "#b8b8c0", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(opcional)</span>
          </label>
          <textarea
            style={{ ...inputStyle, height: 96, resize: "vertical" }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Breve descrição do escopo..."
          />
        </div>

        {error && <p style={{ color: "#dc2626", fontSize: 14 }}>{error}</p>}

        <button type="submit" disabled={loading} style={btnStyle}>
          {loading ? "Criando..." : "Criar projeto"}
        </button>
      </form>
    </main>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 700,
  marginBottom: 7,
  color: "#6a6a7a",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "11px 14px",
  background: "#ffffff",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  fontSize: 14,
  outline: "none",
  color: "#111116",
};

const btnStyle: React.CSSProperties = {
  background: "#4ade80",
  color: "#0a0a0a",
  border: "none",
  borderRadius: 8,
  padding: "13px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
  letterSpacing: "0.01em",
};
