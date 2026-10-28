"use client";

import { ds } from "../../lib/ds";
import type { AcompDispersao, AcompStatus } from "../../lib/api";

const W = 460;
const H = 300;
const M = { l: 44, r: 14, t: 12, b: 44 };
const PW = W - M.l - M.r;
const PH = H - M.t - M.b;

const COR: Record<AcompStatus, string> = { critico: ds.red, atencao: ds.amber, sem_dados: ds.chartGrey, saudavel: ds.green };

const STATUS_PALAVRA: Record<AcompStatus, string> = { critico: "crítico", atencao: "atenção", sem_dados: "faltam dados", saudavel: "saudável" };
const pct = (v: number) => Math.round(v);
const clamp = (v: number) => Math.max(0, Math.min(100, v));
const x = (v: number) => M.l + (clamp(v) / 100) * PW;
const y = (v: number) => M.t + PH - (clamp(v) / 100) * PH;

/** Dispersão: prazo consumido (x) × funcionalidades aprovadas (y); bolha = tasks travadas. Abaixo da diagonal = atrasado. */
export default function DispersaoPrazo({ dispersao, onAbrir }: { dispersao: AcompDispersao; onAbrir: (projetoId: string) => void }) {
  const { pontos, sem_datas } = dispersao;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Dispersão do prazo consumido contra as funcionalidades aprovadas" style={{ width: "100%", height: "auto", maxWidth: 560 }}>
        {[0, 25, 50, 75, 100].map((t) => (
          <g key={t}>
            <line x1={M.l} x2={M.l + PW} y1={y(t)} y2={y(t)} stroke={ds.border} />
            <text x={M.l - 6} y={y(t) + 4} fontSize={10} fill={ds.muted} textAnchor="end">{t}%</text>
            <text x={x(t)} y={M.t + PH + 14} fontSize={10} fill={ds.muted} textAnchor="middle">{t}%</text>
          </g>
        ))}
        <line x1={M.l} x2={M.l} y1={M.t} y2={M.t + PH} stroke={ds.borderStrong} />
        <line x1={M.l} x2={M.l + PW} y1={M.t + PH} y2={M.t + PH} stroke={ds.borderStrong} />
        <line x1={x(0)} y1={y(0)} x2={x(100)} y2={y(100)} stroke={ds.dim} strokeDasharray="5 4" />
        <text x={M.l + PW / 2} y={H - 8} fontSize={11} fill={ds.text2} textAnchor="middle">% do prazo consumido</text>
        <text transform={`translate(12 ${M.t + PH / 2}) rotate(-90)`} fontSize={11} fill={ds.text2} textAnchor="middle">% das funcionalidades aprovadas</text>
        {pontos.map((p) => {
          const nome = p.nome ?? "Projeto";
          const rotulo = `${nome} · ${STATUS_PALAVRA[p.status]} · ${pct(p.pct_prazo)}% do prazo · ${pct(p.pct_escopo)}% do escopo · ${p.travadas} ${p.travadas === 1 ? "travada" : "travadas"}`;
          return (
            <g
              key={p.projeto_id}
              role="button"
              tabIndex={0}
              aria-label={rotulo}
              style={{ cursor: "pointer" }}
              onClick={() => onAbrir(p.projeto_id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onAbrir(p.projeto_id); } }}
            >
              <title>{rotulo}</title>
              <circle cx={x(p.pct_prazo)} cy={y(p.pct_escopo)} r={4 + 2 * Math.sqrt(p.travadas)} fill={COR[p.status] ?? ds.chartGrey} fillOpacity={0.75} stroke={COR[p.status] ?? ds.chartGrey} />
            </g>
          );
        })}
      </svg>
      <ul aria-label="Legenda da dispersão" style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: ds.muted }}>
        {([["crítico", "critico"], ["atenção", "atencao"], ["saudável", "saudavel"], ["sem dado", "sem_dados"]] as [string, AcompStatus][]).map(([t, s]) => (
          <li key={s} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: "50%", background: COR[s], display: "inline-block" }} />
            {t}
          </li>
        ))}
        <li>bolha maior = mais tasks travadas</li>
      </ul>
      {sem_datas > 0 && (
        <span style={{ fontSize: 12.5, color: ds.muted }}>
          {sem_datas} {sem_datas === 1 ? "projeto" : "projetos"} sem datas do contrato
        </span>
      )}
    </div>
  );
}
