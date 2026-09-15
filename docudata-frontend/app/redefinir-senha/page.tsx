"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { resetPassword } from "../lib/api";

function RedefinirSenhaForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [senha, setSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [sucesso, setSucesso] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (senha !== confirmar) {
      setErr("As senhas não coincidem");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, senha);
      setSucesso(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao redefinir senha");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116" }}>
            Redefinir senha
          </h1>
        </div>

        <div style={cardStyle}>
          {!token ? (
            <p style={{ fontSize: 14, color: "#dc2626" }}>
              Link inválido — falta o token de redefinição. Solicite um novo link em{" "}
              <a href="/esqueci-senha" style={{ color: "#16a34a", fontWeight: 700 }}>Esqueci minha senha</a>.
            </p>
          ) : sucesso ? (
            <p style={{ fontSize: 14, color: "#374151" }}>Senha redefinida com sucesso. Redirecionando para o login...</p>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={labelStyle}>Nova senha</label>
                <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={6} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Confirmar nova senha</label>
                <input type="password" value={confirmar} onChange={(e) => setConfirmar(e.target.value)} required minLength={6} style={inputStyle} />
              </div>
              {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}
              <button type="submit" disabled={loading} style={btnPrimary}>
                {loading ? "Salvando..." : "Definir nova senha"}
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

export default function RedefinirSenhaPage() {
  return (
    <Suspense fallback={null}>
      <RedefinirSenhaForm />
    </Suspense>
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
