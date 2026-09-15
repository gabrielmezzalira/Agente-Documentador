"use client";

import { useState } from "react";
import { forgotPassword } from "../lib/api";

export default function EsqueciSenhaPage() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      await forgotPassword(email);
      setEnviado(true);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao solicitar redefinição");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116" }}>
            Esqueci minha senha
          </h1>
        </div>

        <div style={cardStyle}>
          {enviado ? (
            <p style={{ fontSize: 14, color: "#374151", lineHeight: 1.6 }}>
              Se o e-mail existir, você vai receber um link de redefinição em instantes. O link expira em 30 minutos.
            </p>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={labelStyle}>Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} placeholder="voce@citi.org.br" />
              </div>
              {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}
              <button type="submit" disabled={loading} style={btnPrimary}>
                {loading ? "Enviando..." : "Enviar link de redefinição"}
              </button>
            </form>
          )}
        </div>

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <a href="/login" style={{ fontSize: 13, fontWeight: 700, color: "#16a34a" }}>
            Voltar para o login
          </a>
        </div>
      </div>
    </main>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "28px 26px",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 700,
  marginBottom: 6,
  color: "#6a6a7a",
  letterSpacing: "0.04em",
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

const btnPrimary: React.CSSProperties = {
  background: "#4ade80",
  color: "#0a0a0a",
  border: "none",
  borderRadius: 8,
  padding: "11px 18px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
  marginTop: 4,
};
