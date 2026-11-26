"use client";

import { useState } from "react";
import { ds } from "../lib/ds";

const MODOS = {
  ATRIBUICAO: {
    nome: "Atribuição",
    resumo: "o gerente escolhe quem faz cada task, e toda task nasce com responsável.",
    outro: "Pull",
    outroResumo: "as tasks entram numa fila sem dono e cada pessoa puxa a próxima quando termina a anterior, uma por vez, e a avaliação é relativa ao squad.",
  },
  PULL: {
    nome: "Pull",
    resumo: "as tasks entram numa fila sem dono e cada pessoa puxa a sua, uma em andamento por vez.",
    outro: "Atribuição",
    outroResumo: "o gerente escolhe quem faz cada task, toda task nasce com responsável, e a avaliação usa os pontos atribuídos.",
  },
} as const;

/** Faixa no topo da aba Tasks: diz em que modo o projeto está e que existe o outro, para ninguém ser pego de surpresa. */
export default function ModoTrabalhoAviso({ modo }: { modo: "ATRIBUICAO" | "PULL" }) {
  const [aberto, setAberto] = useState(false);
  const m = MODOS[modo];
  return (
    <section
      aria-label="Modo de trabalho do projeto"
      style={{ border: `1px solid ${ds.border}`, borderRadius: 12, background: "rgba(255,255,255,0.025)", padding: "12px 16px" }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13.5, color: ds.text2, lineHeight: 1.55, flex: "1 1 320px" }}>
          <strong style={{ color: ds.white }}>Modo {m.nome}:</strong> {m.resumo}
        </span>
        <button
          type="button" aria-expanded={aberto} onClick={() => setAberto((v) => !v)}
          style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, color: ds.green, textDecoration: "underline", textUnderlineOffset: 2, whiteSpace: "nowrap" }}
        >
          {aberto ? "Ocultar" : `Existe também o modo ${m.outro}`}
        </button>
      </div>
      {aberto && (
        <p style={{ margin: "10px 0 0", fontSize: 13, lineHeight: 1.6, color: ds.muted, maxWidth: "75ch" }}>
          <strong style={{ color: ds.text2 }}>Modo {m.outro}:</strong> {m.outroResumo}{" "}
          Quem troca o modo é o gerente ou o líder, em Configurações do projeto, na seção Modo de trabalho. A troca migra as tasks que já existem, e o sistema mostra o impacto antes de confirmar.
        </p>
      )}
    </section>
  );
}
