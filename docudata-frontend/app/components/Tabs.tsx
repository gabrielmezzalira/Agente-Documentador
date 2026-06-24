"use client";

interface TabItem {
  id: string;
  label: string;
  badge?: number | string;
}

interface Props {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
}

const stripStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
  borderBottom: "1px solid #e4e4ea",
  marginBottom: 24,
};

const tabBaseStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  padding: "10px 16px",
  fontSize: 14,
  fontWeight: 500,
  color: "#9696a0",
  cursor: "pointer",
  borderBottom: "2px solid transparent",
  marginBottom: -1,
  display: "flex",
  alignItems: "center",
  gap: 8,
};

const tabActiveStyle: React.CSSProperties = {
  ...tabBaseStyle,
  color: "#111116",
  fontWeight: 700,
  borderBottom: "2px solid #4ade80",
};

const badgeStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  background: "#dcfce7",
  color: "#16a34a",
  padding: "2px 7px",
  borderRadius: 10,
};

export default function Tabs({ tabs, active, onChange }: Props) {
  return (
    <div style={stripStyle}>
      {tabs.map((t) => (
        <button
          key={t.id}
          style={t.id === active ? tabActiveStyle : tabBaseStyle}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.badge !== undefined && t.badge !== 0 && <span style={badgeStyle}>{t.badge}</span>}
        </button>
      ))}
    </div>
  );
}
