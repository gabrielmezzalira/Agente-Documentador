"use client";

import { useEffect, useRef } from "react";

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
  width: "100%",
  display: "flex",
  gap: 4,
  overflowX: "auto",
  overscrollBehaviorX: "contain",
  WebkitOverflowScrolling: "touch",
  scrollbarWidth: "thin",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
  marginBottom: 28,
  marginTop: 6,
};

const tabBaseStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  padding: "12px 14px",
  fontSize: 14,
  fontFamily: "inherit",
  fontWeight: 500,
  color: "#8a948e",
  cursor: "pointer",
  borderBottom: "2px solid transparent",
  marginBottom: -1,
  display: "flex",
  alignItems: "center",
  gap: 8,
  flex: "0 0 auto",
  whiteSpace: "nowrap",
};

const tabActiveStyle: React.CSSProperties = {
  ...tabBaseStyle,
  color: "#ffffff",
  fontWeight: 600,
  borderBottom: "2px solid #3ee06f",
};

const badgeStyle: React.CSSProperties = {
  fontFamily: "'Geist Mono', ui-monospace, monospace",
  fontSize: 10.5,
  background: "rgba(62,224,111,0.12)",
  color: "#3ee06f",
  padding: "1px 7px",
  borderRadius: 999,
};

export default function Tabs({ tabs, active, onChange }: Props) {
  const activeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  }, [active]);

  return (
    <div style={stripStyle} role="tablist" aria-label="Seções do projeto">
      {tabs.map((t) => (
        <button
          key={t.id}
          ref={t.id === active ? activeRef : undefined}
          type="button"
          role="tab"
          aria-selected={t.id === active}
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
