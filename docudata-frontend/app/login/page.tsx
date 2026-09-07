"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      await login(email, senha);
      router.push("/");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#16a34a" }}>
            citi · subárea de dados
          </span>
          <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116", marginTop: 10 }}>
            Agente Documentador
          </h1>
        </div>

        <div style={cardStyle}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#111116", marginBottom: 18 }}>Entrar</h2>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={labelStyle}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} placeholder="voce@citi.org.br" />
            </div>
            <div>
              <label style={labelStyle}>Senha</label>
              <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required style={inputStyle} />
            </div>
            {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}
            <button type="submit" disabled={loading} style={btnPrimary}>
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>
        </div>

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <span style={{ fontSize: 13, color: "#9696a0" }}>Ainda não tem conta? </span>
          <a href="/cadastro" style={{ fontSize: 13, fontWeight: 700, color: "#16a34a" }}>
            Cadastre-se
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
