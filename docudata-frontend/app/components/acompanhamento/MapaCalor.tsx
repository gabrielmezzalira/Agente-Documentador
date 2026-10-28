"use client";

import type { CSSProperties } from "react";
import { ds } from "../../lib/ds";
import type { AcompMapaProjeto, AcompMapaSprint } from "../../lib/api";

const COLUNAS = [-5, -4, -3, -2, -1, 0];
const SEM_DADO = ds.chartGrey;

function fmt(x: number): string {
  return x.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function corDoSpi(spi: number | null): string {
  if (spi == null) return SEM_DADO;
  if (spi >= 0.9) return ds.green;
  if (spi >= 0.7) return ds.amber;
  return ds.red;
}

function rotuloDaCelula(nome: string, c: number, s: AcompMapaSprint | undefined): string {
  const col = c === 0 ? "atual" : `−${Math.abs(c)}`;
  if (!s || s.numero == null) return `${nome} · ${col} · sem dado`;
  const spi = s.spi != null ? `SPI ${fmt(s.spi)}` : "SPI sem dado";
  const meta = s.meta_total > 0 ? `meta ${s.meta_entregues}/${s.meta_total}` : "sem meta";
  return `${nome} · Sprint ${s.numero} (${col}) · ${spi} · ${meta}`;
}

const grade: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(96px, 1.6fr) repeat(6, minmax(24px, 1fr))",
  gap: 4,
  alignItems: "center",
};

const cab: CSSProperties = { fontSize: 11, color: ds.muted, textAlign: "center", fontFamily: ds.fontMono };

/** Mapa de calor: uma linha por projeto, uma coluna por sprint (−5 … atual); a cor é o SPI da sprint. */
export default function MapaCalor({ mapa, onAbrir }: { mapa: AcompMapaProjeto[]; onAbrir: (projetoId: string) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ overflowX: "auto" }}>
        <div style={{ ...grade, minWidth: 320 }}>
          <span />
          {COLUNAS.map((c) => <span key={c} style={cab}>{c === 0 ? "atual" : `−${Math.abs(c)}`}</span>)}
          {mapa.map((p) => {
            const nome = p.nome ?? "Projeto";
            const porRel = new Map(p.sprints.map((s) => [s.rel, s]));
            return (
              <div key={p.projeto_id} style={{ display: "contents" }}>
                <button
                  type="button"
                  onClick={() => onAbrir(p.projeto_id)}
                  title={nome}
                  style={{ background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left", fontFamily: "inherit", fontSize: 13, color: ds.text2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                >
                  {nome}
                </button>
                {COLUNAS.map((c) => {
                  const s = porRel.get(c);
                  const rotulo = rotuloDaCelula(nome, c, s);
                  return (
                    <span
                      key={c}
                      role="img"
                      aria-label={rotulo}
                      title={rotulo}
                      style={{ height: 22, borderRadius: 4, background: corDoSpi(s?.spi ?? null), opacity: s?.spi == null ? 0.45 : 1, display: "block" }}
                    />
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
      <ul aria-label="Legenda do mapa de calor" style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: ds.muted }}>
        {[["≥ 0,9", ds.green], ["0,7–0,9", ds.amber], ["< 0,7", ds.red], ["sem dado", SEM_DADO]].map(([t, c]) => (
          <li key={t} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 3, background: c, display: "inline-block" }} />
            {t}
          </li>
        ))}
      </ul>
    </div>
  );
}
