"use client";

import { useEffect, useState } from "react";
import { getTechnologies, type TechTimeline } from "../lib/api";

interface Props {
  projectId: string;
}

const sectionStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "20px 22px",
  marginBottom: 14,
};

const sectionTitle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  marginBottom: 16,
  color: "#9696a0",
};

const chipStyle = (active: boolean): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  padding: "5px 12px",
  borderRadius: 999,
  fontSize: 13,
  fontWeight: 600,
  background: active ? "#dcfce7" : "#f7f7fa",
  color: active ? "#16a34a" : "#9696a0",
  border: active ? "1px solid #86efac" : "1px solid #e4e4ea",
});

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 12px",
  borderBottom: "1px solid #e4e4ea",
  color: "#6a6a7a",
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  background: "#f7f7fa",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid #f0f0f4",
};

export default function TechnologiesTab({ projectId }: Props) {
  const [data, setData] = useState<TechTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getTechnologies(projectId)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <section style={sectionStyle}>
        <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>Carregando tecnologias…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section style={sectionStyle}>
        <p style={{ color: "#dc2626", fontSize: 14, margin: 0 }}>{error}</p>
      </section>
    );
  }

  if (!data || data.timeline.length === 0) {
    return (
      <section style={sectionStyle}>
        <h2 style={sectionTitle}>Tecnologias do projeto</h2>
        <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
          Nenhuma tecnologia identificada ainda. Tecnologias são extraídas automaticamente das
          ingestões — assim que o gerente subir conteúdo que mencione stack, ferramentas ou
          bibliotecas, elas aparecem aqui.
        </p>
      </section>
    );
  }

  const activeKeys = new Set(data.em_uso_atual.map((t) => t.toLowerCase()));

  return (
    <>
      <section style={sectionStyle}>
        <h2 style={sectionTitle}>
          Em uso atualmente
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "#16a34a",
              marginLeft: 8,
              background: "#dcfce7",
              borderRadius: 4,
              padding: "2px 7px",
            }}
          >
            {data.em_uso_atual.length}
          </span>
        </h2>
        {data.em_uso_atual.length === 0 ? (
          <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
            Nenhuma tecnologia ativa na sprint mais recente.
          </p>
        ) : (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {data.em_uso_atual.map((t) => (
              <span key={t} style={chipStyle(true)}>
                {t}
              </span>
            ))}
          </div>
        )}
      </section>

      <section style={sectionStyle}>
        <h2 style={sectionTitle}>Histórico — quando cada tecnologia entrou e saiu</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Tecnologia</th>
                <th style={thStyle}>Introduzida em</th>
                <th style={thStyle}>Abandonada em</th>
                <th style={thStyle}>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.timeline.map((entry) => {
                const isActive = activeKeys.has(entry.tecnologia.toLowerCase());
                return (
                  <tr key={entry.tecnologia}>
                    <td style={{ ...tdStyle, fontWeight: 600, color: "#111116" }}>
                      {entry.tecnologia}
                    </td>
                    <td style={tdStyle}>Sprint {entry.introduzida_em}</td>
                    <td style={tdStyle}>
                      {entry.abandonada_em == null ? (
                        <span style={{ color: "#b8b8c0" }}>—</span>
                      ) : (
                        <span style={{ color: "#b45309" }}>Sprint {entry.abandonada_em}</span>
                      )}
                    </td>
                    <td style={tdStyle}>
                      {isActive ? (
                        <span style={chipStyle(true)}>Em uso</span>
                      ) : (
                        <span style={chipStyle(false)}>Abandonada</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
