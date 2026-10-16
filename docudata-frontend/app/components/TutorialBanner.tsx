"use client";

import { useState } from "react";

export interface TutorialStep {
  title: string;
  body: string;
}

interface Props {
  heading: string;
  steps: TutorialStep[];
}

export default function TutorialBanner({ heading, steps }: Props) {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(0);

  function handleOpen() {
    setCurrent(0);
    setOpen(true);
  }

  function handleClose() {
    setOpen(false);
  }

  const step = steps[current];
  const total = steps.length;

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={handleOpen}
        title="Como usar"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          background: "none",
          border: "1.5px solid rgba(62,224,111,0.2)",
          borderRadius: 20,
          padding: "5px 12px",
          fontSize: 12,
          fontWeight: 600,
          color: "#8a948e",
          cursor: "pointer",
          marginBottom: 18,
          transition: "border-color 0.15s, color 0.15s",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = "#4338ca";
          (e.currentTarget as HTMLButtonElement).style.color = "#4338ca";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = "#e2e8f0";
          (e.currentTarget as HTMLButtonElement).style.color = "#64748b";
        }}
      >
        <span style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 16, height: 16, borderRadius: "50%",
          background: "rgba(177,151,252,0.10)", color: "#b197fc",
          fontSize: 10, fontWeight: 800,
        }}>?</span>
        Como usar: {heading}
      </button>

      {/* Modal overlay */}
      {open && (
        <div
          onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
          style={{
            position: "fixed", inset: 0, zIndex: 1000,
            background: "rgba(0,0,0,0.35)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 24,
          }}
        >
          <div style={{
            background: "#0d1711",
            borderRadius: 16,
            width: "100%",
            maxWidth: 520,
            boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}>
            {/* Progress bar */}
            <div style={{ display: "flex", gap: 4, padding: "20px 24px 0" }}>
              {steps.map((_, i) => (
                <div
                  key={i}
                  onClick={() => setCurrent(i)}
                  style={{
                    flex: 1, height: 4, borderRadius: 99, cursor: "pointer",
                    background: i <= current ? "#3ee06f" : "rgba(255,255,255,0.08)",
                    transition: "background 0.2s",
                  }}
                />
              ))}
            </div>

            {/* Content */}
            <div style={{ padding: "24px 28px 20px" }}>
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                <div>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "#8a948e", letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 4px" }}>
                    {heading} · {current + 1} de {total}
                  </p>
                  <h2 style={{ fontSize: 20, fontWeight: 800, color: "#f2f5f3", margin: 0, letterSpacing: "-0.02em" }}>
                    {step.title}
                  </h2>
                </div>
                <button
                  onClick={handleClose}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    fontSize: 18, color: "#8a948e", lineHeight: 1, padding: 4, marginLeft: 12,
                  }}
                >×</button>
              </div>

              {/* Body */}
              <p style={{ fontSize: 14, color: "#c3cbc6", lineHeight: 1.75, margin: 0, minHeight: 80 }}>
                {step.body}
              </p>
            </div>

            {/* Navigation */}
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "16px 28px 24px",
              borderTop: "1px solid rgba(255,255,255,0.08)",
            }}>
              <button
                onClick={() => setCurrent((c) => Math.max(0, c - 1))}
                disabled={current === 0}
                style={{
                  background: "rgba(62,224,111,0.055)", color: "#c3cbc6",
                  border: "1px solid rgba(62,224,111,0.2)", borderRadius: 10,
                  padding: "9px 18px", fontSize: 13, fontWeight: 600,
                  cursor: current === 0 ? "default" : "pointer",
                  opacity: current === 0 ? 0.4 : 1,
                }}
              >
                ← Anterior
              </button>

              {current < total - 1 ? (
                <button
                  onClick={() => setCurrent((c) => c + 1)}
                  style={{
                    background: "#3ee06f", color: "#04120a",
                    border: "none", borderRadius: 10,
                    padding: "9px 22px", fontSize: 13, fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Próximo →
                </button>
              ) : (
                <button
                  onClick={handleClose}
                  style={{
                    background: "#3ee06f", color: "#04120a",
                    border: "none", borderRadius: 10,
                    padding: "9px 22px", fontSize: 13, fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Entendido ✓
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
