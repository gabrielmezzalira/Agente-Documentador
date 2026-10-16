"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../lib/api";
import AuthBrand from "../components/shell/AuthBrand";

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
        <AuthBrand title="Entrar" />

        <div style={cardStyle}>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={labelStyle}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} placeholder="voce@citi.org.br" />
            </div>
            <div>
              <label style={labelStyle}>Senha</label>
              <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required style={inputStyle} />
              <div style={{ textAlign: "right", marginTop: 6 }}>
                <a href="/esqueci-senha" style={{ fontSize: 12, color: "#8a948e" }}>Esqueci minha senha</a>
              </div>
            </div>
            {err && <p style={{ color: "#ff6b6b", fontSize: 13 }}>{err}</p>}
            <button type="submit" disabled={loading} style={btnPrimary}>
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>
        </div>

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <span style={{ fontSize: 13, color: "#8a948e" }}>Ainda não tem conta? </span>
          <a href="/cadastro" style={{ fontSize: 13, fontWeight: 700, color: "#3ee06f" }}>
            Cadastre-se
          </a>
        </div>
      </div>
    </main>
  );
}

const cardStyle: React.CSSProperties = {
  background: "linear-gradient(180deg, #0e1913 0%, #0a120d 100%)",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 16,
  boxShadow: "inset 0 1px 0 rgba(62,224,111,0.12), 0 12px 32px rgba(0,0,0,0.45)",
  padding: "28px 26px",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontFamily: "'Geist Mono', ui-monospace, monospace",
  fontSize: 11,
  fontWeight: 500,
  marginBottom: 8,
  color: "#8a948e",
  letterSpacing: "0.16em",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  height: 42,
  padding: "0 14px",
  background: "rgba(62,224,111,0.055)",
  border: "1px solid rgba(62,224,111,0.17)",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  color: "#f2f5f3",
  fontFamily: "inherit",
};

const btnPrimary: React.CSSProperties = {
  background: "#3ee06f",
  color: "#04120a",
  border: "1px solid #3ee06f",
  borderRadius: 10,
  padding: "11px 18px",
  fontSize: 14,
  fontWeight: 600,
  boxShadow: "0 0 24px rgba(62,224,111,0.25)",
  fontFamily: "inherit",
  cursor: "pointer",
  marginTop: 4,
};
