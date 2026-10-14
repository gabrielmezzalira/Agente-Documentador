"use client";

import { useEffect, useRef, useState } from "react";
import { ingestFile, ValidationError, type ValidationError422 } from "../lib/api";

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
  background: "#0d1711",
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
  color: "#c3cbc6",
  marginBottom: 6,
  marginTop: 14,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 8,
  padding: "8px 12px",
  fontSize: 14,
  outline: "none",
  background: "#0d1711",
  boxSizing: "border-box",
};

const primaryBtn: React.CSSProperties = {
  background: "#3ee06f",
  color: "#3ee06f",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 700,
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: React.CSSProperties = {
  background: "rgba(62,224,111,0.055)",
  color: "#c3cbc6",
  border: "1px solid rgba(62,224,111,0.2)",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

const modeTab = (active: boolean): React.CSSProperties => ({
  background: active ? "#3ee06f" : "transparent",
  color: active ? "#3ee06f" : "#8a948e",
  border: "none",
  padding: "8px 16px",
  fontSize: 13,
  fontWeight: active ? 700 : 500,
  cursor: "pointer",
});

const dangerBtn: React.CSSProperties = {
  background: "rgba(255,107,107,0.10)",
  color: "#ff6b6b",
  border: "1px solid rgba(255,107,107,0.30)",
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
  const [validationErr, setValidationErr] = useState<ValidationError422 | null>(null);

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
      setValidationErr(null);
      cancelRef.current = false;
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (folderInputRef.current) folderInputRef.current.value = "";
    }
  }, [open]);

  if (!open) return null;

  async function doIngest(force = false) {
    if (!file) return;
    setIngesting(true);
    setMsg(null);
    setValidationErr(null);
    try {
      await ingestFile(projetoId, sprintNumero, await resizeImageIfNeeded(file), force);
      setMsg({ ok: true, text: `"${file.name}" processado com sucesso.` });
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      onCompleted?.();
    } catch (err) {
      if (err instanceof ValidationError) {
        setValidationErr(err.detail);
      } else {
        setMsg({ ok: false, text: err instanceof Error ? err.message : "Erro desconhecido" });
      }
    } finally {
      setIngesting(false);
    }
  }

  async function handleSingle(e: React.FormEvent) {
    e.preventDefault();
    await doIngest();
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
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "#f2f5f3" }}>
          Upload livre — Sprint {sprintNumero}
        </h2>
        <p style={{ fontSize: 13, color: "#8a948e", margin: "8px 0 0", lineHeight: 1.5 }}>
          Material avulso que alimenta o contexto do projeto: prints, código, atas externas,
          PDFs do cliente. Estes uploads alimentam as docs gerais (Onboarding, Documentação Final).
        </p>

        <div style={{
          display: "flex",
          border: "1px solid rgba(62,224,111,0.2)",
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
                color: msg.ok ? "#3ee06f" : "#ff6b6b",
                marginTop: 10,
              }}>
                {msg.text}
              </p>
            )}
            {validationErr && (
              <div style={{ marginTop: 12, padding: 12, background: "rgba(242,193,78,0.10)", border: "1px solid rgba(242,193,78,0.30)", color: "#f2c14e", borderRadius: 8, fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Tipo de conteúdo diferente do esperado</div>
                <div>{validationErr.mensagem}</div>
                <div style={{ marginTop: 10, display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button type="button" style={ghostBtn} onClick={() => setValidationErr(null)} disabled={ingesting}>
                    Cancelar
                  </button>
                  <button
                    type="button"
                    style={{ ...primaryBtn, background: "#f2c14e", color: "#f2f5f3", opacity: ingesting ? 0.6 : 1 }}
                    onClick={() => doIngest(true)}
                    disabled={ingesting}
                  >
                    {ingesting ? "Processando…" : "Ingerir mesmo assim"}
                  </button>
                </div>
              </div>
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
              <p style={{ fontSize: 13, color: "#8a948e", marginTop: 8 }}>
                {folderFiles.length} arquivo{folderFiles.length !== 1 ? "s" : ""} aceitos · node_modules, .git e binários ignorados
              </p>
            )}
            {folderProgress && (
              <div style={{ fontSize: 13, marginTop: 14 }}>
                <div style={{ background: "rgba(62,224,111,0.055)", borderRadius: 4, height: 6, marginBottom: 8 }}>
                  <div style={{
                    background: folderProgress.cancelled ? "rgba(255,255,255,0.14)" : folderProgress.errors.length > 0 ? "#f2c14e" : "#3ee06f",
                    borderRadius: 4,
                    height: 6,
                    width: `${(folderProgress.done / folderProgress.total) * 100}%`,
                    transition: "width 0.2s",
                  }} />
                </div>
                {ingesting ? (
                  <p style={{ color: "#8a948e" }}>Processando {folderProgress.done} de {folderProgress.total} · 5 em paralelo</p>
                ) : folderProgress.cancelled ? (
                  <p style={{ color: "#8a948e" }}>Cancelado · {folderProgress.done - folderProgress.errors.length} processados</p>
                ) : (
                  <p style={{ color: folderProgress.errors.length === 0 ? "#3ee06f" : "#f2c14e" }}>
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
