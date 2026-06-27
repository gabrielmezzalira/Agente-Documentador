"use client";

import { useEffect, useRef, useState } from "react";
import { ingestFile } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  projetoId: string;
  sprintNumero: number;
  onCompleted?: () => void;
}

const ACCEPTED_EXTS = new Set([
  ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".sql",
  ".yaml", ".yml", ".json", ".csv", ".html", ".css", ".java",
  ".go", ".rs", ".rb", ".sh", ".toml", ".xml", ".env",
  ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp",
]);
const SKIP_DIRS = new Set([
  "node_modules", ".git", "__pycache__", ".venv", "venv",
  "dist", "build", ".next", ".cache", ".idea", ".vscode",
]);

async function resizeImageIfNeeded(f: File, maxDim = 1024): Promise<File> {
  if (!f.type.startsWith("image/")) return f;
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(f);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const { naturalWidth: w, naturalHeight: h } = img;
      if (w <= maxDim && h <= maxDim) { resolve(f); return; }
      const scale = maxDim / Math.max(w, h);
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(w * scale);
      canvas.height = Math.round(h * scale);
      canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => resolve(blob ? new File([blob], f.name, { type: "image/jpeg" }) : f),
        "image/jpeg",
        0.85
      );
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(f); };
    img.src = url;
  });
}

function isAcceptedFile(f: File): boolean {
  if (f.size < 100) return false;
  const path = (f as File & { webkitRelativePath: string }).webkitRelativePath || f.name;
  const segments = path.split("/");
  if (segments.slice(0, -1).some((s) => SKIP_DIRS.has(s))) return false;
  const ext = "." + (f.name.split(".").pop() ?? "").toLowerCase();
  return ACCEPTED_EXTS.has(ext);
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: 16,
};

const modalStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 12,
  width: "100%",
  maxWidth: 600,
  maxHeight: "90vh",
  overflowY: "auto",
  padding: 28,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 600,
  color: "#334155",
  marginBottom: 6,
  marginTop: 14,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "8px 12px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
};

const primaryBtn: React.CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 700,
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: React.CSSProperties = {
  background: "#f7f7fa",
  color: "#475569",
  border: "1px solid #e2e8f0",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

const modeTab = (active: boolean): React.CSSProperties => ({
  background: active ? "#4ade80" : "transparent",
  color: active ? "#052e16" : "#6a6a7a",
  border: "none",
  padding: "8px 16px",
  fontSize: 13,
  fontWeight: active ? 700 : 500,
  cursor: "pointer",
});

const dangerBtn: React.CSSProperties = {
  background: "#fef2f2",
  color: "#dc2626",
  border: "1px solid #fecaca",
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};

export default function UploadLivreModal({
  open,
  onClose,
  projetoId,
  sprintNumero,
  onCompleted,
}: Props) {
  const [mode, setMode] = useState<"file" | "folder">("file");
  const [file, setFile] = useState<File | null>(null);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);

  const [ingesting, setIngesting] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [folderProgress, setFolderProgress] = useState<
    { done: number; total: number; errors: string[]; cancelled?: boolean } | null
  >(null);
  const cancelRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      setFile(null);
      setFolderFiles([]);
      setFolderProgress(null);
      setMsg(null);
      cancelRef.current = false;
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (folderInputRef.current) folderInputRef.current.value = "";
    }
  }, [open]);

  if (!open) return null;

  async function handleSingle(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setIngesting(true);
    setMsg(null);
    try {
      await ingestFile(projetoId, sprintNumero, await resizeImageIfNeeded(file));
      setMsg({ ok: true, text: `"${file.name}" processado com sucesso.` });
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      onCompleted?.();
    } catch (err) {
      setMsg({ ok: false, text: err instanceof Error ? err.message : "Erro desconhecido" });
    } finally {
      setIngesting(false);
    }
  }

  function handleFolderChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFolderFiles(Array.from(e.target.files ?? []).filter(isAcceptedFile));
    setFolderProgress(null);
  }

  async function handleFolderIngest(e: React.FormEvent) {
    e.preventDefault();
    if (folderFiles.length === 0) return;
    cancelRef.current = false;
    setIngesting(true);
    setFolderProgress({ done: 0, total: folderFiles.length, errors: [] });
    const CONCURRENCY = 5;
    const errors: string[] = [];
    let done = 0;
    let idx = 0;
    async function worker() {
      while (true) {
        if (cancelRef.current) break;
        const myIdx = idx++;
        if (myIdx >= folderFiles.length) break;
        const f = folderFiles[myIdx];
        const relativePath =
          (f as File & { webkitRelativePath: string }).webkitRelativePath || f.name;
        try {
          const fileToSend = await resizeImageIfNeeded(
            new File([f], relativePath, { type: f.type })
          );
          await ingestFile(projetoId, sprintNumero, fileToSend);
        } catch {
          errors.push(relativePath);
        }
        done++;
        setFolderProgress({ done, total: folderFiles.length, errors: [...errors] });
      }
    }
    await Promise.all(Array.from({ length: CONCURRENCY }, worker));
    setIngesting(false);
    if (!cancelRef.current) {
      onCompleted?.();
    } else {
      setFolderProgress((p) => (p ? { ...p, cancelled: true } : null));
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "#0f172a" }}>
          Upload livre — Sprint {sprintNumero}
        </h2>
        <p style={{ fontSize: 13, color: "#6a6a7a", margin: "8px 0 0", lineHeight: 1.5 }}>
          Material avulso que alimenta o contexto do projeto: prints, código, atas externas,
          PDFs do cliente. Estes uploads alimentam as docs gerais (Onboarding, Documentação Final).
        </p>

        <div style={{
          display: "flex",
          border: "1px solid #e4e4ea",
          borderRadius: 8,
          overflow: "hidden",
          marginTop: 18,
          marginBottom: 6,
          width: "fit-content",
        }}>
          <button type="button" onClick={() => setMode("file")} style={modeTab(mode === "file")}>
            Arquivo
          </button>
          <button type="button" onClick={() => setMode("folder")} style={modeTab(mode === "folder")}>
            Pasta / Projeto
          </button>
        </div>

        {mode === "file" ? (
          <form onSubmit={handleSingle}>
            <label style={labelStyle}>Arquivo (.txt, .docx, .pdf, imagens, código)</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp,.py,.js,.ts,.tsx,.jsx,.sql,.md,.yaml,.yml,.json,.csv,.html,.css,.java,.go,.rs,.rb,.sh,.toml,.env,.xml"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              style={{ ...inputStyle, padding: "8px 12px" }}
            />
            {msg && (
              <p style={{
                fontSize: 13,
                color: msg.ok ? "#16a34a" : "#dc2626",
                marginTop: 10,
              }}>
                {msg.text}
              </p>
            )}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={ingesting}>
                Fechar
              </button>
              <button type="submit" disabled={ingesting || !file} style={primaryBtn}>
                {ingesting ? "Processando…" : "Enviar"}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleFolderIngest}>
            <label style={labelStyle}>Selecionar pasta inteira</label>
            <input
              ref={folderInputRef}
              type="file"
              /* @ts-expect-error webkitdirectory não é atributo padrão do TS */
              webkitdirectory=""
              multiple
              onChange={handleFolderChange}
              style={{ ...inputStyle, padding: "8px 12px" }}
            />
            {folderFiles.length > 0 && (
              <p style={{ fontSize: 13, color: "#9696a0", marginTop: 8 }}>
                {folderFiles.length} arquivo{folderFiles.length !== 1 ? "s" : ""} aceitos · node_modules, .git e binários ignorados
              </p>
            )}
            {folderProgress && (
              <div style={{ fontSize: 13, marginTop: 14 }}>
                <div style={{ background: "#f0f0f4", borderRadius: 4, height: 6, marginBottom: 8 }}>
                  <div style={{
                    background: folderProgress.cancelled ? "#b8b8c0" : folderProgress.errors.length > 0 ? "#d97706" : "#22c55e",
                    borderRadius: 4,
                    height: 6,
                    width: `${(folderProgress.done / folderProgress.total) * 100}%`,
                    transition: "width 0.2s",
                  }} />
                </div>
                {ingesting ? (
                  <p style={{ color: "#9696a0" }}>Processando {folderProgress.done} de {folderProgress.total} · 5 em paralelo</p>
                ) : folderProgress.cancelled ? (
                  <p style={{ color: "#9696a0" }}>Cancelado · {folderProgress.done - folderProgress.errors.length} processados</p>
                ) : (
                  <p style={{ color: folderProgress.errors.length === 0 ? "#16a34a" : "#d97706" }}>
                    ✓ {folderProgress.done - folderProgress.errors.length} processados
                    {folderProgress.errors.length > 0 && ` · ${folderProgress.errors.length} com erro`}
                  </p>
                )}
              </div>
            )}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={ingesting}>
                Fechar
              </button>
              {ingesting && (
                <button type="button" onClick={() => { cancelRef.current = true; }} style={dangerBtn}>
                  Cancelar
                </button>
              )}
              <button type="submit" disabled={ingesting || folderFiles.length === 0} style={primaryBtn}>
                {ingesting ? `${folderProgress?.done ?? 0}/${folderProgress?.total ?? 0}` : "Enviar pasta"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
