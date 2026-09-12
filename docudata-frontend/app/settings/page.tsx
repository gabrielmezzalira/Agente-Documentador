"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  getGeminiApiKeyStatus,
  updateGeminiApiKey,
  type GeminiApiKeyStatus,
} from "../lib/api";


export default function SettingsPage() {
  const [status, setStatus] = useState<GeminiApiKeyStatus | null>(null);
  const [newKey, setNewKey] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    getGeminiApiKeyStatus()
      .then(setStatus)
      .catch(() => setMessage({ ok: false, text: "Não foi possível carregar a configuração." }))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!newKey.trim()) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateGeminiApiKey(newKey.trim());
      setStatus(updated);
      setNewKey("");
      setEditing(false);
      setMessage({ ok: true, text: "Chave Gemini salva com sucesso." });
    } catch {
      setMessage({ ok: false, text: "Não foi possível salvar a chave Gemini." });
    } finally {
      setSaving(false);
    }
  }

  const showForm = status?.configured !== true || editing;

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "52px 24px" }}>
      <Link href="/" style={{ fontSize: 13, color: "#9696a0" }}>← Projetos</Link>
      <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116", marginTop: 28, marginBottom: 6 }}>
        Configurações
      </h1>
      <p style={{ color: "#9696a0", marginBottom: 32, fontSize: 14 }}>
        Configurações compartilhadas por toda a aplicação.
      </p>

      <section style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 12, padding: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 750, color: "#111116", margin: 0 }}>Gemini</h2>
        <p style={{ marginTop: 6, color: "#6a6a7a", fontSize: 14 }}>
          Chave utilizada pelos recursos de IA de toda a aplicação.
        </p>

        {loading ? (
          <p style={{ marginTop: 24, color: "#9696a0", fontSize: 14 }}>Carregando...</p>
        ) : (
          <div style={{ marginTop: 24 }}>
            <p style={{ color: status?.configured ? "#16a34a" : "#dc2626", fontSize: 14, fontWeight: 700, margin: 0 }}>
              {status?.configured ? "Chave configurada" : "Chave não configurada"}
            </p>
            {status?.configured && (
              <div style={{ marginTop: 8 }}>
                <code style={{ fontSize: 14, color: "#111116" }}>{status.key_hint}</code>
                {status.updated_at && (
                  <p style={{ marginTop: 6, color: "#9696a0", fontSize: 12 }}>
                    Atualizada em {new Date(status.updated_at).toLocaleString("pt-BR")}
                  </p>
                )}
              </div>
            )}

            {showForm ? (
              <form onSubmit={handleSubmit} style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                <label htmlFor="gemini-new-key" style={labelStyle}>Nova chave Gemini</label>
                <div style={{ display: "flex", gap: 10 }}>
                  <input
                    id="gemini-new-key"
                    type="password"
                    autoComplete="new-password"
                    value={newKey}
                    onChange={(event) => setNewKey(event.target.value)}
                    placeholder="AIza..."
                    style={{ ...inputStyle, flex: 1 }}
                    required
                  />
                  <button type="submit" disabled={saving || !newKey.trim()} style={btnPrimary}>
                    {saving ? "Salvando..." : "Salvar chave"}
                  </button>
                  {status?.configured && (
                    <button type="button" disabled={saving} onClick={() => { setEditing(false); setNewKey(""); }} style={btnSecondary}>
                      Cancelar
                    </button>
                  )}
                </div>
              </form>
            ) : (
              <button type="button" onClick={() => { setEditing(true); setMessage(null); }} style={{ ...btnSecondary, marginTop: 18 }}>
                Alterar chave
              </button>
            )}

            {message && (
              <p style={{ marginTop: 14, fontSize: 13, color: message.ok ? "#16a34a" : "#dc2626" }}>
                {message.text}
              </p>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  color: "#6a6a7a",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  minWidth: 0,
  padding: "11px 14px",
  background: "#fff",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  fontSize: 14,
  color: "#111116",
};

const btnPrimary: React.CSSProperties = {
  background: "#4ade80",
  color: "#0a0a0a",
  border: "none",
  borderRadius: 8,
  padding: "11px 16px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  background: "#fff",
  color: "#6a6a7a",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "10px 14px",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};
