"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../components/AuthGuard";
import {
  listPessoas,
  alterarCargoPessoa,
  type Cargo,
  type PessoaResponse,
} from "../lib/api";

const CARGOS: { valor: Cargo; label: string; descricao: string }[] = [
  { valor: "owner", label: "Owner", descricao: "Tudo, mais a gestão dos cargos" },
  { valor: "lider", label: "Líder", descricao: "Tudo, incluindo ranking de performance" },
  { valor: "gerente", label: "Gerente", descricao: "Todos os projetos, sem o ranking" },
  { valor: "operacional", label: "Operacional", descricao: "Só os projetos em que está" },
];

const CARGO_COR: Record<Cargo, { bg: string; fg: string }> = {
  owner: { bg: "rgba(177,151,252,0.10)", fg: "#b197fc" },
  lider: { bg: "rgba(62,224,111,0.12)", fg: "#3ee06f" },
  gerente: { bg: "#b197fc", fg: "#b197fc" },
  operacional: { bg: "rgba(62,224,111,0.055)", fg: "#c3cbc6" },
};

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 14px",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
  fontSize: 11,
  fontWeight: 700,
  color: "#8a948e",
  textTransform: "uppercase",
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  padding: "12px 14px",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
  color: "#c3cbc6",
  fontSize: 13,
};

export default function PessoasPage() {
  const auth = useAuth();
  const [pessoas, setPessoas] = useState<PessoaResponse[] | null>(null);
  const [erro, setErro] = useState("");
  const [salvandoId, setSalvandoId] = useState<string | null>(null);

  const podeVer = auth ? auth.cargo === "owner" || auth.cargo === "lider" : false;
  const podeEditar = auth?.cargo === "owner";

  useEffect(() => {
    if (!podeVer) return;
    listPessoas()
      .then(setPessoas)
      .catch((e: Error) => setErro(e.message));
  }, [podeVer]);

  async function handleCargo(pessoa: PessoaResponse, cargo: Cargo) {
    if (cargo === pessoa.cargo) return;
    const label = CARGOS.find((c) => c.valor === cargo)?.label ?? cargo;
    if (!confirm(`Mudar ${pessoa.nome} para ${label}?\n\nIsso altera o que essa pessoa enxerga no sistema imediatamente.`)) return;

    setSalvandoId(pessoa.id);
    setErro("");
    try {
      const atualizada = await alterarCargoPessoa(pessoa.id, cargo);
      setPessoas((prev) =>
        (prev ?? []).map((p) => (p.id === atualizada.id ? { ...p, cargo: atualizada.cargo } : p)),
      );
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao alterar o cargo");
    } finally {
      setSalvandoId(null);
    }
  }

  if (auth && !podeVer) {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <Link href="/" style={{ fontSize: 13, color: "#8a948e" }}>← Projetos</Link>
        <p style={{ color: "#ff6b6b", marginTop: 20 }}>Acesso restrito a Líder e Owner.</p>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "48px 24px 96px" }}>
      <Link href="/" style={{ fontSize: 13, color: "#8a948e" }}>← Projetos</Link>

      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#f2f5f3", margin: "20px 0 6px" }}>
        Pessoas
      </h1>
      <p style={{ color: "#8a948e", fontSize: 14, marginBottom: 28 }}>
        Quem tem acesso ao sistema e o que cada um enxerga.
        {podeEditar
          ? " Como Owner, você pode mudar o cargo de qualquer pessoa."
          : " Só o Owner altera cargos."}
      </p>

      {erro && (
        <p style={{ color: "#ff6b6b", fontSize: 13, marginBottom: 16 }}>{erro}</p>
      )}

      <div style={{
        background: "rgba(62,224,111,0.055)", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 12,
        padding: "16px 20px", marginBottom: 24,
      }}>
        {CARGOS.map((c) => (
          <div key={c.valor} style={{ display: "flex", gap: 10, alignItems: "baseline", marginBottom: 6 }}>
            <span style={{
              background: CARGO_COR[c.valor].bg, color: CARGO_COR[c.valor].fg,
              borderRadius: 999, padding: "2px 10px", fontSize: 11, fontWeight: 700,
              minWidth: 96, textAlign: "center",
            }}>
              {c.label}
            </span>
            <span style={{ fontSize: 12, color: "#8a948e" }}>{c.descricao}</span>
          </div>
        ))}
      </div>

      {!pessoas && !erro && <p style={{ color: "#8a948e" }}>Carregando...</p>}

      {pessoas && pessoas.length === 0 && (
        <p style={{ color: "#8a948e" }}>Nenhuma pessoa cadastrada ainda.</p>
      )}

      {pessoas && pessoas.length > 0 && (
        <div style={{
          background: "#0d1711", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 12,
          overflowX: "auto",
        }}>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={th}>Pessoa</th>
                <th style={th}>Projetos</th>
                <th style={th}>Cargo</th>
              </tr>
            </thead>
            <tbody>
              {pessoas.map((p) => (
                <tr key={p.id}>
                  <td style={td}>
                    <div style={{ fontWeight: 700, color: "#f2f5f3" }}>{p.nome}</div>
                    <div style={{ fontSize: 12, color: "#8a948e" }}>{p.email}</div>
                  </td>
                  <td style={{ ...td, fontSize: 12, color: "#8a948e" }}>
                    {p.projetos.length > 0 ? p.projetos.join(", ") : "—"}
                  </td>
                  <td style={td}>
                    {podeEditar ? (
                      <select
                        value={p.cargo}
                        disabled={salvandoId === p.id}
                        onChange={(e) => handleCargo(p, e.target.value as Cargo)}
                        style={{
                          padding: "6px 10px", borderRadius: 8, border: "1px solid rgba(62,224,111,0.2)",
                          fontSize: 13, color: "#f2f5f3", background: "#0d1711",
                          opacity: salvandoId === p.id ? 0.5 : 1,
                        }}
                      >
                        {CARGOS.map((c) => (
                          <option key={c.valor} value={c.valor}>{c.label}</option>
                        ))}
                      </select>
                    ) : (
                      <span style={{
                        background: CARGO_COR[p.cargo].bg, color: CARGO_COR[p.cargo].fg,
                        borderRadius: 999, padding: "3px 12px", fontSize: 12, fontWeight: 700,
                      }}>
                        {CARGOS.find((c) => c.valor === p.cargo)?.label ?? p.cargo}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {podeEditar && (
        <p style={{ fontSize: 12, color: "#8a948e", marginTop: 16, lineHeight: 1.6 }}>
          Você não consegue mudar o próprio cargo: rebaixar a si mesmo tiraria seu acesso a
          esta tela e não teria como ser desfeito por aqui. Se precisar sair, promova outra
          pessoa a Owner antes. Toda troca de cargo fica registrada.
        </p>
      )}
    </main>
  );
}
