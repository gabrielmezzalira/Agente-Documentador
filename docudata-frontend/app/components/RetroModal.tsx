"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { enrichContent, submitRetrospectiva, type EnrichResult, type SprintDocResponse } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  projetoId: string;
  sprintNumero: number;
  onSubmitted?: (response: SprintDocResponse) => void;
}

const overlayStyle: CSSProperties = { position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.55)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 };
const modalStyle: CSSProperties = { background: "#fff", borderRadius: 12, width: "100%", maxWidth: 600, maxHeight: "90vh", overflowY: "auto", padding: 24, boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)" };
const labelStyle: CSSProperties = { display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6, marginTop: 14 };
const inputStyle: CSSProperties = { width: "100%", border: "1px solid #e2e8f0", borderRadius: 8, padding: "8px 10px", fontSize: 14, outline: "none", background: "#fff", boxSizing: "border-box" };
const textareaStyle: CSSProperties = { ...inputStyle, resize: "vertical", minHeight: 80, fontFamily: "inherit" };
const primaryBtn: CSSProperties = { background: "#4ade80", color: "#052e16", border: "none", padding: "10px 18px", borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: "pointer" };
const ghostBtn: CSSProperties = { background: "#f7f7fa", color: "#475569", border: "1px solid #e2e8f0", padding: "10px 18px", borderRadius: 8, fontWeight: 600, fontSize: 14, cursor: "pointer" };
const aiBadgeStyle: CSSProperties = { fontSize: 11, background: "#eff6ff", color: "#2563eb", border: "1px solid #bfdbfe", borderRadius: 4, padding: "1px 6px", marginLeft: 6, fontWeight: 500 };
const sectionStyle: CSSProperties = { background: "#f8fafc", borderRadius: 8, padding: "10px 14px", marginTop: 14 };
const sectionTitleStyle: CSSProperties = { fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 };

export default function RetroModal({ open, onClose, projetoId, sprintNumero, onSubmitted }: Props) {
  const [step, setStep] = useState<"input" | "form">("input");
  const [enrichText, setEnrichText] = useState("");
  const enrichFileRef = useRef<HTMLInputElement | null>(null);
  const [enrichFileName, setEnrichFileName] = useState<string | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [aiFields, setAiFields] = useState<Set<string>>(new Set());

  // Campos base
  const [observacoes, setObservacoes] = useState("");
  const [pedidoForaEscopoStatus, setPedidoForaEscopoStatus] = useState("");

  // Template 3 CITi
  const [squad, setSquad] = useState("");
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFim, setPeriodoFim] = useState("");
  const [subarea, setSubarea] = useState("");
  const [oQueFuncionou, setOQueFuncionou] = useState<string[]>(["", ""]);
  const [oQueNaoFuncionou, setOQueNaoFuncionou] = useState<string[]>(["", ""]);
  const [causaRaizImpacto, setCausaRaizImpacto] = useState<{ causa_raiz_num: string; impacto: string }[]>([
    { causa_raiz_num: "", impacto: "" },
  ]);
  const [acoesMelhoria, setAcoesMelhoria] = useState<{ acao: string; responsavel: string; prazo: string }[]>([
    { acao: "", responsavel: "", prazo: "" },
  ]);
  const [houvePedidoForaEscopo, setHouvePedidoForaEscopo] = useState("");
  const [statusPedidoForaEscopo, setStatusPedidoForaEscopo] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [anexoName, setAnexoName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setStep("input"); setEnrichText(""); setEnrichFileName(null); setEnriching(false);
      setAiFields(new Set()); setObservacoes(""); setPedidoForaEscopoStatus("");
      setSquad(""); setPeriodoInicio(""); setPeriodoFim(""); setSubarea("");
      setOQueFuncionou(["", ""]); setOQueNaoFuncionou(["", ""]);
      setCausaRaizImpacto([{ causa_raiz_num: "", impacto: "" }]);
      setAcoesMelhoria([{ acao: "", responsavel: "", prazo: "" }]);
      setHouvePedidoForaEscopo(""); setStatusPedidoForaEscopo("");
      setSubmitting(false); setError(null); setAnexoName(null);
      if (fileRef.current) fileRef.current.value = "";
      if (enrichFileRef.current) enrichFileRef.current.value = "";
    }
  }, [open]);

  if (!open) return null;

  const AiBadge = ({ field }: { field: string }) =>
    aiFields.has(field) ? <span style={aiBadgeStyle}>IA</span> : null;

  const toDate = (s: string) => { const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/); return m ? `${m[3]}-${m[2]}-${m[1]}` : s; };

  const handleEnrich = async () => {
    setEnriching(true);
    setError(null);
    const arquivo = enrichFileRef.current?.files?.[0] ?? null;
    try {
      const result: EnrichResult = await enrichContent({ projetoId, docType: "retrospectiva", texto: enrichText.trim() || undefined, arquivo: arquivo || undefined });
      const fields = new Set<string>();
      if (result.observacoes) { setObservacoes(result.observacoes); fields.add("observacoes"); }
      if (result.pedido_fora_escopo_status) { setPedidoForaEscopoStatus(result.pedido_fora_escopo_status); fields.add("pedidoStatus"); }
      if (result.squad) { setSquad(result.squad); fields.add("squad"); }
      if (result.subarea) { setSubarea(result.subarea); fields.add("subarea"); }
      if (result.periodo_inicio) { setPeriodoInicio(toDate(result.periodo_inicio)); fields.add("periodo"); }
      if (result.periodo_fim) { setPeriodoFim(toDate(result.periodo_fim)); fields.add("periodo"); }
      if (result.o_que_funcionou?.length) { setOQueFuncionou(result.o_que_funcionou.concat(result.o_que_funcionou.length < 2 ? [""] : [])); fields.add("oQueFuncionou"); }
      if (result.o_que_nao_funcionou?.length) { setOQueNaoFuncionou(result.o_que_nao_funcionou.concat(result.o_que_nao_funcionou.length < 2 ? [""] : [])); fields.add("oQueNaoFuncionou"); }
      if (result.causa_raiz_impacto?.length) { setCausaRaizImpacto(result.causa_raiz_impacto); fields.add("causaRaiz"); }
      if (result.acoes_melhoria?.length) { setAcoesMelhoria(result.acoes_melhoria.slice(0, 2)); fields.add("acoesMelhoria"); }
      if (result.houve_pedido_fora_escopo) { setHouvePedidoForaEscopo(result.houve_pedido_fora_escopo); fields.add("houveEscopo"); }
      if (result.status_pedido_fora_escopo) { setStatusPedidoForaEscopo(result.status_pedido_fora_escopo); fields.add("statusEscopo"); }
      setAiFields(fields);
      setStep("form");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao analisar conteúdo");
    } finally {
      setEnriching(false);
    }
  };

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    const file = fileRef.current?.files?.[0] ?? null;
    try {
      const cleanOQF = oQueFuncionou.filter((s) => s.trim());
      const cleanOQNF = oQueNaoFuncionou.filter((s) => s.trim());
      const cleanCRI = causaRaizImpacto.filter((r) => r.causa_raiz_num.trim());
      const cleanAM = acoesMelhoria.filter((a) => a.acao.trim()).slice(0, 2);
      const response = await submitRetrospectiva({
        projetoId,
        sprintNumero,
        observacoes: observacoes || undefined,
        pedidoForaEscopoStatus: pedidoForaEscopoStatus || undefined,
        squad: squad || undefined,
        periodoInicio: periodoInicio || undefined,
        periodoFim: periodoFim || undefined,
        subarea: subarea || undefined,
        oQueFuncionou: cleanOQF.length ? cleanOQF : undefined,
        oQueNaoFuncionou: cleanOQNF.length ? cleanOQNF : undefined,
        causaRaizImpacto: cleanCRI.length ? cleanCRI : undefined,
        acoesMelhoria: cleanAM.length ? cleanAM : undefined,
        houvePedidoForaEscopo: houvePedidoForaEscopo || undefined,
        statusPedidoForaEscopo: statusPedidoForaEscopo || undefined,
        anexo: file,
      });
      onSubmitted?.(response);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao gerar retrospectiva");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
            Gerar Retrospectiva — Sprint {sprintNumero}
          </h2>
          {step === "form" && <span style={{ fontSize: 12, color: "#64748b" }}>Etapa 2 de 2 — Revise e confirme</span>}
        </div>

        {/* ── ETAPA 1 ── */}
        {step === "input" && (
          <>
            <p style={{ fontSize: 13, color: "#64748b", marginTop: 12, marginBottom: 0 }}>
              Cole a matéria-prima da retro ou faça upload de um arquivo. A IA vai preencher os campos para você revisar antes de gerar.
            </p>
            <label style={labelStyle}>Texto (cole aqui)</label>
            <textarea style={{ ...textareaStyle, minHeight: 160 }} value={enrichText} onChange={(e) => setEnrichText(e.target.value)}
              placeholder="Ex: anotações da reunião de retro, transcrição, relato pós-sprint..." />
            <label style={labelStyle}>Ou faça upload de arquivo</label>
            <input ref={enrichFileRef} type="file" accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setEnrichFileName(e.target.files?.[0]?.name ?? null)} />
            {enrichFileName && <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Arquivo: {enrichFileName}</div>}
            {error && <div style={{ marginTop: 14, padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, fontSize: 13 }}>{error}</div>}
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={enriching}>Cancelar</button>
              <button type="button" style={ghostBtn} onClick={() => { setError(null); setStep("form"); }} disabled={enriching}>Preencher manualmente</button>
              <button type="button" style={{ ...primaryBtn, opacity: enriching || (!enrichText.trim() && !enrichFileName) ? 0.6 : 1 }}
                onClick={handleEnrich} disabled={enriching || (!enrichText.trim() && !enrichFileName)}>
                {enriching ? "Analisando..." : "Analisar com IA"}
              </button>
            </div>
          </>
        )}

        {/* ── ETAPA 2 ── */}
        {step === "form" && (
          <>
            {aiFields.size > 0 && (
              <div style={{ marginTop: 12, padding: "8px 12px", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 8, fontSize: 13, color: "#1e40af" }}>
                Campos marcados com <strong>IA</strong> foram preenchidos automaticamente — revise antes de confirmar.
              </div>
            )}

            {/* Cabeçalho */}
            <div style={sectionStyle}>
              <div style={sectionTitleStyle}>Cabeçalho</div>
              <label style={{ ...labelStyle, marginTop: 4 }}>Squad (membros e papéis) <AiBadge field="squad" /></label>
              <input style={inputStyle} value={squad} onChange={(e) => setSquad(e.target.value)}
                placeholder="Ex: Gabriel (Gerente), Ana (Analista)" />
              <label style={labelStyle}>Período da sprint <AiBadge field="periodo" /></label>
              <div style={{ display: "flex", gap: 8 }}>
                <input type="date" style={{ ...inputStyle, flex: 1 }} value={periodoInicio} onChange={(e) => setPeriodoInicio(e.target.value)} />
                <input type="date" style={{ ...inputStyle, flex: 1 }} value={periodoFim} onChange={(e) => setPeriodoFim(e.target.value)} />
              </div>
              <label style={labelStyle}>Subárea <AiBadge field="subarea" /></label>
              <select style={{ ...inputStyle, cursor: "pointer" }} value={subarea} onChange={(e) => setSubarea(e.target.value)}>
                <option value="">Selecione...</option>
                <option value="dados">Dados</option>
                <option value="desenvolvimento">Desenvolvimento</option>
                <option value="produto">Produto</option>
              </select>
            </div>

            {/* O que Funcionou */}
            <div style={sectionStyle}>
              <div style={sectionTitleStyle}>O que Funcionou <AiBadge field="oQueFuncionou" /></div>
              {oQueFuncionou.map((v, idx) => (
                <div key={idx} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                  <input style={{ ...inputStyle, flex: 1 }} value={v} placeholder={`Item ${idx + 1} — ex: Entrega do pipeline no prazo`}
                    onChange={(e) => { const n = [...oQueFuncionou]; n[idx] = e.target.value; setOQueFuncionou(n); }} />
                  {oQueFuncionou.length > 1 && (
                    <button type="button" style={ghostBtn} onClick={() => setOQueFuncionou(oQueFuncionou.filter((_, i) => i !== idx))}>−</button>
                  )}
                </div>
              ))}
              <button type="button" style={{ ...ghostBtn, marginTop: 4 }} onClick={() => setOQueFuncionou([...oQueFuncionou, ""])}>+ Adicionar</button>
            </div>

            {/* O que Não Funcionou */}
            <div style={sectionStyle}>
              <div style={sectionTitleStyle}>O que Não Funcionou <AiBadge field="oQueNaoFuncionou" /></div>
              {oQueNaoFuncionou.map((v, idx) => (
                <div key={idx} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                  <input style={{ ...inputStyle, flex: 1 }} value={v} placeholder={`Item ${idx + 1} — ex: Estimativa equivocada no item X`}
                    onChange={(e) => { const n = [...oQueNaoFuncionou]; n[idx] = e.target.value; setOQueNaoFuncionou(n); }} />
                  {oQueNaoFuncionou.length > 1 && (
                    <button type="button" style={ghostBtn} onClick={() => setOQueNaoFuncionou(oQueNaoFuncionou.filter((_, i) => i !== idx))}>−</button>
                  )}
                </div>
              ))}
              <button type="button" style={{ ...ghostBtn, marginTop: 4 }} onClick={() => setOQueNaoFuncionou([...oQueNaoFuncionou, ""])}>+ Adicionar</button>
            </div>

            {/* Causa Raiz × Impacto */}
            <div style={sectionStyle}>
              <div style={sectionTitleStyle}>Causa Raiz × Impacto <AiBadge field="causaRaiz" /></div>
              <p style={{ fontSize: 11, color: "#9696a0", margin: "0 0 8px" }}>
                1=Especif. incompleta · 2=Dep. cliente atrasada · 3=Escopo novo · 4=Estimativa equivocada · 5=Bloqueio técnico · 6=Ausência membro · 7=Outro
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "3fr 120px auto", gap: 6, marginBottom: 4 }}>
                {["Causa raiz (nº e nome)", "Impacto", ""].map((h, i) => (
                  <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                ))}
              </div>
              {causaRaizImpacto.map((row, idx) => (
                <div key={idx} style={{ display: "grid", gridTemplateColumns: "3fr 120px auto", gap: 6, marginBottom: 6 }}>
                  <input style={inputStyle} value={row.causa_raiz_num} placeholder="Ex: 4: Estimativa equivocada"
                    onChange={(e) => { const n = [...causaRaizImpacto]; n[idx] = { ...n[idx], causa_raiz_num: e.target.value }; setCausaRaizImpacto(n); }} />
                  <select style={{ ...inputStyle, cursor: "pointer" }} value={row.impacto}
                    onChange={(e) => { const n = [...causaRaizImpacto]; n[idx] = { ...n[idx], impacto: e.target.value }; setCausaRaizImpacto(n); }}>
                    <option value="">—</option>
                    <option value="Baixo">Baixo</option>
                    <option value="Médio">Médio</option>
                    <option value="Alto">Alto</option>
                  </select>
                  {causaRaizImpacto.length > 1 && (
                    <button type="button" style={ghostBtn} onClick={() => setCausaRaizImpacto(causaRaizImpacto.filter((_, i) => i !== idx))}>−</button>
                  )}
                </div>
              ))}
              <button type="button" style={{ ...ghostBtn, marginTop: 4 }} onClick={() => setCausaRaizImpacto([...causaRaizImpacto, { causa_raiz_num: "", impacto: "" }])}>+ Adicionar causa raiz</button>
            </div>

            {/* Ações de Melhoria */}
            <div style={sectionStyle}>
              <div style={sectionTitleStyle}>Ações de Melhoria (máx. 2) <AiBadge field="acoesMelhoria" /></div>
              <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr 2fr auto", gap: 6, marginBottom: 4 }}>
                {["Ação", "Responsável", "Prazo", ""].map((h, i) => (
                  <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                ))}
              </div>
              {acoesMelhoria.map((row, idx) => (
                <div key={idx} style={{ display: "grid", gridTemplateColumns: "3fr 2fr 2fr auto", gap: 6, marginBottom: 6 }}>
                  <input style={inputStyle} value={row.acao} placeholder="Ex: Revisar estimativas no planning"
                    onChange={(e) => { const n = [...acoesMelhoria]; n[idx] = { ...n[idx], acao: e.target.value }; setAcoesMelhoria(n); }} />
                  <input style={inputStyle} value={row.responsavel} placeholder="Ex: Gabriel"
                    onChange={(e) => { const n = [...acoesMelhoria]; n[idx] = { ...n[idx], responsavel: e.target.value }; setAcoesMelhoria(n); }} />
                  <input style={inputStyle} value={row.prazo} placeholder="Ex: Sprint 3"
                    onChange={(e) => { const n = [...acoesMelhoria]; n[idx] = { ...n[idx], prazo: e.target.value }; setAcoesMelhoria(n); }} />
                  {acoesMelhoria.length > 1 && (
                    <button type="button" style={ghostBtn} onClick={() => setAcoesMelhoria(acoesMelhoria.filter((_, i) => i !== idx))}>−</button>
                  )}
                </div>
              ))}
              {acoesMelhoria.length < 2 && (
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }} onClick={() => setAcoesMelhoria([...acoesMelhoria, { acao: "", responsavel: "", prazo: "" }])}>+ Adicionar ação</button>
              )}
            </div>

            {/* Pedido Fora de Escopo */}
            <div style={sectionStyle}>
              <div style={sectionTitleStyle}>Pedido Fora de Escopo</div>
              <label style={{ ...labelStyle, marginTop: 4 }}>Houve pedido fora de escopo nesta sprint? <AiBadge field="houveEscopo" /></label>
              <div style={{ display: "flex", gap: 16, marginTop: 6 }}>
                {["sim", "nao"].map((v) => (
                  <label key={v} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, cursor: "pointer" }}>
                    <input type="radio" name="houveEscopo" value={v} checked={houvePedidoForaEscopo === v}
                      onChange={() => setHouvePedidoForaEscopo(v)} />
                    {v === "sim" ? "Sim" : "Não"}
                  </label>
                ))}
              </div>
              {houvePedidoForaEscopo === "sim" && (
                <>
                  <label style={labelStyle}>Status do registro <AiBadge field="statusEscopo" /></label>
                  <input style={inputStyle} value={statusPedidoForaEscopo} onChange={(e) => setStatusPedidoForaEscopo(e.target.value)}
                    placeholder="Ex: Lista informal · CR formalizado · Aceito para Sprint 4" />
                </>
              )}
            </div>

            {/* Observações */}
            <label style={labelStyle}>Observações do gerente <span style={{ fontWeight: 400, color: "#9696a0" }}>(opcional)</span> <AiBadge field="observacoes" /></label>
            <textarea style={textareaStyle} value={observacoes} onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Tópicos discutidos na reunião de retro, o que o time sentiu que travou, feedbacks internos..." />

            <label style={labelStyle}>
              Anexo <span style={{ fontWeight: 400, color: "#9696a0" }}>(opcional) — ex: Tactiq da reunião, ata externa</span>
            </label>
            <input ref={fileRef} type="file" accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setAnexoName(e.target.files?.[0]?.name ?? null)} />
            {anexoName && <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Anexo: {anexoName}</div>}

            {error && <div style={{ marginTop: 14, padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, fontSize: 13 }}>{error}</div>}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={() => { setError(null); setStep("input"); }} disabled={submitting}>Voltar</button>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={submitting}>Cancelar</button>
              <button type="button" style={{ ...primaryBtn, opacity: submitting ? 0.6 : 1 }} onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Gerando…" : "Gerar Retrospectiva"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
