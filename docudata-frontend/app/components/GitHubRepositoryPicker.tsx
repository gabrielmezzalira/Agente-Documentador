"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { GitHubRepositoryCandidate } from "../lib/api";

const DATE_FORMATTER = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" });

interface GitHubRepositoryPickerProps {
  open: boolean;
  projectName: string;
  repositories: GitHubRepositoryCandidate[];
  selected: number[];
  selectedRepositories: GitHubRepositoryCandidate[];
  busy: boolean;
  preparing: boolean;
  ready: boolean;
  searching: boolean;
  error: string;
  manageUrl: string | null;
  repositoryScope: "all" | "selected" | "unknown";
  hasMore: boolean;
  onSearch: (search: string) => void;
  onToggle: (repository: GitHubRepositoryCandidate) => void;
  onClose: () => void;
  onRetry: () => void;
  onConfirm: () => void;
}

export default function GitHubRepositoryPicker({
  open,
  projectName,
  repositories,
  selected,
  selectedRepositories,
  busy,
  preparing,
  ready,
  searching,
  error,
  manageUrl,
  repositoryScope,
  hasMore,
  onSearch,
  onToggle,
  onClose,
  onRetry,
  onConfirm,
}: GitHubRepositoryPickerProps) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"available" | "selected" | "results">("available");
  const lastRequestedSearchRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const fecharComEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", fecharComEscape);
    return () => {
      document.body.style.overflow = overflowAnterior;
      window.removeEventListener("keydown", fecharComEscape);
    };
  }, [busy, onClose, open]);

  useEffect(() => {
    if (open) {
      setSearch("");
      setFilter("available");
      lastRequestedSearchRef.current = null;
    }
  }, [open]);

  useEffect(() => {
    if (!open || !ready || filter === "selected") return;
    const normalizedSearch = search.trim();
    if (normalizedSearch.length === 1 || lastRequestedSearchRef.current === normalizedSearch) return;
    const timer = window.setTimeout(
      () => {
        lastRequestedSearchRef.current = normalizedSearch;
        onSearch(normalizedSearch);
      },
      normalizedSearch ? 450 : 0,
    );
    return () => window.clearTimeout(timer);
  }, [filter, onSearch, open, ready, search]);

  const filtered = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("pt-BR");
    const origem = filter === "selected" ? selectedRepositories : repositories;
    return origem.filter((repo) => {
      const correspondeAoFiltro = filter !== "available" || repo.connection_status === "available";
      return correspondeAoFiltro && (!term || repo.full_name.toLocaleLowerCase("pt-BR").includes(term));
    });
  }, [filter, repositories, search, selectedRepositories]);

  if (!open) return null;

  const available = repositories.filter((repo) => repo.connection_status === "available").length;
  const selectedCount = selected.length;

  return (
    <div
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 18,
        background: "rgba(15, 23, 42, 0.58)",
        backdropFilter: "blur(3px)",
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="github-picker-title"
        style={{
          width: "min(720px, 100%)",
          maxHeight: "min(760px, calc(100vh - 36px))",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          borderRadius: 16,
          border: "1px solid #e2e8f0",
          background: "#ffffff",
          boxShadow: "0 24px 70px rgba(15, 23, 42, 0.24)",
        }}
      >
        <header style={{ padding: "20px 22px 16px", borderBottom: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
            <div style={{ minWidth: 0 }}>
              <span style={{ display: "block", marginBottom: 5, color: "#6366f1", fontSize: 11, fontWeight: 750, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                {preparing ? "Preparando conexão" : "GitHub App conectado"}
              </span>
              <h2 id="github-picker-title" style={{ margin: 0, color: "#0f172a", fontSize: 20, lineHeight: 1.25 }}>
                Escolha os repositórios deste projeto
              </h2>
              <p style={{ margin: "7px 0 0", color: "#64748b", fontSize: 13, lineHeight: 1.5 }}>
                Marque apenas os repositórios que pertencem a <strong style={{ color: "#334155" }}>{projectName}</strong>. Nenhum deles será vinculado automaticamente.
              </p>
              {repositoryScope === "all" && (
                <span style={{ display: "inline-block", marginTop: 9, padding: "4px 8px", borderRadius: 999, background: "#ecfdf5", color: "#047857", fontSize: 11, fontWeight: 700 }}>
                  Todos os repositórios da organização estão disponíveis
                </span>
              )}
            </div>
            <button
              type="button"
              aria-label="Fechar seleção de repositórios"
              onClick={onClose}
              disabled={busy}
              style={{ flex: "0 0 auto", width: 34, height: 34, border: "1px solid #e2e8f0", borderRadius: 9, background: "#fff", color: "#64748b", fontSize: 20, cursor: busy ? "not-allowed" : "pointer" }}
            >
              ×
            </button>
          </div>
        </header>

        <div style={{ padding: "14px 22px 10px" }}>
          {error && (
            <p role="alert" style={{ margin: "0 0 10px", padding: "9px 11px", borderRadius: 8, background: "#fef2f2", color: "#b91c1c", fontSize: 12 }}>
              {error}
            </p>
          )}
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar em todos os repositórios da organização..."
            aria-label="Buscar repositórios"
            disabled={!ready || preparing}
            autoFocus
            style={{ width: "100%", minHeight: 42, padding: "9px 12px", border: "1px solid #cbd5e1", borderRadius: 9, background: ready ? "#fff" : "#f8fafc", color: "#0f172a", fontSize: 13, outlineColor: "#6366f1" }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 9, color: "#64748b", fontSize: 12 }}>
            <span>{preparing ? "Conectando ao GitHub..." : searching ? "Buscando no GitHub..." : `${filtered.length} resultado${filtered.length === 1 ? "" : "s"}`}</span>
            <strong style={{ color: selectedCount ? "#4338ca" : "#64748b" }}>
              {selectedCount} selecionado{selectedCount === 1 ? "" : "s"}
            </strong>
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 10, overflowX: "auto", paddingBottom: 2 }}>
            {([
              ["available", `Disponíveis (${available})`],
              ["selected", `Selecionados (${selectedCount})`],
              ["results", `Resultados (${repositories.length})`],
            ] as const).map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-pressed={filter === id}
                onClick={() => setFilter(id)}
                disabled={!ready || preparing}
                style={{ flex: "0 0 auto", padding: "6px 9px", border: `1px solid ${filter === id ? "#a5b4fc" : "#e2e8f0"}`, borderRadius: 8, background: filter === id ? "#eef2ff" : "#fff", color: filter === id ? "#4338ca" : "#64748b", fontSize: 11, fontWeight: 700, opacity: ready && !preparing ? 1 : 0.55, cursor: ready && !preparing ? "pointer" : "not-allowed" }}
              >
                {label}
              </button>
            ))}
          </div>
          {!search.trim() && hasMore && !searching && (
            <p style={{ margin: "7px 0 0", color: "#64748b", fontSize: 11 }}>
              Exibindo os 30 repositórios com atividade mais recente. Use a busca para encontrar qualquer outro.
            </p>
          )}
          {search.trim().length === 1 && (
            <p style={{ margin: "7px 0 0", color: "#64748b", fontSize: 11 }}>
              Digite mais um caractere para buscar em toda a organização. Enquanto isso, filtramos os itens recentes.
            </p>
          )}
        </div>

        <div style={{ minHeight: 160, overflowY: "auto", padding: "4px 22px 14px" }}>
          {preparing || (searching && repositories.length === 0) ? (
            <div role="status" style={{ padding: "32px 16px", textAlign: "center", color: "#64748b", fontSize: 13 }}>
              <div style={{ display: "grid", gap: 9, marginBottom: 14 }}>
                {["82%", "66%", "74%"].map((width) => (
                  <span key={width} style={{ display: "block", width, height: 12, margin: "0 auto", borderRadius: 999, background: "#e2e8f0" }} />
                ))}
              </div>
              {preparing ? "Preparando uma conexão segura…" : "Buscando repositórios…"}
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: "32px 16px", border: "1px dashed #cbd5e1", borderRadius: 10, textAlign: "center", color: "#64748b", fontSize: 13 }}>
              {repositories.length === 0
                ? "O GitHub App ainda não tem acesso a nenhum repositório."
                : search.trim()
                  ? "Nenhum repositório encontrado para essa busca."
                  : filter === "selected"
                    ? "Nenhum repositório selecionado ainda."
                    : filter === "available"
                      ? "Não há outros repositórios disponíveis para este projeto."
                      : "Nenhum repositório disponível."}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {filtered.map((repo) => {
                const selectable = repo.connection_status === "available";
                const checked = selected.includes(repo.github_repository_id);
                const [owner, ...nameParts] = repo.full_name.split("/");
                const name = nameParts.join("/") || owner;
                return (
                  <label
                    key={repo.github_repository_id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "12px 13px",
                      border: `1px solid ${checked ? "#a5b4fc" : "#e2e8f0"}`,
                      borderRadius: 10,
                      background: checked ? "#f5f3ff" : "#fff",
                      opacity: selectable ? 1 : 0.62,
                      cursor: selectable ? "pointer" : "not-allowed",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!selectable || busy}
                      onChange={() => onToggle(repo)}
                      style={{ width: 17, height: 17, accentColor: "#6366f1", flex: "0 0 auto" }}
                    />
                    <span style={{ minWidth: 0, flex: 1 }}>
                      <span style={{ display: "block", color: "#0f172a", fontSize: 13, fontWeight: 700, overflowWrap: "anywhere" }}>
                        {name}
                      </span>
                      <span style={{ display: "block", marginTop: 3, color: "#64748b", fontSize: 11 }}>
                        {owner} · branch {repo.default_branch ?? "padrão não informada"}
                        {repo.pushed_at && ` · atividade em ${DATE_FORMATTER.format(new Date(repo.pushed_at))}`}
                      </span>
                    </span>
                    <span style={{ flex: "0 0 auto", padding: "4px 7px", borderRadius: 999, background: "#f1f5f9", color: "#64748b", fontSize: 10, fontWeight: 700 }}>
                      {repo.connection_status === "connected_here"
                        ? "Já conectado"
                        : repo.connection_status === "unavailable"
                          ? "Em outro projeto"
                          : repo.private
                            ? "Privado"
                            : "Público"}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <footer style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap", padding: "14px 22px", borderTop: "1px solid #e2e8f0", background: "#f8fafc" }}>
          {repositoryScope === "all" ? (
            <span style={{ color: "#64748b", fontSize: 11 }}>
              Acesso organizacional completo
            </span>
          ) : manageUrl ? (
            <a href={manageUrl} target="_blank" rel="noreferrer" style={{ color: "#4f46e5", fontSize: 12, fontWeight: 650, textDecoration: "none" }}>
              Liberar mais repositórios no GitHub ↗
            </a>
          ) : <span />}
          <div style={{ display: "flex", gap: 8, marginLeft: "auto" }}>
            <button type="button" onClick={onClose} disabled={busy} style={{ padding: "9px 14px", border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff", color: "#475569", fontSize: 12, fontWeight: 650, cursor: busy ? "not-allowed" : "pointer" }}>
              Cancelar
            </button>
            {!preparing && error && !ready ? (
              <button type="button" onClick={onRetry} style={{ padding: "9px 14px", border: "none", borderRadius: 8, background: "#6366f1", color: "#fff", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                Tentar novamente
              </button>
            ) : (
              <button type="button" onClick={onConfirm} disabled={busy || preparing || selectedCount === 0} style={{ padding: "9px 14px", border: "none", borderRadius: 8, background: "#6366f1", color: "#fff", fontSize: 12, fontWeight: 700, opacity: busy || preparing || selectedCount === 0 ? 0.5 : 1, cursor: busy || preparing || selectedCount === 0 ? "not-allowed" : "pointer" }}>
                {busy
                  ? "Conectando..."
                  : `Conectar ${selectedCount} repositório${selectedCount === 1 ? "" : "s"}`}
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}
