"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listOperacionaisSemConta, signupClaim, signupNovo, type OperacionalSemConta } from "../lib/api";

export default function CadastroPage() {
  const router = useRouter();
  const [modo, setModo] = useState<"lista" | "claim" | "novo">("lista");
  const [operacionais, setOperacionais] = useState<OperacionalSemConta[]>([]);
  const [selecionado, setSelecionado] = useState<OperacionalSemConta | null>(null);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listOperacionaisSemConta().then(setOperacionais).catch(() => setOperacionais([]));
  }, []);

  const inputSt: React.CSSProperties = { padding: "10px 12px", border: "1px solid #e4e4ea", borderRadius: 8, fontSize: 14 };
  const btnPrimary: React.CSSProperties = { padding: "10px 12px", borderRadius: 8, background: "#111116", color: "#fff", border: "none", fontWeight: 600 };
  const btnGhost: React.CSSProperties = { fontSize: 13, background: "none", border: "none", color: "#9696a0", cursor: "pointer" };

  async function handleClaim(e: React.FormEvent) {
    e.preventDefault();
    if (!selecionado) return;
    setLoading(true);
    setErr("");
    try {
      await signupClaim(selecionado.operacional_id, email, senha);
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
      await signupNovo(nome, email, senha);
      router.push("/");
      router.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: "60px auto", padding: 24 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Criar conta — DocuData</h1>

      {modo === "lista" && (
        <div>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 12 }}>Você já é operacional em algum projeto?</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 240, overflowY: "auto" }}>
            {operacionais.map((op) => (
              <button
                key={op.operacional_id}
                onClick={() => { setSelecionado(op); setModo("claim"); }}
                style={{ textAlign: "left", padding: "8px 12px", border: "1px solid #e4e4ea", borderRadius: 8, background: "#fff", cursor: "pointer" }}
              >
                {op.nome} <span style={{ color: "#9696a0", fontSize: 12 }}>— {op.project_name}</span>
              </button>
            ))}
          </div>
          <button onClick={() => setModo("novo")} style={{ ...btnGhost, marginTop: 16 }}>
            Não me encontrei na lista — sou novo
          </button>
        </div>
      )}

      {modo === "claim" && selecionado && (
        <form onSubmit={handleClaim} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <p style={{ fontSize: 13 }}>Criando conta para <strong>{selecionado.nome}</strong> ({selecionado.project_name})</p>
          <input type="email" placeholder="Seu email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputSt} />
          <input type="password" placeholder="Crie uma senha" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={6} style={inputSt} />
          {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}
          <button type="submit" disabled={loading} style={btnPrimary}>{loading ? "Criando..." : "Criar conta"}</button>
          <button type="button" onClick={() => setModo("lista")} style={btnGhost}>Voltar</button>
        </form>
      )}

      {modo === "novo" && (
        <form onSubmit={handleNovo} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input placeholder="Seu nome" value={nome} onChange={(e) => setNome(e.target.value)} required style={inputSt} />
          <input type="email" placeholder="Seu email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputSt} />
          <input type="password" placeholder="Crie uma senha" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={6} style={inputSt} />
          {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}
          <button type="submit" disabled={loading} style={btnPrimary}>{loading ? "Criando..." : "Criar conta"}</button>
          <button type="button" onClick={() => setModo("lista")} style={btnGhost}>Voltar</button>
        </form>
      )}
    </div>
  );
}
