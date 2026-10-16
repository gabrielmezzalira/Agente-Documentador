"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { resetPassword } from "../lib/api";
import AuthBrand from "../components/shell/AuthBrand";

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
        <AuthBrand title="Redefinir senha" />

        <div style={cardStyle}>
          {!token ? (
            <p style={{ fontSize: 14, color: "#ff6b6b" }}>
              Link inválido — falta o token de redefinição. Solicite um novo link em{" "}
              <a href="/esqueci-senha" style={{ color: "#3ee06f", fontWeight: 700 }}>Esqueci minha senha</a>.
            </p>
          ) : sucesso ? (
            <p style={{ fontSize: 14, color: "#c3cbc6" }}>Senha redefinida com sucesso. Redirecionando para o login...</p>
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
              {err && <p style={{ color: "#ff6b6b", fontSize: 13 }}>{err}</p>}
              <button type="submit" disabled={loading} style={btnPrimary}>
                {loading ? "Salvando..." : "Definir nova senha"}
              </button>
            </form>
          )}
        </div>

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <a href="/login" style={{ fontSize: 13, fontWeight: 700, color: "#3ee06f" }}>
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
