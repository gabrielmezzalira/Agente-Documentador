"use client";

import { useEffect, useState } from "react";
import { Button, Chip, Field, Input, PageHeader } from "../components/ds";
import { PanelCard } from "../components/painel/PanelCard";
import { ds } from "../lib/ds";
import {
  getGeminiApiKeyStatus,
  updateGeminiApiKey,
  type GeminiApiKeyStatus,
} from "../lib/api";

export default function SettingsPage() {
  const [status, setStatus] = useState<GeminiApiKeyStatus | null>(null);
  const [newKey, setNewKey] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    getGeminiApiKeyStatus()
      .then(setStatus)
      .catch(() => setMessage({ ok: false, text: "Não foi possível carregar a configuração." }))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!newKey.trim()) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateGeminiApiKey(newKey.trim());
      setStatus(updated);
      setNewKey("");
      setEditing(false);
      setMessage({ ok: true, text: "Chave Gemini salva com sucesso." });
    } catch {
      setMessage({ ok: false, text: "Não foi possível salvar a chave Gemini." });
    } finally {
      setSaving(false);
    }
  }

  const showForm = status?.configured !== true || editing;

  return (
    <>
      <PageHeader title="Configurações" subtitle="Configurações compartilhadas por toda a aplicação." />

      <div style={{ maxWidth: 760 }}>
        <PanelCard
          label="Gemini"
          action={!loading && <Chip tone={status?.configured ? "green" : "red"} dot={status?.configured}>{status?.configured ? "Chave configurada" : "Chave não configurada"}</Chip>}
        >
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: ds.muted }}>Chave utilizada pelos recursos de IA de toda a aplicação.</p>

          {loading ? (
            <p role="status" style={{ margin: 0, color: ds.muted, fontSize: 14 }}>Carregando...</p>
          ) : (
            <>
              {status?.configured && (
                <div style={{ display: "flex", alignItems: "baseline", gap: 14, flexWrap: "wrap" }}>
                  <code style={{ fontFamily: ds.fontMono, fontSize: 14, color: ds.text }}>{status.key_hint}</code>
                  {status.updated_at && (
                    <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>
                      atualizada em {new Date(status.updated_at).toLocaleString("pt-BR")}
                    </span>
                  )}
                </div>
              )}

              {showForm ? (
                <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <Field label="Nova chave Gemini" htmlFor="gemini-new-key" required>
                    <Input
                      id="gemini-new-key"
                      type="password"
                      autoComplete="new-password"
                      value={newKey}
                      onChange={(event) => setNewKey(event.target.value)}
                      placeholder="AIza..."
                      required
                    />
                  </Field>
                  <div style={{ display: "flex", gap: 10 }}>
                    <Button type="submit" variant="primary" disabled={saving || !newKey.trim()}>
                      {saving ? "Salvando..." : "Salvar chave"}
                    </Button>
                    {status?.configured && (
                      <Button variant="ghost" disabled={saving} onClick={() => { setEditing(false); setNewKey(""); }}>Cancelar</Button>
                    )}
                  </div>
                </form>
              ) : (
                <div>
                  <Button variant="secondary" onClick={() => { setEditing(true); setMessage(null); }}>Alterar chave</Button>
                </div>
              )}

              {message && (
                <p role={message.ok ? "status" : "alert"} style={{ margin: 0, fontSize: 13, color: message.ok ? ds.green : ds.red }}>{message.text}</p>
              )}
            </>
          )}
        </PanelCard>
      </div>
    </>
  );
}
