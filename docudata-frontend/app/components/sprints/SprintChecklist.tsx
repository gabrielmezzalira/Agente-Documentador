import { ds } from "../../lib/ds";

export type ChecklistState = "done" | "pending" | "optional";

export interface ChecklistItem {
  key: string;
  label: string;
  state: ChecklistState;
  /** Texto em mono ao lado do rótulo (ex.: "1/1", "opcional"). */
  count: string;
  onClick?: () => void;
  title?: string;
}

function CheckCircle({ state }: { state: ChecklistState }) {
  const base = { width: 18, height: 18, borderRadius: "50%", flexShrink: 0, boxSizing: "border-box" as const };
  if (state === "done") {
    return (
      <span aria-hidden="true" style={{ ...base, background: ds.green, color: "#04120a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800 }}>
        ✓
      </span>
    );
  }
  if (state === "pending") return <span aria-hidden="true" style={{ ...base, border: `1.5px solid ${ds.amber}` }} />;
  return <span aria-hidden="true" style={{ ...base, border: `1.5px dashed ${ds.dim}` }} />;
}

const STATE_LABEL: Record<ChecklistState, string> = { done: "feito", pending: "pendente", optional: "opcional" };

/** Linha de documentos da sprint: círculo de check + rótulo + contagem (protótipo 03). */
export default function SprintChecklist({ items }: { items: ChecklistItem[] }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 28 }}>
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          className="ds-check-item"
          onClick={item.onClick}
          title={item.title}
          aria-label={`${item.label}: ${item.count} (${STATE_LABEL[item.state]})`}
          style={{
            display: "flex", alignItems: "center", gap: 8, padding: 0,
            background: "none", border: "none", cursor: item.onClick ? "pointer" : "default",
            fontFamily: "inherit", fontSize: 14, fontWeight: 500,
            color: item.state === "optional" ? ds.muted : ds.text,
          }}
        >
          <CheckCircle state={item.state} />
          {item.label}
          <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: item.state === "pending" ? ds.amber : ds.muted }}>
            {item.count}
          </span>
        </button>
      ))}
    </div>
  );
}

/** Mini-barras (uma por documento obrigatório) usadas na linha recolhida da sprint fechada. */
export function ChecklistBars({ items }: { items: ChecklistItem[] }) {
  const required = items.filter((i) => i.state !== "optional");
  const done = required.filter((i) => i.state === "done").length;
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, color: ds.text2 }}>
      <span aria-hidden="true" style={{ display: "flex", gap: 3 }}>
        {required.map((i) => (
          <span key={i.key} style={{ width: 16, height: 5, borderRadius: 2, background: i.state === "done" ? ds.green : ds.amber }} />
        ))}
      </span>
      {done} de {required.length} documentos
    </span>
  );
}
