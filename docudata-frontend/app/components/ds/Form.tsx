import type { CSSProperties, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { ds, labelStyle } from "../../lib/ds";

const CONTROL: CSSProperties = {
  width: "100%",
  borderRadius: 10,
  background: ds.inner,
  border: `1px solid ${ds.innerBorder}`,
  color: ds.text,
  fontSize: 14,
  padding: "0 14px",
  fontFamily: "inherit",
};

export function Input({ style, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className="ds-control" style={{ ...CONTROL, height: 42, ...style }} {...rest} />;
}

export function Textarea({ style, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className="ds-control" style={{ ...CONTROL, padding: "12px 14px", lineHeight: 1.6, resize: "vertical", ...style }} {...rest} />;
}

export function Select({ style, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className="ds-control" style={{ ...CONTROL, height: 42, ...style }} {...rest} />;
}

interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: ReactNode;
  error?: string | null;
  required?: boolean;
  children: ReactNode;
}

/** Rótulo + controle + dica/erro. */
export function Field({ label, htmlFor, hint, error, required, children }: FieldProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label htmlFor={htmlFor} style={labelStyle}>
        {label}
        {required && <span style={{ color: ds.green }}> *</span>}
      </label>
      {children}
      {error ? (
        <span role="alert" style={{ fontSize: 12.5, color: ds.red }}>{error}</span>
      ) : (
        hint && <span style={{ fontSize: 12.5, color: ds.muted }}>{hint}</span>
      )}
    </div>
  );
}
