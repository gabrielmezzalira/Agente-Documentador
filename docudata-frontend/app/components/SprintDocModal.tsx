"use client";

import { useEffect, useRef, useState } from "react";
import {
  submitPlanning,
  submitDaily,
  submitReview,
  type SprintDocResponse,
  type SprintDocType,
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
  maxWidth: 560,
  maxHeight: "90vh",
  overflowY: "auto",
  padding: 24,
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
  padding: "8px 10px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  resize: "vertical",
  minHeight: 80,
  fontFamily: "inherit",
};

const primaryBtn: React.CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 700,
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: React.CSSProperties = {
  background: "#f7f7fa",
  color: "#475569",
  border: "1px solid #e2e8f0",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
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
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Planning state
  const [descricao, setDescricao] = useState("");
  const [itens, setItens] = useState<{ item: string; prazo: string; criterio: string }[]>([
    { item: "", prazo: "", criterio: "" },
  ]);
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFim, setPeriodoFim] = useState("");
  const [horasDisponiveis, setHorasDisponiveis] = useState<number | "">("");
  const [horasEstimadas, setHorasEstimadas] = useState<number | "">("");
  const [dependenciasCliente, setDependenciasCliente] = useState("");
  const [carryOver, setCarryOver] = useState("");

  // Daily state
  const today = new Date().toISOString().slice(0, 10);
  const [data, setData] = useState(today);
  const [feito, setFeito] = useState("");
  const [proximo, setProximo] = useState("");
  const [impedimentos, setImpedimentos] = useState("");

  // Review state
  const [observacoes, setObservacoes] = useState("");
  const [percepcaoCliente, setPercepcaoCliente] = useState("");
  const [sinalSatisfacao, setSinalSatisfacao] = useState("");
  const [pedidosForaEscopo, setPedidosForaEscopo] = useState("");

  // Common
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [anexoName, setAnexoName] = useState<string | null>(null);

  // Reset on close / pre-fill on open
  useEffect(() => {
    if (!open) {
      setSubmitting(false);
      setError(null);
      setDescricao("");
      setItens([{ item: "", prazo: "", criterio: "" }]);
      setPeriodoInicio("");
      setPeriodoFim("");
      setHorasDisponiveis("");
      setHorasEstimadas("");
      setDependenciasCliente("");
      setCarryOver("");
      setData(today);
      setFeito("");
      setProximo("");
      setImpedimentos("");
      setObservacoes("");
      setPercepcaoCliente("");
      setSinalSatisfacao("");
      setPedidosForaEscopo("");
      setAnexoName(null);
      if (fileRef.current) fileRef.current.value = "";
    } else {
      // Pre-fill carry-over when opening planning modal
      setCarryOver(initialCarryOver ?? "");
    }
  }, [open, today, initialCarryOver]);

  if (!open) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
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
          dependenciasCliente: dependenciasCliente || undefined,
          carryOver: carryOver || undefined,
          anexo,
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
        });
      } else {
        response = await submitReview({
          projetoId,
          sprintNumero,
          observacoes: observacoes || undefined,
          percepcaoCliente: percepcaoCliente || undefined,
          sinalSatisfacao: sinalSatisfacao || undefined,
          pedidosForaEscopo: pedidosForaEscopo || undefined,
          anexo,
        });
      }
      onSubmitted?.(response);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao submeter");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
          {TITLES[tipo]} — Sprint {sprintNumero}
        </h2>

        {tipo === "planning" && (
          <>
            <label style={labelStyle}>Descrição do planejamento</label>
            <textarea
              style={textareaStyle}
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Ex: Sprint focada em finalizar o ETL e iniciar a camada de visualização"
            />
            <label style={labelStyle}>Itens do backlog</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 1fr auto", gap: 6, marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>Tarefa</span>
              <span style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>Prazo</span>
              <span style={{ fontSize: 11, color: "#9696a0", fontWeight: 600 }}>Critério de pronto</span>
              <span />
            </div>
            {itens.map((row, idx) => (
              <div key={idx} style={{ display: "grid", gridTemplateColumns: "1fr 100px 1fr auto", gap: 6, marginBottom: 6 }}>
                <input
                  style={inputStyle}
                  value={row.item}
                  onChange={(e) => {
                    const next = [...itens];
                    next[idx] = { ...next[idx], item: e.target.value };
                    setItens(next);
                  }}
                  placeholder={`Item ${idx + 1}`}
                />
                <input
                  style={inputStyle}
                  value={row.prazo}
                  onChange={(e) => {
                    const next = [...itens];
                    next[idx] = { ...next[idx], prazo: e.target.value };
                    setItens(next);
                  }}
                  placeholder="Ex: 15/08"
                />
                <input
                  style={inputStyle}
                  value={row.criterio}
                  onChange={(e) => {
                    const next = [...itens];
                    next[idx] = { ...next[idx], criterio: e.target.value };
                    setItens(next);
                  }}
                  placeholder="Ex: PR aprovado e deploy feito"
                />
                {itens.length > 1 && (
                  <button
                    type="button"
                    style={ghostBtn}
                    onClick={() => setItens(itens.filter((_, i) => i !== idx))}
                  >
                    −
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              style={{ ...ghostBtn, marginTop: 4 }}
              onClick={() => setItens([...itens, { item: "", prazo: "", criterio: "" }])}
            >
              + Adicionar item
            </button>

            <label style={labelStyle}>Período da sprint</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="date"
                style={{ ...inputStyle, flex: 1 }}
                value={periodoInicio}
                onChange={(e) => setPeriodoInicio(e.target.value)}
              />
              <input
                type="date"
                style={{ ...inputStyle, flex: 1 }}
                value={periodoFim}
                onChange={(e) => setPeriodoFim(e.target.value)}
              />
            </div>

            <label style={labelStyle}>Capacidade vs. Estimativa</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="number"
                min={0}
                style={{ ...inputStyle, flex: 1 }}
                value={horasDisponiveis}
                onChange={(e) => setHorasDisponiveis(e.target.value ? Number(e.target.value) : "")}
                placeholder="Horas disponíveis"
              />
              <input
                type="number"
                min={0}
                style={{ ...inputStyle, flex: 1 }}
                value={horasEstimadas}
                onChange={(e) => setHorasEstimadas(e.target.value ? Number(e.target.value) : "")}
                placeholder="Horas estimadas"
              />
            </div>

            <label style={labelStyle}>Dependências do cliente</label>
            <textarea
              style={textareaStyle}
              value={dependenciasCliente}
              onChange={(e) => setDependenciasCliente(e.target.value)}
              placeholder="Ex: Acesso ao banco de produção, aprovação do layout"
            />

            <label style={labelStyle}>Carry-over da sprint anterior</label>
            <textarea
              style={{ ...textareaStyle, minHeight: 60 }}
              value={carryOver}
              onChange={(e) => setCarryOver(e.target.value)}
              placeholder="Itens não entregues na sprint anterior (pré-preenchido automaticamente)"
            />
          </>
        )}

        {tipo === "daily" && (
          <>
            <label style={labelStyle}>Data</label>
            <input
              type="date"
              style={inputStyle}
              value={data}
              onChange={(e) => setData(e.target.value)}
            />
            <label style={labelStyle}>O que foi feito desde a última Daily?</label>
            <textarea
              style={textareaStyle}
              value={feito}
              onChange={(e) => setFeito(e.target.value)}
            />
            <label style={labelStyle}>O que será feito até a próxima Daily?</label>
            <textarea
              style={textareaStyle}
              value={proximo}
              onChange={(e) => setProximo(e.target.value)}
            />
            <label style={labelStyle}>Existe algum impedimento ou risco?</label>
            <textarea
              style={textareaStyle}
              value={impedimentos}
              onChange={(e) => setImpedimentos(e.target.value)}
              placeholder="Opcional"
            />
          </>
        )}

        {tipo === "review" && (
          <>
            <label style={labelStyle}>Observações do gerente sobre a sprint</label>
            <textarea
              style={{ ...textareaStyle, minHeight: 120 }}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Opcional — observações qualitativas. O delta planejado vs realizado será calculado automaticamente a partir do planning e das dailys da sprint."
            />

            <label style={labelStyle}>Percepção do cliente</label>
            <textarea
              style={textareaStyle}
              value={percepcaoCliente}
              onChange={(e) => setPercepcaoCliente(e.target.value)}
              placeholder="Ex: Cliente satisfeito com a velocidade de entrega"
            />

            <label style={labelStyle}>Sinal de satisfação</label>
            <select
              style={{ ...inputStyle, cursor: "pointer" }}
              value={sinalSatisfacao}
              onChange={(e) => setSinalSatisfacao(e.target.value)}
            >
              <option value="">Selecione...</option>
              <option value="🟢 Verde">🟢 Verde</option>
              <option value="🟡 Amarelo">🟡 Amarelo</option>
              <option value="🔴 Vermelho">🔴 Vermelho</option>
            </select>

            <label style={labelStyle}>Pedidos fora do escopo</label>
            <textarea
              style={textareaStyle}
              value={pedidosForaEscopo}
              onChange={(e) => setPedidosForaEscopo(e.target.value)}
              placeholder="Ex: Cliente solicitou relatório PDF — registrado para avaliação"
            />
          </>
        )}

        <label style={labelStyle}>
          Anexo (opcional)
          {tipo === "planning" && (
            <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 6 }}>
              — PDF ou print do kanban; tasks visíveis na imagem são extraídas como itens do backlog
            </span>
          )}
          {tipo !== "planning" && (
            <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 6 }}>
              — PDF
            </span>
          )}
        </label>
        <input
          ref={fileRef}
          type="file"
          accept={tipo === "planning" ? "application/pdf,image/png,image/jpeg,image/jpg,image/webp" : "application/pdf"}
          onChange={(e) => setAnexoName(e.target.files?.[0]?.name ?? null)}
        />
        {anexoName && (
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            Anexo: {anexoName}
          </div>
        )}

        {error && (
          <div
            style={{
              marginTop: 14,
              padding: 10,
              background: "#fef2f2",
              color: "#b91c1c",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
          <button type="button" style={ghostBtn} onClick={onClose} disabled={submitting}>
            Cancelar
          </button>
          <button
            type="button"
            style={{ ...primaryBtn, opacity: submitting ? 0.6 : 1 }}
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "Gerando…" : `Gerar ${tipo === "planning" ? "Planning" : tipo === "daily" ? "Daily" : "Review"}`}
          </button>
        </div>
      </div>
    </div>
  );
}
