"use client";

import { useState, useEffect } from "react";
import TutorialBanner from "./TutorialBanner";
import { useAuth } from "./AuthGuard";
import { Button, Card, Chip, EmptyState, ErrorNotice, Field, Input, Select, TabSectionHead, Textarea } from "./ds";
import { ds, labelStyle, type Tone } from "../lib/ds";
import {
  FuncionalidadeResponse,
  FuncionalidadeProposta,
  importarFuncionalidades,
  importarFuncionalidadesArquivo,
  confirmarImportacao,
  createFuncionalidade,
  updateFuncionalidade,
  deleteFuncionalidade,
  aprovarFuncionalidade,
  desfazerAprovacaoFuncionalidade,
} from "../lib/api";

const PRIORIDADE_LABEL: Record<string, string> = {
  must: "Must",
  should: "Should",
  could: "Could",
  wont: "Won't",
};

const PRIORIDADE_COLOR: Record<string, string> = {
  must: "#ff6b6b",
  should: "#f2c14e",
  could: "#b197fc",
  wont: "#8a948e",
};

const STATUS_LABEL: Record<string, string> = {
  nao_iniciada: "Não iniciada",
  em_andamento: "Em andamento",
  em_ajuste: "Em ajuste",
  concluida: "Concluída",
};

const STATUS_COLOR: Record<string, string> = {
  nao_iniciada: "#8a948e",
  em_andamento: "#b197fc",
  concluida: "#3ee06f",
};

type Step = "idle" | "input" | "loading" | "review" | "saving" | "manual";
type InputMode = "texto" | "arquivo";

interface Props {
  projectId: string;
  funcionalidades: FuncionalidadeResponse[];
  onImported: (novas: FuncionalidadeResponse[]) => void;
  onDeleted?: (id: string) => void;
}

export default function EscopoTab({ projectId, funcionalidades, onImported, onDeleted }: Props) {
  const [step, setStep] = useState<Step>("idle");
  const [inputMode, setInputMode] = useState<InputMode>("arquivo");
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [propostas, setPropostas] = useState<FuncionalidadeProposta[]>([]);
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set());
  const [erro, setErro] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ id_funcional: string; titulo: string; descricao: string; criterios_aceite: string[]; prioridade: string; responsavel: string; status: string; sprint_alvo: string }>({ id_funcional: "", titulo: "", descricao: "", criterios_aceite: [""], prioridade: "should", responsavel: "", status: "nao_iniciada", sprint_alvo: "" });
  const [savingEdit, setSavingEdit] = useState(false);
  const [erroEdit, setErroEdit] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [funcList, setFuncList] = useState<FuncionalidadeResponse[]>(funcionalidades);
  const auth = useAuth();
  const podeAprovar = !!auth?.cargo && auth.cargo !== "operacional";
  const [aprovandoId, setAprovandoId] = useState<string | null>(null);
  const [erroAprov, setErroAprov] = useState("");

  async function alterarAprovacao(id: string, acao: (id: string) => Promise<FuncionalidadeResponse>, msgErro: string) {
    setAprovandoId(id);
    setErroAprov("");
    try {
      const atualizada = await acao(id);
      setFuncList((fs) => fs.map((f) => (f.id === id ? { ...f, ...atualizada } : f)));
    } catch (e) {
      setErroAprov(e instanceof Error ? e.message : msgErro);
    } finally {
      setAprovandoId(null);
    }
  }
  const handleAprovar = (id: string) => alterarAprovacao(id, aprovarFuncionalidade, "Erro ao aprovar.");
  const handleDesfazer = (id: string) => alterarAprovacao(id, desfazerAprovacaoFuncionalidade, "Erro ao desfazer aprovação.");
  useEffect(() => { setFuncList(funcionalidades); }, [funcionalidades]);

  function startEdit(f: FuncionalidadeResponse) {
    setEditingId(f.id);
    setEditForm({ id_funcional: f.id_funcional, titulo: f.titulo, descricao: f.descricao ?? "", criterios_aceite: f.criterios_aceite.length ? f.criterios_aceite : [""], prioridade: f.prioridade, responsavel: f.responsavel ?? "", status: f.status ?? "nao_iniciada", sprint_alvo: f.sprint_alvo ?? "" });
    setErroEdit("");
  }

  async function handleSalvarEdit() {
    if (!editForm.titulo.trim()) { setErroEdit("Título é obrigatório."); return; }
    const criterios = editForm.criterios_aceite.filter(c => c.trim());
    if (!criterios.length) { setErroEdit("Adicione ao menos um critério de aceite."); return; }
    setSavingEdit(true);
    setErroEdit("");
    try {
      const atualizada = await updateFuncionalidade(editingId!, {
        id_funcional: editForm.id_funcional.trim() || undefined,
        titulo: editForm.titulo.trim(),
        descricao: editForm.descricao.trim() || undefined,
        criterios_aceite: criterios,
        prioridade: editForm.prioridade,
        responsavel: editForm.responsavel.trim() || undefined,
        status: editForm.status,
        sprint_alvo: editForm.sprint_alvo.trim() || undefined,
      });
      setFuncList(prev => prev.map(f => f.id === atualizada.id ? atualizada : f));
      setEditingId(null);
    } catch (e: unknown) {
      setErroEdit((e as Error).message);
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDelete(f: FuncionalidadeResponse) {
    if (!confirm(`Excluir a funcionalidade "${f.titulo}"? Esta ação é irreversível.`)) return;
    setDeletingId(f.id);
    try {
      await deleteFuncionalidade(f.id);
      setFuncList(prev => prev.filter(x => x.id !== f.id));
      onDeleted?.(f.id);
    } catch (e: unknown) {
      alert((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  // formulário manual
  const emptyForm = { id_funcional: "", titulo: "", descricao: "", criterios_aceite: [""], prioridade: "should", responsavel: "" };
  const [form, setForm] = useState(emptyForm);
  const [savingManual, setSavingManual] = useState(false);

  async function handleSalvarManual() {
    if (!form.titulo.trim()) { setErro("Título é obrigatório."); return; }
    const criterios = form.criterios_aceite.filter(c => c.trim());
    if (!criterios.length) { setErro("Adicione ao menos um critério de aceite."); return; }
    setSavingManual(true);
    setErro("");
    try {
      const nova = await createFuncionalidade({
        project_id: projectId,
        id_funcional: form.id_funcional.trim() || `F${String(funcList.length + 1).padStart(2, "0")}`,
        titulo: form.titulo.trim(),
        descricao: form.descricao.trim() || undefined,
        criterios_aceite: criterios,
        prioridade: form.prioridade,
        responsavel: form.responsavel.trim() || undefined,
      });
      setFuncList(prev => [...prev, nova]);
      onImported([nova]);
      setForm(emptyForm);
      setStep("idle");
    } catch (e: unknown) {
      setErro((e as Error).message);
    } finally {
      setSavingManual(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const ok = file.name.endsWith(".pdf") || file.name.endsWith(".docx") || file.name.endsWith(".txt");
    if (!ok) { setErro("Formato não suportado. Use PDF, DOCX ou TXT."); return; }
    setErro("");
    setArquivo(file);
  }

  async function handleAnalisar() {
    setErro("");
    setStep("loading");
    try {
      let resultado: FuncionalidadeProposta[];
      if (inputMode === "arquivo") {
        if (!arquivo) { setErro("Selecione um arquivo antes de continuar."); setStep("input"); return; }
        resultado = await importarFuncionalidadesArquivo(projectId, arquivo);
      } else {
        if (texto.trim().length < 20) { setErro("Cole o texto do contrato antes de continuar."); setStep("input"); return; }
        resultado = await importarFuncionalidades(projectId, texto);
      }
      setPropostas(resultado);
      setSelecionadas(new Set(resultado.map((_, i) => i)));
      setStep("review");
    } catch (e: unknown) {
      setErro((e as Error).message);
      setStep("input");
    }
  }

  async function handleConfirmar() {
    setStep("saving");
    setErro("");
    try {
      const itens = propostas.map((p, i) => ({ proposta: p, confirmed: selecionadas.has(i) }));
      const criadas = await confirmarImportacao(projectId, itens);
      onImported(criadas);
      setStep("idle");
      setTexto("");
      setPropostas([]);
      setSelecionadas(new Set());
    } catch (e: unknown) {
      setErro((e as Error).message);
      setStep("review");
    }
  }

  function toggleSelecionada(i: number) {
    setSelecionadas((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function handleCancelar() {
    setStep("idle");
    setTexto("");
    setArquivo(null);
    setPropostas([]);
    setSelecionadas(new Set());
    setErro("");
  }

  const [sprintFiltro, setSprintFiltro] = useState<string>("todas");

  const totalPorStatus = funcList.reduce<Record<string, number>>((acc, f) => {
    acc[f.status] = (acc[f.status] ?? 0) + 1;
    return acc;
  }, {});

  // sprints únicas presentes nas funcionalidades, ordenadas
  const sprintsDisponiveis = Array.from(
    new Set(funcList.map((f) => f.sprint_alvo).filter(Boolean))
  ).sort((a, b) => Number(a) - Number(b)) as string[];

  const funcExibidas = sprintFiltro === "todas"
    ? funcList
    : sprintFiltro === "sem_sprint"
    ? funcList.filter((f) => !f.sprint_alvo)
    : funcList.filter((f) => f.sprint_alvo === sprintFiltro);

  const escopoSteps = [
    { title: "O que são funcionalidades", body: "São as entregas de alto nível do projeto — ex: 'Tela de Login', 'Dashboard', 'Relatório mensal'. Cada funcionalidade representa um entregável para o cliente, diferente das tasks (que são o trabalho técnico interno)." },
    { title: "Importar do contrato", body: "Clique em 'Importar funcionalidades' e faça upload do PDF ou documento do contrato/proposta. O DocuData usa IA para extrair automaticamente as funcionalidades listadas. Você revisa antes de confirmar." },
    { title: "Adicionar manualmente", body: "Clique em '+ Adicionar manualmente' para criar uma funcionalidade sem IA. Preencha o nome, a prioridade (Must/Should/Could/Won't — metodologia MoSCoW) e a categoria." },
    { title: "Prioridades MoSCoW", body: "Must = obrigatório para entrega. Should = importante, mas não bloqueia. Could = desejável se houver tempo. Won't = fora do escopo desta versão. Use para alinhar expectativas com o cliente." },
    { title: "Status das funcionalidades", body: "Cada funcionalidade passa por Não iniciada → Em andamento → Concluída. Concluída ainda precisa da sua aprovação: só funcionalidades aprovadas contam no 'Escopo concluído' do Painel. Se uma task dela for reaberta ou entrar task nova, a aprovação cai e ela volta a aguardar." },
    { title: "Funcionalidade travada", body: "Marque uma funcionalidade como 'Travada' quando há um bloqueio externo (aguardando cliente, dependência técnica). Funcionalidades travadas aparecem em destaque no Painel > Itens em atenção." },
    { title: "Vincular à sprint", body: "Defina em qual sprint cada funcionalidade está planejada. Isso alimenta o Kanban de Sprint no Painel e ajuda a visualizar o progresso sprint a sprint." },
  ];

  const statusTone = (status: string): Tone =>
    status === "concluida" ? "green" : status === "em_andamento" ? "violet" : "neutral";

  const linkBtn: React.CSSProperties = {
    background: "none", border: "none", cursor: "pointer", fontFamily: "inherit",
    fontSize: 13, padding: "6px 10px", borderRadius: 8, color: ds.text2,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <TutorialBanner heading="Planejamento e Funcionalidades" steps={escopoSteps} />

      <TabSectionHead
        title="Planejamento"
        count={`${funcionalidades.length} ${funcionalidades.length === 1 ? "funcionalidade" : "funcionalidades"}`}
        description="Lista de funcionalidades do projeto. Importe direto do texto do contrato ou da proposta: a IA extrai e propõe cada item para você confirmar."
        actions={step === "idle" ? (
          <>
            <Button variant="secondary" onClick={() => { setStep("manual"); setErro(""); setForm(emptyForm); }}>+ Adicionar manualmente</Button>
            <Button variant="primary" onClick={() => setStep("input")}>+ Importar do contrato</Button>
          </>
        ) : undefined}
      />

      {/* Fluxo de importação */}
      {step === "input" && (
        <Card>
          <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: 18 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: ds.white }}>Importar do contrato</h3>
            <div role="group" aria-label="Forma de importar" style={{ display: "flex", padding: 4, gap: 2, borderRadius: 12, background: "rgba(255,255,255,0.04)", border: `1px solid ${ds.border}`, width: "fit-content" }}>
              {(["arquivo", "texto"] as InputMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  aria-pressed={inputMode === mode}
                  onClick={() => setInputMode(mode)}
                  style={{
                    height: 32, padding: "0 14px", borderRadius: 9, border: "none", cursor: "pointer", fontFamily: "inherit",
                    fontSize: 13, fontWeight: 600,
                    background: inputMode === mode ? ds.greenSoft : "transparent",
                    color: inputMode === mode ? ds.green : ds.muted,
                  }}
                >
                  {mode === "arquivo" ? "Upload de arquivo" : "Colar texto"}
                </button>
              ))}
            </div>

            {inputMode === "arquivo" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <p style={{ margin: 0, fontSize: 13.5, color: ds.muted, lineHeight: 1.55 }}>
                  Faça upload do contrato ou proposta. Aceita PDF (com ou sem texto), DOCX e TXT.
                </p>
                <label
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  style={{
                    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6,
                    border: `1.5px dashed ${dragging || arquivo ? ds.greenLine : ds.borderStrong}`,
                    borderRadius: 12, padding: "40px 24px", cursor: "pointer",
                    background: dragging || arquivo ? ds.greenSoft : ds.inner,
                    transition: "background 0.15s, border-color 0.15s",
                  }}
                >
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt"
                    style={{ display: "none" }}
                    onChange={(e) => { setErro(""); setArquivo(e.target.files?.[0] ?? null); }}
                  />
                  {dragging ? (
                    <span style={{ fontSize: 14, fontWeight: 600, color: ds.green }}>Solte aqui</span>
                  ) : arquivo ? (
                    <>
                      <span style={{ fontSize: 14, fontWeight: 600, color: ds.green }}>✓ {arquivo.name}</span>
                      <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>
                        {(arquivo.size / 1024).toFixed(0)} KB · clique ou arraste para trocar
                      </span>
                    </>
                  ) : (
                    <>
                      <span style={{ fontSize: 14, fontWeight: 600, color: ds.text2 }}>Arraste o arquivo aqui</span>
                      <span style={{ fontSize: 12.5, color: ds.muted }}>ou clique para selecionar · PDF, DOCX ou TXT</span>
                    </>
                  )}
                </label>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <p style={{ margin: 0, fontSize: 13.5, color: ds.muted, lineHeight: 1.55 }}>
                  Cole o texto completo do contrato ou proposta. A IA extrai cada funcionalidade com título, descrição e critérios de aceite.
                </p>
                <Textarea
                  aria-label="Texto do contrato"
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                  placeholder="Cole aqui o texto do contrato..."
                  rows={12}
                />
              </div>
            )}

            {erro && <ErrorNotice>{erro}</ErrorNotice>}
            <div style={{ display: "flex", gap: 10 }}>
              <Button variant="primary" onClick={handleAnalisar}>Analisar com IA</Button>
              <Button variant="ghost" onClick={handleCancelar}>Cancelar</Button>
            </div>
          </div>
        </Card>
      )}

      {step === "loading" && (
        <Card>
          <div role="status" style={{ padding: 40, textAlign: "center" }}>
            <p style={{ margin: 0, fontSize: 14, color: ds.text2 }}>Analisando o contrato e extraindo funcionalidades...</p>
            <p style={{ margin: "8px 0 0", fontSize: 12.5, color: ds.muted }}>Isso pode levar alguns segundos</p>
          </div>
        </Card>
      )}

      {step === "review" && (
        <Card>
          <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: ds.white }}>
                  {propostas.length} funcionalidades encontradas
                </h3>
                <p style={{ margin: "4px 0 0", fontSize: 13.5, color: ds.muted }}>Desmarque as que não quer salvar, depois confirme.</p>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <Button variant="ghost" onClick={handleCancelar}>Cancelar</Button>
                <Button variant="primary" onClick={handleConfirmar} disabled={selecionadas.size === 0}>
                  Salvar {selecionadas.size} selecionadas
                </Button>
              </div>
            </div>

            {erro && <ErrorNotice>{erro}</ErrorNotice>}

            <div style={{ display: "flex", gap: 14 }}>
              <button type="button" className="ds-text-btn" style={{ ...linkBtn, padding: 0, color: ds.green, fontWeight: 600 }} onClick={() => setSelecionadas(new Set(propostas.map((_, i) => i)))}>
                Selecionar todas
              </button>
              <button type="button" className="ds-text-btn" style={{ ...linkBtn, padding: 0, color: ds.muted, fontWeight: 600 }} onClick={() => setSelecionadas(new Set())}>
                Desmarcar todas
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {propostas.map((p, i) => {
                const marcada = selecionadas.has(i);
                return (
                  <label
                    key={i}
                    style={{
                      display: "flex", alignItems: "flex-start", gap: 12, padding: "14px 16px", borderRadius: 12, cursor: "pointer",
                      border: `1px solid ${marcada ? ds.greenLine : ds.innerBorder}`,
                      background: marcada ? ds.greenSoft : ds.inner,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={marcada}
                      onChange={() => toggleSelecionada(i)}
                      style={{ marginTop: 3, width: 16, height: 16, accentColor: ds.green, cursor: "pointer" }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{p.id_funcional}</span>
                        <span style={{ fontFamily: ds.fontMono, fontSize: 11, color: PRIORIDADE_COLOR[p.prioridade] ?? ds.muted, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                          {PRIORIDADE_LABEL[p.prioridade] ?? p.prioridade}
                        </span>
                      </div>
                      <p style={{ margin: "4px 0 0", fontSize: 15, fontWeight: 500, color: ds.white }}>{p.titulo}</p>
                      {p.descricao && <p style={{ margin: "4px 0 0", fontSize: 13.5, color: ds.text2, lineHeight: 1.55 }}>{p.descricao}</p>}
                      {p.criterios_aceite.length > 0 && (
                        <div style={{ marginTop: 10 }}>
                          <span style={labelStyle}>Critérios de aceite</span>
                          <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                            {p.criterios_aceite.map((c, j) => (
                              <li key={j} style={{ fontSize: 13, color: ds.text2, marginBottom: 2, lineHeight: 1.5 }}>{c}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {step === "saving" && (
        <Card>
          <p role="status" style={{ margin: 0, padding: 40, textAlign: "center", fontSize: 14, color: ds.text2 }}>Salvando funcionalidades...</p>
        </Card>
      )}

      {step === "manual" && (
        <Card>
          <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: ds.white }}>Nova funcionalidade</h3>
            {(
              [
                { label: "ID funcional", key: "id_funcional" as const, placeholder: "Ex: F01 (opcional, gerado automaticamente)", required: false },
                { label: "Título", key: "titulo" as const, placeholder: "Ex: Autenticação de usuários", required: true },
                { label: "Descrição", key: "descricao" as const, placeholder: "Contexto adicional (opcional)", required: false },
                { label: "Responsável", key: "responsavel" as const, placeholder: "Nome do responsável (opcional)", required: false },
              ] as const
            ).map(({ label, key, placeholder, required }) => (
              <Field key={key} label={label} htmlFor={`nova-${key}`} required={required}>
                <Input id={`nova-${key}`} value={form[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} placeholder={placeholder} />
              </Field>
            ))}
            <CriteriosEditor
              idPrefix="nova"
              criterios={form.criterios_aceite}
              onChange={(criterios_aceite) => setForm((f) => ({ ...f, criterios_aceite }))}
            />
            {erro && <ErrorNotice>{erro}</ErrorNotice>}
            <div style={{ display: "flex", gap: 10 }}>
              <Button variant="primary" onClick={handleSalvarManual} disabled={savingManual}>
                {savingManual ? "Salvando..." : "Salvar funcionalidade"}
              </Button>
              <Button variant="ghost" onClick={() => { setStep("idle"); setErro(""); }}>Cancelar</Button>
            </div>
          </div>
        </Card>
      )}

      {/* Resumo de status + filtro por sprint */}
      {funcionalidades.length > 0 && step !== "review" && step !== "loading" && step !== "saving" && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {Object.entries(totalPorStatus).map(([status, count]) => (
            <Chip key={status} tone={statusTone(status)} dot={status === "concluida"}>
              {STATUS_LABEL[status] ?? status} · {count}
            </Chip>
          ))}
          {sprintsDisponiveis.length > 0 && (
            <div role="group" aria-label="Filtrar por sprint" style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
              {[{ label: "Todas", value: "todas" }, ...sprintsDisponiveis.map((s) => ({ label: `Sprint ${s}`, value: s })), { label: "Sem sprint", value: "sem_sprint" }].map(({ label, value }) => {
                const ativo = sprintFiltro === value;
                return (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={ativo}
                    onClick={() => setSprintFiltro(value)}
                    style={{
                      padding: "4px 10px", borderRadius: 999, fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
                      background: ativo ? ds.greenSoft : "rgba(255,255,255,0.05)",
                      color: ativo ? ds.green : ds.text2,
                      border: `1px solid ${ativo ? ds.greenLine : ds.border}`,
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lista existente */}
      {funcList.length === 0 && step === "idle" ? (
        <EmptyState>
          Nenhuma funcionalidade cadastrada. Clique em + Importar do contrato para extrair as funcionalidades automaticamente.
        </EmptyState>
      ) : (
        step !== "review" && step !== "loading" && step !== "saving" && funcExibidas.length > 0 && (
          <>
          {erroAprov && <ErrorNotice>{erroAprov}</ErrorNotice>}
          <Card>
            {funcExibidas.map((f, idx) => {
              const aberta = expanded === f.id;
              const editando = editingId === f.id;
              return (
                <div key={f.id} style={{ borderTop: idx > 0 ? `1px solid ${ds.border}` : "none" }}>
                  <div className="ds-func-row" style={{ display: "grid", gridTemplateColumns: "44px 120px minmax(0,1fr) auto", gap: 16, alignItems: "center", padding: "15px 22px" }}>
                    <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{f.id_funcional}</span>
                    <span><Chip tone={statusTone(f.status)}>{STATUS_LABEL[f.status] ?? f.status}</Chip></span>
                    <span style={{ display: "flex", alignItems: "baseline", gap: 10, minWidth: 0 }}>
                      <span style={{ fontSize: 15, fontWeight: 500, color: ds.white, overflow: "hidden", textOverflow: "ellipsis" }}>{f.titulo}</span>
                      {f.sprint_alvo && <span style={{ fontFamily: ds.fontMono, fontSize: 11.5, color: ds.muted, flexShrink: 0 }}>Sprint {f.sprint_alvo}</span>}
                      {f.status === "concluida" && (f.aprovada_em ? (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12.5, color: ds.text2, flexShrink: 0 }}>
                          <Chip tone="green" dot>
                            Aprovada em {new Date(f.aprovada_em).toLocaleDateString("pt-BR")}{f.aprovada_por_nome ? ` por ${f.aprovada_por_nome}` : ""}
                          </Chip>
                          {podeAprovar && (
                            <button type="button" className="ds-text-btn" onClick={() => handleDesfazer(f.id)} disabled={aprovandoId === f.id}
                              style={{ background: "none", border: "none", padding: 0, cursor: aprovandoId === f.id ? "default" : "pointer", fontFamily: "inherit", fontSize: 12.5, color: ds.muted }}>
                              {aprovandoId === f.id ? "Desfazendo..." : "Desfazer aprovação"}
                            </button>
                          )}
                        </span>
                      ) : (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                          <Chip tone="amber">Aguardando aprovação</Chip>
                          {podeAprovar && (
                            <Button size="sm" variant="primary" onClick={() => handleAprovar(f.id)} disabled={aprovandoId === f.id}>
                              {aprovandoId === f.id ? "Aprovando..." : "Aprovar"}
                            </Button>
                          )}
                        </span>
                      ))}
                    </span>
                    {!editando ? (
                      <div style={{ display: "flex", gap: 2 }}>
                        <button type="button" className="ds-text-btn" style={linkBtn} onClick={() => { startEdit(f); setExpanded(f.id); }}>Editar</button>
                        <button
                          type="button"
                          style={{ ...linkBtn, color: deletingId === f.id ? ds.muted : ds.red }}
                          disabled={deletingId === f.id}
                          onClick={() => handleDelete(f)}
                        >
                          {deletingId === f.id ? "Excluindo..." : "Excluir"}
                        </button>
                        <button
                          type="button"
                          className="ds-text-btn"
                          aria-expanded={aberta}
                          aria-label={aberta ? `Recolher ${f.titulo}` : `Ver detalhes de ${f.titulo}`}
                          style={{ ...linkBtn, padding: "6px 8px", color: ds.muted }}
                          onClick={() => setExpanded(aberta ? null : f.id)}
                        >
                          {aberta ? "▴" : "▾"}
                        </button>
                      </div>
                    ) : <span />}
                  </div>

                  {/* Formulário de edição inline */}
                  {editando && (
                    <div style={{ padding: "4px 22px 22px 82px", display: "flex", flexDirection: "column", gap: 14 }}>
                      {([
                        { label: "ID funcional", key: "id_funcional" as const, placeholder: "F01", required: false },
                        { label: "Título", key: "titulo" as const, placeholder: "Título da funcionalidade", required: true },
                        { label: "Descrição", key: "descricao" as const, placeholder: "Descrição opcional", required: false },
                        { label: "Responsável", key: "responsavel" as const, placeholder: "Nome do responsável", required: false },
                      ] as const).map(({ label, key, placeholder, required }) => (
                        <Field key={key} label={label} htmlFor={`edit-${f.id}-${key}`} required={required}>
                          <Input id={`edit-${f.id}-${key}`} value={editForm[key]} onChange={(e) => setEditForm((ef) => ({ ...ef, [key]: e.target.value }))} placeholder={placeholder} />
                        </Field>
                      ))}
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 14 }}>
                        <Field label="Status" htmlFor={`edit-${f.id}-status`} hint={f.tem_tasks ? "O status vem das tasks." : undefined}>
                          <Select id={`edit-${f.id}-status`} value={editForm.status} disabled={f.tem_tasks} onChange={(e) => setEditForm((ef) => ({ ...ef, status: e.target.value }))}>
                            <option value="nao_iniciada">Não iniciada</option>
                            <option value="em_andamento">Em andamento</option>
                            <option value="em_ajuste">Em ajuste</option>
                            <option value="concluida">Concluída</option>
                          </Select>
                        </Field>
                        <Field label="Sprint alvo" htmlFor={`edit-${f.id}-sprint`}>
                          <Input id={`edit-${f.id}-sprint`} value={editForm.sprint_alvo} onChange={(e) => setEditForm((ef) => ({ ...ef, sprint_alvo: e.target.value }))} placeholder="ex: 3" />
                        </Field>
                        <Field label="Prioridade" htmlFor={`edit-${f.id}-prioridade`}>
                          <Select id={`edit-${f.id}-prioridade`} value={editForm.prioridade} onChange={(e) => setEditForm((ef) => ({ ...ef, prioridade: e.target.value }))}>
                            {[["must", "Must"], ["should", "Should"], ["could", "Could"], ["wont", "Won't"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                          </Select>
                        </Field>
                      </div>
                      <CriteriosEditor
                        idPrefix={`edit-${f.id}`}
                        criterios={editForm.criterios_aceite}
                        onChange={(criterios_aceite) => setEditForm((ef) => ({ ...ef, criterios_aceite }))}
                      />
                      {erroEdit && <ErrorNotice>{erroEdit}</ErrorNotice>}
                      <div style={{ display: "flex", gap: 10 }}>
                        <Button variant="primary" onClick={handleSalvarEdit} disabled={savingEdit}>{savingEdit ? "Salvando..." : "Salvar"}</Button>
                        <Button variant="ghost" onClick={() => { setEditingId(null); setErroEdit(""); }}>Cancelar</Button>
                      </div>
                    </div>
                  )}

                  {/* Detalhes expandidos (só quando não está editando) */}
                  {aberta && !editando && (
                    <div style={{ padding: "0 22px 18px 82px", display: "flex", flexDirection: "column", gap: 12 }}>
                      {f.descricao && <p style={{ margin: 0, fontSize: 13.5, color: ds.text2, lineHeight: 1.6 }}>{f.descricao}</p>}
                      {f.criterios_aceite.length > 0 && (
                        <div>
                          <span style={labelStyle}>Critérios de aceite</span>
                          <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                            {f.criterios_aceite.map((c, i) => <li key={i} style={{ fontSize: 13.5, color: ds.text2, marginBottom: 4, lineHeight: 1.55 }}>{c}</li>)}
                          </ul>
                        </div>
                      )}
                      <div style={{ display: "flex", gap: 18, flexWrap: "wrap", fontSize: 12.5, color: ds.muted }}>
                        <span>Prioridade <span style={{ color: PRIORIDADE_COLOR[f.prioridade] ?? ds.text2, fontWeight: 600 }}>{PRIORIDADE_LABEL[f.prioridade] ?? f.prioridade}</span></span>
                        {f.responsavel && <span>Responsável <span style={{ color: ds.text2, fontWeight: 600 }}>{f.responsavel}</span></span>}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </Card>
          </>
        )
      )}
    </div>
  );
}

/** Lista editável de critérios de aceite (usada na criação e na edição). */
function CriteriosEditor({ idPrefix, criterios, onChange }: { idPrefix: string; criterios: string[]; onChange: (c: string[]) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <span style={labelStyle}>Critérios de aceite<span style={{ color: ds.green }}> *</span></span>
      {criterios.map((c, i) => (
        <div key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Input
            id={`${idPrefix}-criterio-${i}`}
            aria-label={`Critério ${i + 1}`}
            value={c}
            onChange={(e) => { const next = [...criterios]; next[i] = e.target.value; onChange(next); }}
            placeholder={`Critério ${i + 1}`}
          />
          {criterios.length > 1 && (
            <button
              type="button"
              aria-label={`Remover critério ${i + 1}`}
              onClick={() => onChange(criterios.filter((_, j) => j !== i))}
              style={{ background: "none", border: "none", color: ds.red, fontSize: 18, cursor: "pointer", padding: "0 6px" }}
            >
              ×
            </button>
          )}
        </div>
      ))}
      <button
        type="button"
        className="ds-text-btn"
        onClick={() => onChange([...criterios, ""])}
        style={{ alignSelf: "flex-start", background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 600, color: ds.green }}
      >
        + Adicionar critério
      </button>
    </div>
  );
}
