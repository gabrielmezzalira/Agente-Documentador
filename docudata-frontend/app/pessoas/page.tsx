"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Card, Chip, EmptyState, ErrorNotice, PageHeader, Select } from "../components/ds";
import { ds, labelStyle, type Tone } from "../lib/ds";
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

const CARGO_TOM: Record<Cargo, Tone> = {
  owner: "violet",
  lider: "green",
  gerente: "amber",
  operacional: "neutral",
};

const COLUNAS = "minmax(0,1.4fr) minmax(0,1.6fr) 180px";

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

  if (auth && !podeVer) return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;

  return (
    <>
      <PageHeader
        title="Pessoas"
        subtitle={`Quem tem acesso ao sistema e o que cada um enxerga.${podeEditar ? " Como Owner, você pode mudar o cargo de qualquer pessoa." : " Só o Owner altera cargos."}`}
      />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}

      <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14 }}>
        {CARGOS.map((c) => (
          <Card key={c.valor}>
            <div style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
              <Chip tone={CARGO_TOM[c.valor]}>{c.label}</Chip>
              <span style={{ fontSize: 13, lineHeight: 1.45, color: ds.muted }}>{c.descricao}</span>
            </div>
          </Card>
        ))}
      </div>

      {!pessoas && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
      {pessoas && pessoas.length === 0 && <EmptyState>Nenhuma pessoa cadastrada ainda.</EmptyState>}

      {pessoas && pessoas.length > 0 && (
        <Card style={{ overflowX: "auto" }}>
          <div role="table" style={{ display: "flex", flexDirection: "column", minWidth: 640 }}>
            <div role="row" style={{ display: "grid", gridTemplateColumns: COLUNAS, gap: 12, padding: "10px 16px", borderBottom: `1px solid ${ds.border}` }}>
              <span role="columnheader" style={labelStyle}>Pessoa</span>
              <span role="columnheader" style={labelStyle}>Projetos</span>
              <span role="columnheader" style={labelStyle}>Cargo</span>
            </div>
            {pessoas.map((p, i) => (
              <div key={p.id} role="row" style={{ display: "grid", gridTemplateColumns: COLUNAS, gap: 12, alignItems: "center", padding: "14px 16px", borderTop: i > 0 ? `1px solid ${ds.border}` : "none" }}>
                <span role="cell" style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: ds.white }}>{p.nome}</span>
                  <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted, overflow: "hidden", textOverflow: "ellipsis" }}>{p.email}</span>
                </span>
                <span role="cell" style={{ fontSize: 13, color: ds.text2, lineHeight: 1.45 }}>
                  {p.projetos.length > 0 ? p.projetos.join(", ") : <span style={{ color: ds.dim }}>—</span>}
                </span>
                <span role="cell">
                  {podeEditar ? (
                    <Select
                      aria-label={`Cargo de ${p.nome}`}
                      value={p.cargo}
                      disabled={salvandoId === p.id}
                      onChange={(e) => handleCargo(p, e.target.value as Cargo)}
                      style={{ height: 36, fontSize: 13, opacity: salvandoId === p.id ? 0.5 : 1 }}
                    >
                      {CARGOS.map((c) => <option key={c.valor} value={c.valor}>{c.label}</option>)}
                    </Select>
                  ) : (
                    <Chip tone={CARGO_TOM[p.cargo]}>{CARGOS.find((c) => c.valor === p.cargo)?.label ?? p.cargo}</Chip>
                  )}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {podeEditar && (
        <p style={{ margin: 0, fontSize: 12.5, color: ds.muted, lineHeight: 1.6, maxWidth: 760 }}>
          Você não consegue mudar o próprio cargo: rebaixar a si mesmo tiraria seu acesso a
          esta tela e não teria como ser desfeito por aqui. Se precisar sair, promova outra
          pessoa a Owner antes. Toda troca de cargo fica registrada.
        </p>
      )}
    </>
  );
}
