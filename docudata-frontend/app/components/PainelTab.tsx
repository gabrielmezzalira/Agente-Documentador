"use client";

import { useEffect, useState } from "react";
import TutorialBanner from "./TutorialBanner";
import {
  getPainel,
  listFuncionalidades,
  getSprintFuncionalidades,
  createSprintFuncionalidades,
  updateSprintFuncionalidade,
  updateFuncionalidade,
  listTasksKanban,
  type FuncionalidadeResponse,
  type OperacionalResponse,
  type PainelData,
  type Project,
  type SprintFuncionalidade,
  type SprintWithStatus,
} from "../lib/api";
import { ds } from "../lib/ds";
import { Card, ErrorNotice } from "./ds";
import { ItensAtencaoCard, MetricasFluxoCard, TempoEscopoCard, TempoPorFaseCard } from "./painel/IndicadoresCards";
import SprintKanbanBoard from "./painel/SprintKanbanBoard";
import { ElegibilidadeCard, ExtratoPontosCard } from "./painel/PontosCards";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  project: Project;
  operacionais: OperacionalResponse[];
  onProjectUpdated?: (updated: Project) => void;
}

export default function PainelTab({ projectId, sprints, project, operacionais, onProjectUpdated }: Props) {
  const [data, setData] = useState<PainelData | null>(null);
  const [funcionalidades, setFuncionalidades] = useState<FuncionalidadeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sprintSelecionada, setSprintSelecionada] = useState<number>(
    sprints.length > 0 ? Math.max(...sprints.map((s) => s.numero)) : 1
  );
  const [sprintFuncs, setSprintFuncs] = useState<SprintFuncionalidade[]>([]);
  const [dragFuncId, setDragFuncId] = useState<string | null>(null);
  const [addingFunc, setAddingFunc] = useState(false);
  const [addFuncId, setAddFuncId] = useState("");
  const [kanbanSaving, setKanbanSaving] = useState(false);
  const [taskCountsByFuncId, setTaskCountsByFuncId] = useState<Map<string, { total: number; concluidas: number }>>(new Map());

  useEffect(() => {
    setLoading(true);
    Promise.all([getPainel(projectId), listFuncionalidades(projectId)])
      .then(([d, funcs]) => {
        setData(d);
        setFuncionalidades(funcs);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    listTasksKanban({ project_id: projectId }).then((tasks) => {
      const map = new Map<string, { total: number; concluidas: number }>();
      for (const t of tasks) {
        if (!t.funcionalidade_id) continue;
        const prev = map.get(t.funcionalidade_id) ?? { total: 0, concluidas: 0 };
        map.set(t.funcionalidade_id, {
          total: prev.total + 1,
          concluidas: prev.concluidas + (t.coluna_kanban === "concluida" ? 1 : 0),
        });
      }
      setTaskCountsByFuncId(map);
    }).catch(() => {});
  }, [projectId]);

  const selectedSprintObj = sprints.find((s) => s.numero === sprintSelecionada);

  useEffect(() => {
    if (!selectedSprintObj) { setSprintFuncs([]); return; }
    getSprintFuncionalidades(selectedSprintObj.id)
      .then(setSprintFuncs)
      .catch(() => setSprintFuncs([]));
  }, [selectedSprintObj?.id]);

  if (loading) {
    return (
      <Card>
        <p role="status" style={{ margin: 0, padding: "24px 26px", fontSize: 14, color: ds.muted }}>Carregando painel…</p>
      </Card>
    );
  }

  if (error) return <ErrorNotice>{error}</ErrorNotice>;

  if (!data) return null;

  const sfByFuncId = new Map(sprintFuncs.map((sf) => [sf.funcionalidade_id, sf]));
  const funcsNotInSprint = funcionalidades.filter((f) => !sfByFuncId.has(f.id));

  async function handleDrop(targetStatus: "nao_iniciada" | "em_andamento" | "concluida") {
    if (!dragFuncId) { setDragFuncId(null); return; }
    const sf = sfByFuncId.get(dragFuncId);
    setKanbanSaving(true);
    try {
      if (sf) {
        // Fluxo novo: existe registro em sprint_funcionalidades — status só aceita em_andamento/concluida
        if (targetStatus !== "nao_iniciada" && sf.status !== targetStatus && selectedSprintObj) {
          await updateSprintFuncionalidade(sf.id, { status: targetStatus });
          setSprintFuncs(await getSprintFuncionalidades(selectedSprintObj.id));
        }
      } else {
        // Fluxo antigo (fallback): status mora direto em funcionalidades.status
        const f = funcionalidades.find((fn) => fn.id === dragFuncId);
        if (f && f.status !== targetStatus) {
          await updateFuncionalidade(f.id, { status: targetStatus });
          setFuncionalidades(await listFuncionalidades(projectId));
        }
      }
    } finally {
      setKanbanSaving(false);
      setDragFuncId(null);
    }
  }

  async function handleAddToSprint() {
    if (!addFuncId || !selectedSprintObj) return;
    setKanbanSaving(true);
    try {
      await createSprintFuncionalidades(selectedSprintObj.id, [{ funcionalidade_id: addFuncId, tasks: [] }]);
      setSprintFuncs(await getSprintFuncionalidades(selectedSprintObj.id));
      setAddFuncId("");
      setAddingFunc(false);
    } finally {
      setKanbanSaving(false);
    }
  }


  // Resolve sprint_funcionalidade → FuncionalidadeResponse using the funcionalidades list
  function sfToFunc(sf: SprintFuncionalidade): FuncionalidadeResponse | null {
    return funcionalidades.find((f) => f.id === sf.funcionalidade_id) ?? null;
  }

  let planejado: FuncionalidadeResponse[];
  let emAndamento: FuncionalidadeResponse[];
  let concluido: FuncionalidadeResponse[];

  if (sprintFuncs.length > 0) {
    // New planning flow: use sprint_funcionalidades as source of truth
    planejado = [];
    emAndamento = sprintFuncs
      .filter((sf) => sf.status === "em_andamento")
      .map(sfToFunc)
      .filter((f): f is FuncionalidadeResponse => f !== null);
    concluido = sprintFuncs
      .filter((sf) => sf.status === "concluida")
      .map(sfToFunc)
      .filter((f): f is FuncionalidadeResponse => f !== null);
  } else {
    // Fallback: old sprint_alvo-based filtering
    const funcsDaSprint = funcionalidades.filter(
      (f) => f.sprint_alvo !== null && f.sprint_alvo !== undefined && f.sprint_alvo === String(sprintSelecionada)
    );
    planejado = funcsDaSprint.filter((f) => f.status === "nao_iniciada");
    emAndamento = funcsDaSprint.filter((f) => f.status === "em_andamento");
    concluido = funcsDaSprint.filter((f) => f.status === "concluida");
  }

  const painelSteps = [
    { title: "Tempo × Escopo", body: "Compara o % do prazo já consumido com o % do escopo concluído (funcionalidades entregues). Se o prazo avança mais rápido que o escopo, há atraso. Configure data de início, data de término e tolerância clicando em 'Editar' no card." },
    { title: "Desvio e tolerância", body: "Desvio = prazo consumido % − escopo concluído %. Se positivo, você está atrás do planejado. Tolerância define quantos pontos percentuais de desvio são aceitáveis — acima disso, aparece um alerta laranja." },
    { title: "Itens em atenção", body: "Funcionalidades marcadas como 'Travadas' na aba Planejamento aparecem aqui. São bloqueios que precisam de ação — aguardando cliente, dependência externa ou decisão pendente." },
    { title: "WIP e Throughput de funcionalidades", body: "WIP (Work in Progress) = funcionalidades em andamento agora. Throughput = quantas foram concluídas por semana. Cycle-time = tempo médio de uma funcionalidade do início ao fim. Métricas calculadas a partir do histórico de status das funcionalidades." },
    { title: "Eficiência de fluxo", body: "% do tempo total que as funcionalidades passaram em fase ativa (Em andamento) vs. em espera. Baixa eficiência indica que as funcionalidades ficam muito tempo paradas entre etapas." },
    { title: "Tempo por fase", body: "Mostra quanto tempo (média e p85) as funcionalidades passaram em cada status. Útil para identificar qual fase é o gargalo do projeto." },
    { title: "Kanban de Sprint", body: "Visualize as funcionalidades planejadas para cada sprint e mova entre Planejado / Em andamento / Concluído. Use o seletor de sprint no canto superior direito. Adicione funcionalidades existentes à sprint com '+ Adicionar funcionalidade'." },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <TutorialBanner heading="Painel do Projeto" steps={painelSteps} />

      <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <TempoEscopoCard
          bloco={data.bloco_a}
          project={project}
          onSaved={(updated) => {
            onProjectUpdated?.(updated);
            getPainel(projectId).then(setData).catch(() => {});
          }}
        />
        <ItensAtencaoCard bloco={data.bloco_b} />
        <MetricasFluxoCard bloco={data.bloco_c} />
        <TempoPorFaseCard bloco={data.bloco_d} />
      </div>

      <SprintKanbanBoard
        sprints={sprints}
        sprintSelecionada={sprintSelecionada}
        onSelectSprint={setSprintSelecionada}
        colunas={{ nao_iniciada: planejado, em_andamento: emAndamento, concluida: concluido }}
        taskCounts={taskCountsByFuncId}
        saving={kanbanSaving}
        onDragStart={setDragFuncId}
        onDragEnd={() => setDragFuncId(null)}
        onDrop={handleDrop}
        adding={addingFunc}
        addFuncId={addFuncId}
        funcsDisponiveis={funcsNotInSprint}
        onStartAdding={() => setAddingFunc(true)}
        onChangeAddFunc={setAddFuncId}
        onConfirmAdd={handleAddToSprint}
        onCancelAdd={() => { setAddingFunc(false); setAddFuncId(""); }}
      />

      <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr", gap: 16, alignItems: "start" }}>
        <ExtratoPontosCard operacionais={operacionais} sprints={sprints} />
        <ElegibilidadeCard sprints={sprints} />
      </div>
    </div>
  );
}
