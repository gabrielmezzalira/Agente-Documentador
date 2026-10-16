"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listOperacionaisSemConta, signupClaim, signupNovo, type OperacionalSemConta } from "../lib/api";
import AuthBrand from "../components/shell/AuthBrand";

export default function CadastroPage() {
  const router = useRouter();
  const [modo, setModo] = useState<"lista" | "claim" | "novo">("lista");
  const [operacionais, setOperacionais] = useState<OperacionalSemConta[]>([]);
  const [selecionado, setSelecionado] = useState<OperacionalSemConta | null>(null);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [githubLogin, setGithubLogin] = useState("");
  const [githubEmail, setGithubEmail] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listOperacionaisSemConta().then(setOperacionais).catch(() => setOperacionais([]));
  }, []);

  async function handleClaim(e: React.FormEvent) {
    e.preventDefault();
    if (!selecionado) return;
    setLoading(true);
    setErr("");
    try {
      await signupClaim(selecionado.operacional_id, email, senha, githubLogin, githubEmail);
      router.push("/");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  }

  async function handleNovo(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr("");
    try {
      await signupNovo(nome, email, senha, githubLogin, githubEmail);
      router.push("/");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 420 }}>
        <AuthBrand title="Criar conta" />

        <div style={cardStyle}>
          {modo === "lista" && (
            <div>
              <p style={{ fontSize: 13, color: "#8a948e", marginBottom: 14 }}>Você já é operacional em algum projeto?</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 260, overflowY: "auto" }}>
                {operacionais.map((op) => (
                  <button
                    key={op.operacional_id}
                    onClick={() => { setSelecionado(op); setModo("claim"); }}
                    style={pickBtnStyle}
                  >
                    <span style={{ fontWeight: 600, color: "#f2f5f3" }}>{op.nome}</span>
                    <span style={{ color: "#8a948e", fontSize: 12, marginLeft: 8 }}>{op.project_name}</span>
                  </button>
                ))}
                {operacionais.length === 0 && (
                  <p style={{ fontSize: 13, color: "#5d6661" }}>Nenhum operacional pendente de conta no momento.</p>
                )}
              </div>
              <button onClick={() => setModo("novo")} style={destaqueBtnStyle}>
                Não me encontrei na lista, sou novo
              </button>
            </div>
          )}

          {modo === "claim" && selecionado && (
            <form onSubmit={handleClaim} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <p style={{ fontSize: 13, color: "#c3cbc6" }}>
                Criando conta para <strong>{selecionado.nome}</strong> no projeto <strong>{selecionado.project_name}</strong>
              </p>
              <div>
                <label style={labelStyle}>Seu email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Crie uma senha</label>
                <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={6} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Usuário do GitHub</label>
                <input value={githubLogin} onChange={(e) => setGithubLogin(e.target.value)} required style={inputStyle} placeholder="ex: joaosilva" />
              </div>
              <div>
                <label style={labelStyle}>Email do GitHub</label>
                <input type="email" value={githubEmail} onChange={(e) => setGithubEmail(e.target.value)} required style={inputStyle} placeholder="pode ser diferente do email de login" />
                <p style={{ marginTop: 6, fontSize: 12, color: "#5d6661", lineHeight: 1.5 }}>
                  Você pode criar a conta com qualquer email. O que conta para reconhecer seus
                  commits é o email que o Git usa no seu computador, informado aqui.
                </p>
              </div>
              {err && <p style={{ color: "#ff6b6b", fontSize: 13 }}>{err}</p>}
              <button type="submit" disabled={loading} style={btnPrimary}>{loading ? "Criando..." : "Criar conta"}</button>
              <button type="button" onClick={() => setModo("lista")} style={btnGhost}>Voltar</button>
            </form>
          )}

          {modo === "novo" && (
            <form onSubmit={handleNovo} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={labelStyle}>Seu nome</label>
                <input value={nome} onChange={(e) => setNome(e.target.value)} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Seu email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Crie uma senha</label>
                <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={6} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Usuário do GitHub</label>
                <input value={githubLogin} onChange={(e) => setGithubLogin(e.target.value)} required style={inputStyle} placeholder="ex: joaosilva" />
              </div>
              <div>
                <label style={labelStyle}>Email do GitHub</label>
                <input type="email" value={githubEmail} onChange={(e) => setGithubEmail(e.target.value)} required style={inputStyle} placeholder="pode ser diferente do email de login" />
                <p style={{ marginTop: 6, fontSize: 12, color: "#5d6661", lineHeight: 1.5 }}>
                  Você pode criar a conta com qualquer email. O que conta para reconhecer seus
                  commits é o email que o Git usa no seu computador, informado aqui.
                </p>
              </div>
              {err && <p style={{ color: "#ff6b6b", fontSize: 13 }}>{err}</p>}
              <button type="submit" disabled={loading} style={btnPrimary}>{loading ? "Criando..." : "Criar conta"}</button>
              <button type="button" onClick={() => setModo("lista")} style={btnGhost}>Voltar</button>
            </form>
          )}
        </div>

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <span style={{ fontSize: 13, color: "#8a948e" }}>Já tem conta? </span>
          <a href="/login" style={{ fontSize: 13, fontWeight: 700, color: "#3ee06f" }}>
            Entrar
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
};

const btnGhost: React.CSSProperties = {
  fontSize: 13,
  background: "none",
  border: "none",
  color: "#8a948e",
  cursor: "pointer",
  padding: 0,
};

const pickBtnStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 14px",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 8,
  background: "#0d1711",
  cursor: "pointer",
  fontSize: 13,
};

const destaqueBtnStyle: React.CSSProperties = {
  marginTop: 18,
  width: "100%",
  textAlign: "center",
  padding: "11px 14px",
  borderRadius: 8,
  border: "1px solid rgba(62,224,111,0.35)",
  background: "rgba(62,224,111,0.12)",
  color: "#3ee06f",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};
