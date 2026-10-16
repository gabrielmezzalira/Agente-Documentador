import { ds, cardStyle } from "../../lib/ds";

interface Option<T extends string> {
  value: T;
  label: string;
}

/** Seletor segmentado (pílulas dentro de um cartão), como "Por sprint | Cross-sprint" e as janelas de Performance. */
export default function SegmentedControl<T extends string>({
  options, value, onChange, label,
}: {
  options: Option<T>[];
  value: T;
  onChange: (v: T) => void;
  /** Nome acessível do grupo. */
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} style={{ ...cardStyle, boxShadow: "none", borderRadius: 12, display: "flex", padding: 4, alignSelf: "flex-start", flexWrap: "wrap" }}>
      {options.map((o) => {
        const ativo = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={ativo}
            onClick={() => onChange(o.value)}
            style={{
              display: "flex", alignItems: "center", height: 34, padding: "0 14px", borderRadius: 9, border: "none",
              cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 600,
              background: ativo ? ds.greenSoft : "transparent",
              color: ativo ? ds.green : ds.muted,
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
