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

  const inputSt: React.CSSProperties = { padding: "10px 12px", border: "1px solid #e4e4ea", borderRadius: 8, fontSize: 14 };

  return (
    <div style={{ maxWidth: 360, margin: "80px auto", padding: 24 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Entrar — DocuData</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputSt} />
        <input type="password" placeholder="Senha" value={senha} onChange={(e) => setSenha(e.target.value)} required style={inputSt} />
        {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}
        <button type="submit" disabled={loading} style={{ padding: "10px 12px", borderRadius: 8, background: "#111116", color: "#fff", border: "none", fontWeight: 600 }}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: 13 }}>
        Ainda não tem conta? <a href="/cadastro">Cadastre-se</a>
      </p>
    </div>
  );
}
