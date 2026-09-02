"use client";

import { useState } from "react";

export interface TutorialStep {
  title: string;
  body: string;
}

interface Props {
  heading: string;
  steps: TutorialStep[];
  defaultOpen?: boolean;
}

export default function TutorialBanner({ heading, steps, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div style={{
      marginBottom: 18,
      border: "1px solid #e2e8f0",
      borderRadius: 10,
      overflow: "hidden",
      background: "#f8fafc",
    }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 16px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 18, height: 18, borderRadius: "50%",
          background: "#e0e7ff", color: "#4338ca",
          fontSize: 11, fontWeight: 800, flexShrink: 0,
        }}>?</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#475569", flex: 1 }}>
          Como usar: {heading}
        </span>
        <span style={{ fontSize: 11, color: "#94a3b8", whiteSpace: "nowrap" }}>
          {open ? "▲ fechar" : "▼ ver tutorial"}
        </span>
      </button>

      {open && (
        <div style={{ borderTop: "1px solid #e2e8f0", padding: "12px 18px 16px" }}>
          <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 10 }}>
            {steps.map((step, i) => (
              <li key={i} style={{ fontSize: 13, color: "#374151", lineHeight: 1.65 }}>
                <span style={{ fontWeight: 700, color: "#0f172a" }}>{step.title}</span>
                {" — "}
                <span>{step.body}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
