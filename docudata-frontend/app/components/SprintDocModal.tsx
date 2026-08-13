"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  submitPlanning,
  submitDaily,
  submitReview,
  enrichContent,
  ValidationError,
  type ValidationError422,
  type SprintDocResponse,
  type SprintDocType,
  type EnrichResult,
} from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmitted?: (response: SprintDocResponse) => void;
  tipo: SprintDocType;
  projetoId: string;
  sprintNumero: number;
  initialCarryOver?: string;
}

const TITLES: Record<SprintDocType, string> = {
  planning: "Adicionar Planning",
  daily: "Adicionar Daily",
  review: "Adicionar Review",
};

const overlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: 16,
};

const modalStyle: CSSProperties = {
  background: "#fff",
  borderRadius: 12,
  width: "100%",
  maxWidth: 560,
  maxHeight: "90vh",
  overflowY: "auto",
  padding: 24,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const labelStyle: CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 600,
  color: "#334155",
  marginBottom: 6,
  marginTop: 14,
};

const inputStyle: CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "8px 10px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
};

const textareaStyle: CSSProperties = {
  ...inputStyle,
  resize: "vertical",
  minHeight: 80,
  fontFamily: "inherit",
};

const primaryBtn: CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 700,
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: CSSProperties = {
  background: "#f7f7fa",
  color: "#475569",
  border: "1px solid #e2e8f0",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

const aiBadgeStyle: CSSProperties = {
  fontSize: 11,
  background: "#eff6ff",
  color: "#2563eb",
  border: "1px solid #bfdbfe",
  borderRadius: 4,
  padding: "1px 6px",
  marginLeft: 6,
  fontWeight: 500,
};

export default function SprintDocModal({
  open,
  onClose,
  onSubmitted,
  tipo,
  projetoId,
  sprintNumero,
  initialCarryOver,
}: Props) {
  // Enrichment step state
  const [step, setStep] = useState<"input" | "form">("input");
  const [enrichText, setEnrichText] = useState("");
  const enrichFileRef = useRef<HTMLInputElement | null>(null);
  const [enrichFileName, setEnrichFileName] = useState<string | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [aiFields, setAiFields] = useState<Set<string>>(new Set());

  // Form state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErr, setValidationErr] = useState<ValidationError422 | null>(null);

  // Planning state
  const [descricao, setDescricao] = useState("");
  const [itens, setItens] = useState<{ item: string; responsavel: string; prazo: string; criterio: string }[]>([
    { item: "", responsavel: "", prazo: "", criterio: "" },
  ]);
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFim, setPeriodoFim] = useState("");
  const [horasDisponiveis, setHorasDisponiveis] = useState<number | "">("");
  const [horasEstimadas, setHorasEstimadas] = useState<number | "">("");
  const [dependencias, setDependencias] = useState<{ item: string; prazo: string; consequencia: string; confianca: string }[]>([
    { item: "", prazo: "", consequencia: "", confianca: "" },
  ]);
  const [riscos, setRiscos] = useState<{ risco: string; consequencia: string }[]>([
    { risco: "", consequencia: "" },
  ]);
  const [carryOverItems, setCarryOverItems] = useState<{ item: string; causa_raiz: string }[]>([
    { item: "", causa_raiz: "" },
  ]);

  // Daily state
  const today = new Date().toISOString().slice(0, 10);
  const [data, setData] = useState(today);
  const [feito, setFeito] = useState("");
  const [proximo, setProximo] = useState("");
  const [impedimentos, setImpedimentos] = useState("");

  // Review state — campos base
  const [observacoes, setObservacoes] = useState("");
  const [percepcaoCliente, setPercepcaoCliente] = useState("");
  const [sinalSatisfacao, setSinalSatisfacao] = useState("");
  const [pedidosForaEscopo, setPedidosForaEscopo] = useState("");
  // Review state — Template 2 CITi
  const [reviewSquad, setReviewSquad] = useState("");
  const [reviewPeriodoInicio, setReviewPeriodoInicio] = useState("");
  const [reviewPeriodoFim, setReviewPeriodoFim] = useState("");
  const [reviewSubarea, setReviewSubarea] = useState("");
  const [itensPlanejadasEntregues, setItensPlanejadasEntregues] = useState<
    { item: string; entregue: string; motivo_nao: string; causa_raiz_num: string }[]
  >([{ item: "", entregue: "", motivo_nao: "", causa_raiz_num: "" }]);
  const [percentualItensProntos, setPercentualItensProntos] = useState("");
  const [pedidosForaEscopoItens, setPedidosForaEscopoItens] = useState<
    { data: string; descricao: string; status: string }[]
  >([{ data: "", descricao: "", status: "" }]);
  const [itensProximaSprint, setItensProximaSprint] = useState<
    { item: string; causa_raiz_num: string }[]
  >([{ item: "", causa_raiz_num: "" }]);

  // Common
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [anexoName, setAnexoName] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setStep("input");
      setEnrichText("");
      setEnrichFileName(null);
      setEnriching(false);
      setAiFields(new Set());
      setSubmitting(false);
      setError(null);
      setValidationErr(null);
      setDescricao("");
      setItens([{ item: "", responsavel: "", prazo: "", criterio: "" }]);
      setPeriodoInicio("");
      setPeriodoFim("");
      setHorasDisponiveis("");
      setHorasEstimadas("");
      setDependencias([{ item: "", prazo: "", consequencia: "", confianca: "" }]);
      setRiscos([{ risco: "", consequencia: "" }]);
      setCarryOverItems([{ item: "", causa_raiz: "" }]);
      setData(today);
      setFeito("");
      setProximo("");
      setImpedimentos("");
      setObservacoes("");
      setPercepcaoCliente("");
      setSinalSatisfacao("");
      setPedidosForaEscopo("");
      setReviewSquad("");
      setReviewPeriodoInicio("");
      setReviewPeriodoFim("");
      setReviewSubarea("");
      setItensPlanejadasEntregues([{ item: "", entregue: "", motivo_nao: "", causa_raiz_num: "" }]);
      setPercentualItensProntos("");
      setPedidosForaEscopoItens([{ data: "", descricao: "", status: "" }]);
      setItensProximaSprint([{ item: "", causa_raiz_num: "" }]);
      setAnexoName(null);
      if (fileRef.current) fileRef.current.value = "";
      if (enrichFileRef.current) enrichFileRef.current.value = "";
    } else {
      if (initialCarryOver) {
        const lines = initialCarryOver.split("\n").filter(Boolean);
        setCarryOverItems(lines.length ? lines.map((l) => ({ item: l, causa_raiz: "" })) : [{ item: "", causa_raiz: "" }]);
      }
    }
  }, [open, today, initialCarryOver]);

  if (!open) return null;

  const AiBadge = ({ field }: { field: string }) =>
    aiFields.has(field) ? <span style={aiBadgeStyle}>IA</span> : null;

  const applyEnrichResult = (result: EnrichResult, fields: Set<string>) => {
    if (tipo === "planning") {
      if (result.descricao) { setDescricao(result.descricao); fields.add("descricao"); }
      if (result.itens_backlog?.length) {
        setItens(result.itens_backlog.map((i) => ({
          item: i.item || "",
          responsavel: i.responsavel || "",
          prazo: i.prazo || "",
          criterio: i.criterio || "",
        })));
        fields.add("itens_backlog");
      }
      if (result.horas_disponiveis != null) { setHorasDisponiveis(result.horas_disponiveis); fields.add("horas_disponiveis"); }
      if (result.horas_estimadas != null) { setHorasEstimadas(result.horas_estimadas); fields.add("horas_estimadas"); }
      const toInputDate = (s: string) => {
        const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        return m ? `${m[3]}-${m[2]}-${m[1]}` : s;
      };
      if (result.periodo_inicio) { setPeriodoInicio(toInputDate(result.periodo_inicio)); fields.add("periodo"); }
      if (result.periodo_fim) { setPeriodoFim(toInputDate(result.periodo_fim)); fields.add("periodo"); }
      if (result.dependencias_items?.length) {
        setDependencias(result.dependencias_items.map((d) => ({
          item: d.item || "", prazo: d.prazo || "", consequencia: d.consequencia || "", confianca: d.confianca || "",
        })));
        fields.add("dependencias");
      }
      if (result.riscos_items?.length) {
        setRiscos(result.riscos_items.map((r) => ({ risco: r.risco || "", consequencia: r.consequencia || "" })));
        fields.add("riscos");
      }
      if (result.carry_over_items?.length) {
        setCarryOverItems(result.carry_over_items.map((c) => ({ item: c.item || "", causa_raiz: c.causa_raiz || "" })));
        fields.add("carryOver");
      }
    } else if (tipo === "daily") {
      if (result.feito) { setFeito(result.feito); fields.add("feito"); }
      if (result.proximo) { setProximo(result.proximo); fields.add("proximo"); }
      if (result.impedimentos) { setImpedimentos(result.impedimentos); fields.add("impedimentos"); }
      if (result.data) { setData(result.data); fields.add("data"); }
    } else {
      if (result.observacoes) { setObservacoes(result.observacoes); fields.add("observacoes"); }
      if (result.percepcao_cliente) { setPercepcaoCliente(result.percepcao_cliente); fields.add("percepcaoCliente"); }
      if (result.sinal_satisfacao) { setSinalSatisfacao(result.sinal_satisfacao); fields.add("sinalSatisfacao"); }
      if (result.pedidos_fora_escopo) { setPedidosForaEscopo(result.pedidos_fora_escopo); fields.add("pedidosForaEscopo"); }
      if (result.squad) { setReviewSquad(result.squad); fields.add("reviewSquad"); }
      if (result.subarea) { setReviewSubarea(result.subarea); fields.add("reviewSubarea"); }
      const toDate = (s: string) => { const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/); return m ? `${m[3]}-${m[2]}-${m[1]}` : s; };
      if (result.periodo_inicio) { setReviewPeriodoInicio(toDate(result.periodo_inicio)); fields.add("reviewPeriodo"); }
      if (result.periodo_fim) { setReviewPeriodoFim(toDate(result.periodo_fim)); fields.add("reviewPeriodo"); }
      if (result.itens_planejados_entregues?.length) { setItensPlanejadasEntregues(result.itens_planejados_entregues); fields.add("itensEntregues"); }
      if (result.percentual_itens_prontos) { setPercentualItensProntos(result.percentual_itens_prontos); fields.add("percentual"); }
      if (result.pedidos_fora_escopo_itens?.length) { setPedidosForaEscopoItens(result.pedidos_fora_escopo_itens); fields.add("pedidosItens"); }
      if (result.itens_proxima_sprint?.length) { setItensProximaSprint(result.itens_proxima_sprint); fields.add("itensProxima"); }
    }
  };

  const handleEnrich = async () => {
    setEnriching(true);
    setError(null);
    const arquivo = enrichFileRef.current?.files?.[0] ?? null;
    try {
      const result = await enrichContent({
        projetoId,
        docType: tipo,
        texto: enrichText.trim() || undefined,
        arquivo: arquivo || undefined,
      });
      const newAiFields = new Set<string>();
      applyEnrichResult(result, newAiFields);
      setAiFields(newAiFields);
      setStep("form");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao analisar conteúdo");
    } finally {
      setEnriching(false);
    }
  };

  const handleSubmit = async (force = false) => {
    setSubmitting(true);
    setError(null);
    setValidationErr(null);
    const anexo = fileRef.current?.files?.[0] ?? null;
    try {
      let response: SprintDocResponse;
      if (tipo === "planning") {
        const cleanItens = itens.filter((i) => i.item.trim());
        if (!descricao.trim()) throw new Error("Descrição é obrigatória");
        response = await submitPlanning({
          projetoId,
          sprintNumero,
          descricao,
          itensBacklog: cleanItens,
          periodoInicio: periodoInicio || undefined,
          periodoFim: periodoFim || undefined,
          horasDisponiveis: horasDisponiveis !== "" ? horasDisponiveis : undefined,
          horasEstimadas: horasEstimadas !== "" ? horasEstimadas : undefined,
          dependenciasItems: dependencias.filter((d) => d.item.trim()),
          riscosItems: riscos.filter((r) => r.risco.trim()),
          carryOverItems: carryOverItems.filter((c) => c.item.trim()),
          anexo,
          force,
        });
      } else if (tipo === "daily") {
        if (!feito.trim() || !proximo.trim())
          throw new Error("Preencha 'O que foi feito' e 'O que será feito'");
        response = await submitDaily({
          projetoId,
          sprintNumero,
          data,
          feito,
          proximo,
          impedimentos: impedimentos || undefined,
          anexo,
          force,
        });
      } else {
        const cleanIPE = itensPlanejadasEntregues.filter((i) => i.item.trim());
        const cleanPFE = pedidosForaEscopoItens.filter((i) => i.descricao.trim());
        const cleanIPS = itensProximaSprint.filter((i) => i.item.trim());
        response = await submitReview({
          projetoId,
          sprintNumero,
          observacoes: observacoes || undefined,
          percepcaoCliente: percepcaoCliente || undefined,
          sinalSatisfacao: sinalSatisfacao || undefined,
          pedidosForaEscopo: pedidosForaEscopo || undefined,
          squad: reviewSquad || undefined,
          periodoInicio: reviewPeriodoInicio || undefined,
          periodoFim: reviewPeriodoFim || undefined,
          subarea: reviewSubarea || undefined,
          itensPlanejadasEntregues: cleanIPE.length ? cleanIPE : undefined,
          percentualItensProntos: percentualItensProntos || undefined,
          pedidosForaEscopoItens: cleanPFE.length ? cleanPFE : undefined,
          itensProximaSprint: cleanIPS.length ? cleanIPS : undefined,
          anexo,
          force,
        });
      }
      onSubmitted?.(response);
      onClose();
    } catch (e) {
      if (e instanceof ValidationError) {
        setValidationErr(e.detail);
      } else {
        setError(e instanceof Error ? e.message : "Erro ao submeter");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
            {TITLES[tipo]} — Sprint {sprintNumero}
          </h2>
          {step === "form" && (
            <span style={{ fontSize: 12, color: "#64748b" }}>
              Etapa 2 de 2 — Revise e confirme
            </span>
          )}
        </div>

        {/* ── ETAPA 1: Forneça a matéria-prima ─────────────────────────── */}
        {step === "input" && (
          <>
            <p style={{ fontSize: 13, color: "#64748b", marginTop: 12, marginBottom: 0 }}>
              Cole a matéria-prima abaixo ou faça upload de um arquivo. A IA vai preencher
              os campos automaticamente para você revisar antes de gerar o documento.
            </p>

            <label style={labelStyle}>Texto (cole aqui)</label>
            <textarea
              style={{ ...textareaStyle, minHeight: 160 }}
              value={enrichText}
              onChange={(e) => setEnrichText(e.target.value)}
              placeholder={
                tipo === "planning"
                  ? "Ex: pauta de reunião, lista de tarefas do Planner, documento de escopo..."
                  : tipo === "daily"
                  ? "Ex: atualização no WhatsApp, mensagem de status, notas da daily..."
                  : tipo === "review"
                  ? "Ex: transcrição da reunião de review, anotações de feedback do cliente..."
                  : "Cole aqui a matéria-prima..."
              }
            />

            <label style={labelStyle}>Ou faça upload de arquivo</label>
            <input
              ref={enrichFileRef}
              type="file"
              accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setEnrichFileName(e.target.files?.[0]?.name ?? null)}
            />
            {enrichFileName && (
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                Arquivo: {enrichFileName}
              </div>
            )}

            {error && (
              <div style={{ marginTop: 14, padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, fontSize: 13 }}>
                {error}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={enriching}>
                Cancelar
              </button>
              <button
                type="button"
                style={ghostBtn}
                onClick={() => { setError(null); setStep("form"); }}
                disabled={enriching}
              >
                Preencher manualmente
              </button>
              <button
                type="button"
                style={{ ...primaryBtn, opacity: enriching || (!enrichText.trim() && !enrichFileName) ? 0.6 : 1 }}
                onClick={handleEnrich}
                disabled={enriching || (!enrichText.trim() && !enrichFileName)}
              >
                {enriching ? "Analisando..." : "Analisar com IA"}
              </button>
            </div>
          </>
        )}

        {/* ── ETAPA 2: Formulário (pre-preenchido ou manual) ─────────────── */}
        {step === "form" && (
          <>
            {aiFields.size > 0 && (
              <div style={{
                marginTop: 12,
                padding: "8px 12px",
                background: "#eff6ff",
                border: "1px solid #bfdbfe",
                borderRadius: 8,
                fontSize: 13,
                color: "#1e40af",
              }}>
                Campos marcados com <strong>IA</strong> foram preenchidos automaticamente — revise antes de confirmar.
              </div>
            )}

            {tipo === "planning" && (
              <>
                <label style={labelStyle}>
                  Descrição do planejamento
                  <AiBadge field="descricao" />
                </label>
                <textarea
                  style={textareaStyle}
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="Ex: Sprint focada em finalizar o ETL e iniciar a camada de visualização"
                />

                <label style={labelStyle}>
                  Itens do backlog
                  <AiBadge field="itens_backlog" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 80px 2fr auto", gap: 6, marginBottom: 4 }}>
                  {["Tarefa", "Responsável", "Prazo", "Critério de pronto", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {itens.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 80px 2fr auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.item} placeholder={`Item ${idx + 1}`}
                      onChange={(e) => { const n = [...itens]; n[idx] = { ...n[idx], item: e.target.value }; setItens(n); }} />
                    <input style={inputStyle} value={row.responsavel} placeholder="Ex: Gabriel"
                      onChange={(e) => { const n = [...itens]; n[idx] = { ...n[idx], responsavel: e.target.value }; setItens(n); }} />
                    <input style={inputStyle} value={row.prazo} placeholder="15/08"
                      onChange={(e) => { const n = [...itens]; n[idx] = { ...n[idx], prazo: e.target.value }; setItens(n); }} />
                    <input style={inputStyle} value={row.criterio} placeholder="Ex: PR aprovado"
                      onChange={(e) => { const n = [...itens]; n[idx] = { ...n[idx], criterio: e.target.value }; setItens(n); }} />
                    {itens.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setItens(itens.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setItens([...itens, { item: "", responsavel: "", prazo: "", criterio: "" }])}>
                  + Adicionar item
                </button>

                <label style={labelStyle}>
                  Período da sprint
                  <AiBadge field="periodo" />
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input type="date" style={{ ...inputStyle, flex: 1 }} value={periodoInicio}
                    onChange={(e) => setPeriodoInicio(e.target.value)} />
                  <input type="date" style={{ ...inputStyle, flex: 1 }} value={periodoFim}
                    onChange={(e) => setPeriodoFim(e.target.value)} />
                </div>

                <label style={labelStyle}>
                  Capacidade vs. Estimativa
                  <AiBadge field="horas_disponiveis" />
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input type="number" min={0} style={{ ...inputStyle, flex: 1 }} value={horasDisponiveis}
                    onChange={(e) => setHorasDisponiveis(e.target.value ? Number(e.target.value) : "")}
                    placeholder="Horas disponíveis" />
                  <input type="number" min={0} style={{ ...inputStyle, flex: 1 }} value={horasEstimadas}
                    onChange={(e) => setHorasEstimadas(e.target.value ? Number(e.target.value) : "")}
                    placeholder="Horas estimadas" />
                </div>

                <label style={labelStyle}>
                  Dependências do cliente
                  <AiBadge field="dependencias" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "2fr 80px 2fr 100px auto", gap: 6, marginBottom: 4 }}>
                  {["O que precisa entregar", "Prazo", "Consequência se atrasar", "Confiança", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {dependencias.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "2fr 80px 2fr 100px auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.item} placeholder="Ex: Acesso ao banco"
                      onChange={(e) => { const n = [...dependencias]; n[idx] = { ...n[idx], item: e.target.value }; setDependencias(n); }} />
                    <input style={inputStyle} value={row.prazo} placeholder="15/08"
                      onChange={(e) => { const n = [...dependencias]; n[idx] = { ...n[idx], prazo: e.target.value }; setDependencias(n); }} />
                    <input style={inputStyle} value={row.consequencia} placeholder="Ex: Sprint atrasada"
                      onChange={(e) => { const n = [...dependencias]; n[idx] = { ...n[idx], consequencia: e.target.value }; setDependencias(n); }} />
                    <select style={{ ...inputStyle, cursor: "pointer" }} value={row.confianca}
                      onChange={(e) => { const n = [...dependencias]; n[idx] = { ...n[idx], confianca: e.target.value }; setDependencias(n); }}>
                      <option value="">—</option>
                      <option value="Alta">Alta</option>
                      <option value="Média">Média</option>
                      <option value="Baixa">Baixa</option>
                    </select>
                    {dependencias.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setDependencias(dependencias.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setDependencias([...dependencias, { item: "", prazo: "", consequencia: "", confianca: "" }])}>
                  + Adicionar dependência
                </button>

                <label style={labelStyle}>
                  Riscos identificados
                  <AiBadge field="riscos" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr auto", gap: 6, marginBottom: 4 }}>
                  {["O que pode dar errado", "Consequência se acontecer", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {riscos.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "2fr 2fr auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.risco} placeholder="Ex: Atraso no dado do cliente"
                      onChange={(e) => { const n = [...riscos]; n[idx] = { ...n[idx], risco: e.target.value }; setRiscos(n); }} />
                    <input style={inputStyle} value={row.consequencia} placeholder="Ex: Sprint comprometida"
                      onChange={(e) => { const n = [...riscos]; n[idx] = { ...n[idx], consequencia: e.target.value }; setRiscos(n); }} />
                    {riscos.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setRiscos(riscos.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setRiscos([...riscos, { risco: "", consequencia: "" }])}>
                  + Adicionar risco
                </button>

                <label style={labelStyle}>
                  Carry-over da sprint anterior
                  <AiBadge field="carryOver" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "3fr 80px auto", gap: 6, marginBottom: 4 }}>
                  {["Item pendente", "Causa raiz (nº)", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {carryOverItems.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "3fr 80px auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.item} placeholder="Ex: Integração com API do cliente"
                      onChange={(e) => { const n = [...carryOverItems]; n[idx] = { ...n[idx], item: e.target.value }; setCarryOverItems(n); }} />
                    <input style={inputStyle} value={row.causa_raiz} placeholder="1–7"
                      onChange={(e) => { const n = [...carryOverItems]; n[idx] = { ...n[idx], causa_raiz: e.target.value }; setCarryOverItems(n); }} />
                    {carryOverItems.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setCarryOverItems(carryOverItems.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setCarryOverItems([...carryOverItems, { item: "", causa_raiz: "" }])}>
                  + Adicionar item
                </button>
              </>
            )}

            {tipo === "daily" && (
              <>
                <label style={labelStyle}>
                  Data
                  <AiBadge field="data" />
                </label>
                <input type="date" style={inputStyle} value={data} onChange={(e) => setData(e.target.value)} />

                <label style={labelStyle}>
                  O que foi feito desde a última Daily?
                  <AiBadge field="feito" />
                </label>
                <textarea style={textareaStyle} value={feito} onChange={(e) => setFeito(e.target.value)} />

                <label style={labelStyle}>
                  O que será feito até a próxima Daily?
                  <AiBadge field="proximo" />
                </label>
                <textarea style={textareaStyle} value={proximo} onChange={(e) => setProximo(e.target.value)} />

                <label style={labelStyle}>
                  Existe algum impedimento ou risco?
                  <AiBadge field="impedimentos" />
                </label>
                <textarea style={textareaStyle} value={impedimentos} onChange={(e) => setImpedimentos(e.target.value)} placeholder="Opcional" />
              </>
            )}

            {tipo === "review" && (
              <>
                <label style={labelStyle}>
                  Observações do gerente sobre a sprint
                  <AiBadge field="observacoes" />
                </label>
                <textarea
                  style={{ ...textareaStyle, minHeight: 120 }}
                  value={observacoes}
                  onChange={(e) => setObservacoes(e.target.value)}
                  placeholder="Opcional — observações qualitativas. O delta planejado vs realizado será calculado automaticamente."
                />

                <label style={labelStyle}>
                  Percepção do cliente
                  <AiBadge field="percepcaoCliente" />
                </label>
                <textarea style={textareaStyle} value={percepcaoCliente}
                  onChange={(e) => setPercepcaoCliente(e.target.value)}
                  placeholder="Ex: Cliente satisfeito com a velocidade de entrega" />

                <label style={labelStyle}>
                  Sinal de satisfação
                  <AiBadge field="sinalSatisfacao" />
                </label>
                <select style={{ ...inputStyle, cursor: "pointer" }} value={sinalSatisfacao}
                  onChange={(e) => setSinalSatisfacao(e.target.value)}>
                  <option value="">Selecione...</option>
                  <option value="Elogio espontâneo">Elogio espontâneo</option>
                  <option value="Neutro / sem sinal">Neutro / sem sinal</option>
                  <option value="Reclamação pontual, resolvida na própria Review">Reclamação pontual, resolvida na própria Review</option>
                  <option value="Reclamação não resolvida ao final da Review">Reclamação não resolvida ao final da Review</option>
                  <option value="Reclamação recorrente sobre o mesmo tema (2ª vez)">Reclamação recorrente sobre o mesmo tema (2ª vez)</option>
                  <option value="Cliente solicitou reunião de escalonamento">Cliente solicitou reunião de escalonamento</option>
                </select>

                <label style={labelStyle}>
                  Pedidos fora do escopo (texto livre)
                  <AiBadge field="pedidosForaEscopo" />
                </label>
                <textarea style={textareaStyle} value={pedidosForaEscopo}
                  onChange={(e) => setPedidosForaEscopo(e.target.value)}
                  placeholder="Ex: Cliente solicitou relatório PDF — registrado para avaliação" />

                <label style={labelStyle}>
                  Squad (membros e papéis)
                  <AiBadge field="reviewSquad" />
                </label>
                <input style={inputStyle} value={reviewSquad} onChange={(e) => setReviewSquad(e.target.value)}
                  placeholder="Ex: Gabriel (Gerente), Ana (Analista), João (Analista)" />

                <label style={labelStyle}>
                  Período da sprint
                  <AiBadge field="reviewPeriodo" />
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input type="date" style={{ ...inputStyle, flex: 1 }} value={reviewPeriodoInicio} onChange={(e) => setReviewPeriodoInicio(e.target.value)} />
                  <input type="date" style={{ ...inputStyle, flex: 1 }} value={reviewPeriodoFim} onChange={(e) => setReviewPeriodoFim(e.target.value)} />
                </div>

                <label style={labelStyle}>Subárea</label>
                <select style={{ ...inputStyle, cursor: "pointer" }} value={reviewSubarea} onChange={(e) => setReviewSubarea(e.target.value)}>
                  <option value="">Selecione...</option>
                  <option value="dados">Dados</option>
                  <option value="desenvolvimento">Desenvolvimento</option>
                  <option value="produto">Produto</option>
                </select>

                <label style={labelStyle}>
                  Planejado vs Entregue
                  <AiBadge field="itensEntregues" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "3fr 60px 2fr 80px auto", gap: 6, marginBottom: 4 }}>
                  {["Item", "Entregue", "Motivo se não", "Causa raiz", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {itensPlanejadasEntregues.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "3fr 60px 2fr 80px auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.item} placeholder={`Item ${idx + 1}`}
                      onChange={(e) => { const n = [...itensPlanejadasEntregues]; n[idx] = { ...n[idx], item: e.target.value }; setItensPlanejadasEntregues(n); }} />
                    <select style={{ ...inputStyle, cursor: "pointer" }} value={row.entregue}
                      onChange={(e) => { const n = [...itensPlanejadasEntregues]; n[idx] = { ...n[idx], entregue: e.target.value }; setItensPlanejadasEntregues(n); }}>
                      <option value="">—</option>
                      <option value="S">S</option>
                      <option value="N">N</option>
                    </select>
                    <input style={inputStyle} value={row.motivo_nao} placeholder="Motivo se N"
                      onChange={(e) => { const n = [...itensPlanejadasEntregues]; n[idx] = { ...n[idx], motivo_nao: e.target.value }; setItensPlanejadasEntregues(n); }} />
                    <input style={inputStyle} value={row.causa_raiz_num} placeholder="1–7"
                      onChange={(e) => { const n = [...itensPlanejadasEntregues]; n[idx] = { ...n[idx], causa_raiz_num: e.target.value }; setItensPlanejadasEntregues(n); }} />
                    {itensPlanejadasEntregues.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setItensPlanejadasEntregues(itensPlanejadasEntregues.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setItensPlanejadasEntregues([...itensPlanejadasEntregues, { item: "", entregue: "", motivo_nao: "", causa_raiz_num: "" }])}>
                  + Adicionar item
                </button>

                <label style={labelStyle}>
                  % de itens com Pronto cumprido
                  <AiBadge field="percentual" />
                </label>
                <input style={inputStyle} value={percentualItensProntos} onChange={(e) => setPercentualItensProntos(e.target.value)}
                  placeholder="Ex: 8 de 10 = 80%" />

                <label style={labelStyle}>
                  Pedidos fora do escopo (tabela)
                  <AiBadge field="pedidosItens" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "80px 3fr 2fr auto", gap: 6, marginBottom: 4 }}>
                  {["Data", "Descrição do pedido", "Insistência ou sugestão", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {pedidosForaEscopoItens.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "80px 3fr 2fr auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.data} placeholder="DD/MM"
                      onChange={(e) => { const n = [...pedidosForaEscopoItens]; n[idx] = { ...n[idx], data: e.target.value }; setPedidosForaEscopoItens(n); }} />
                    <input style={inputStyle} value={row.descricao} placeholder="Ex: Relatório PDF"
                      onChange={(e) => { const n = [...pedidosForaEscopoItens]; n[idx] = { ...n[idx], descricao: e.target.value }; setPedidosForaEscopoItens(n); }} />
                    <select style={{ ...inputStyle, cursor: "pointer" }} value={row.status}
                      onChange={(e) => { const n = [...pedidosForaEscopoItens]; n[idx] = { ...n[idx], status: e.target.value }; setPedidosForaEscopoItens(n); }}>
                      <option value="">—</option>
                      <option value="Insistência">Insistência</option>
                      <option value="Sugestão pontual">Sugestão pontual</option>
                    </select>
                    {pedidosForaEscopoItens.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setPedidosForaEscopoItens(pedidosForaEscopoItens.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setPedidosForaEscopoItens([...pedidosForaEscopoItens, { data: "", descricao: "", status: "" }])}>
                  + Adicionar pedido
                </button>

                <label style={labelStyle}>
                  Itens para a próxima sprint
                  <AiBadge field="itensProxima" />
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "3fr 80px auto", gap: 6, marginBottom: 4 }}>
                  {["Item pendente", "Causa raiz (nº)", ""].map((h, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>{h}</span>
                  ))}
                </div>
                {itensProximaSprint.map((row, idx) => (
                  <div key={idx} style={{ display: "grid", gridTemplateColumns: "3fr 80px auto", gap: 6, marginBottom: 6 }}>
                    <input style={inputStyle} value={row.item} placeholder="Ex: Integração com API"
                      onChange={(e) => { const n = [...itensProximaSprint]; n[idx] = { ...n[idx], item: e.target.value }; setItensProximaSprint(n); }} />
                    <input style={inputStyle} value={row.causa_raiz_num} placeholder="1–7"
                      onChange={(e) => { const n = [...itensProximaSprint]; n[idx] = { ...n[idx], causa_raiz_num: e.target.value }; setItensProximaSprint(n); }} />
                    {itensProximaSprint.length > 1 && (
                      <button type="button" style={ghostBtn} onClick={() => setItensProximaSprint(itensProximaSprint.filter((_, i) => i !== idx))}>−</button>
                    )}
                  </div>
                ))}
                <button type="button" style={{ ...ghostBtn, marginTop: 4 }}
                  onClick={() => setItensProximaSprint([...itensProximaSprint, { item: "", causa_raiz_num: "" }])}>
                  + Adicionar item
                </button>
              </>
            )}

            <label style={labelStyle}>
              Anexo (opcional)
              {tipo === "planning" && (
                <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 6 }}>
                  — PDF ou print do kanban
                </span>
              )}
              {tipo !== "planning" && (
                <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 6 }}>— PDF</span>
              )}
            </label>
            <input
              ref={fileRef}
              type="file"
              accept={tipo === "planning" ? "application/pdf,image/png,image/jpeg,image/jpg,image/webp" : "application/pdf"}
              onChange={(e) => setAnexoName(e.target.files?.[0]?.name ?? null)}
            />
            {anexoName && (
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Anexo: {anexoName}</div>
            )}

            {validationErr && (
              <div style={{ marginTop: 14, padding: 12, background: "#fffbeb", border: "1px solid #fde68a", color: "#92400e", borderRadius: 8, fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Tipo de conteúdo diferente do esperado</div>
                <div>{validationErr.mensagem}</div>
                <div style={{ marginTop: 10, display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button type="button" style={ghostBtn} onClick={() => setValidationErr(null)} disabled={submitting}>
                    Cancelar
                  </button>
                  <button
                    type="button"
                    style={{ ...primaryBtn, background: "#f59e0b", color: "#1c1917", opacity: submitting ? 0.6 : 1 }}
                    onClick={() => handleSubmit(true)}
                    disabled={submitting}
                  >
                    {submitting ? "Gerando…" : "Ingerir mesmo assim"}
                  </button>
                </div>
              </div>
            )}

            {error && (
              <div style={{ marginTop: 14, padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, fontSize: 13 }}>
                {error}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={() => { setError(null); setValidationErr(null); setStep("input"); }} disabled={submitting}>
                Voltar
              </button>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={submitting}>
                Cancelar
              </button>
              <button
                type="button"
                style={{ ...primaryBtn, opacity: submitting ? 0.6 : 1 }}
                onClick={() => handleSubmit()}
                disabled={submitting}
              >
                {submitting ? "Gerando…" : `Gerar ${tipo === "planning" ? "Planning" : tipo === "daily" ? "Daily" : "Review"}`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
