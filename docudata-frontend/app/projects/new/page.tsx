"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createProject } from "../../lib/api";

export default function NewProject() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [description, setDescription] = useState("");
  const [budgetStr, setBudgetStr] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const budget_usd = budgetStr.trim() ? parseFloat(budgetStr) : null;
    try {
      const project = await createProject({ name, client, description, budget_usd, gemini_api_key: apiKey || undefined });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar projeto");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 520, margin: "0 auto", padding: "52px 24px" }}>
      <Link href="/" style={{ fontSize: 13, color: "#9696a0", display: "inline-flex", alignItems: "center", gap: 6 }}>
        ← Projetos
      </Link>

      <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116", marginTop: 28, marginBottom: 6 }}>
        Novo projeto
      </h1>
      <p style={{ color: "#9696a0", marginBottom: 36, fontSize: 14 }}>Preencha as informações básicas.</p>

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

        <div>
          <label style={labelStyle}>Chave de API do Gemini</label>
          <input style={inputStyle} type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="AIza..." />
          <p style={{ marginTop: 6, fontSize: 12, color: "#b8b8c0", lineHeight: 1.5 }}>
            Obtida em <strong style={{ color: "#9696a0" }}>aistudio.google.com</strong> → Get API Key.
          </p>
        </div>

        <div>
          <label style={labelStyle}>
            Budget de IA{" "}
            <span style={{ color: "#b8b8c0", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>em USD (opcional)</span>
          </label>
          <input style={inputStyle} type="number" min="0" step="0.01" value={budgetStr} onChange={(e) => setBudgetStr(e.target.value)} placeholder="Ex: 1.00" />
          <p style={{ marginTop: 6, fontSize: 12, color: "#b8b8c0" }}>Limite de gasto com o Gemini. Deixe em branco para sem limite.</p>
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
