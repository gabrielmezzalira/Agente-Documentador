import { ds, type Tone } from "../../lib/ds";
import type { AcompSinal, AcompStatus } from "../../lib/api";

export const ORDEM_STATUS: Record<AcompStatus, number> = { critico: 0, atencao: 1, sem_dados: 2, saudavel: 3 };
export const TOM_STATUS: Record<AcompStatus, Tone> = { critico: "red", atencao: "amber", sem_dados: "neutral", saudavel: "green" };
export const COR_STATUS: Record<AcompStatus, string> = { critico: ds.red, atencao: ds.amber, sem_dados: ds.chartGrey, saudavel: ds.green };

/** Nome e regra de cada status, com as mesmas regras de services/status_projeto.py. */
export const STATUS_INFO: Record<AcompStatus, { nome: string; regra: string }> = {
  critico: { nome: "Crítico", regra: "Ritmo abaixo de 0,7, prazo andando mais rápido que o escopo, meta da última sprint abaixo da metade ou 5+ tasks travadas." },
  atencao: { nome: "Atenção", regra: "Alguma task travada, ritmo caindo há 3 sprints ou sprint atual sem meta." },
  sem_dados: { nome: "Faltam dados", regra: "Nada de errado à vista, mas falta cadastro para medir: datas do contrato, escopo, gerente ou sprint iniciada." },
  saudavel: { nome: "Saudável", regra: "Sprint planejada, com meta, e nenhum sinal de risco." },
};

interface Pendencia {
  titulo: (texto: string) => string;
  explicacao: string;
  quem: string;
  tom: Tone;
}

/** Cada sinal do backend vira uma pendência legível: o que é, por que importa e quem resolve. */
export const PENDENCIAS: Record<string, Pendencia> = {
  spi_critico: {
    titulo: (t) => `Ritmo baixo (${t})`, tom: "red", quem: "Gerente com o time",
    explicacao: "A última sprint fechada entregou menos de 70% dos pontos previstos.",
  },
  prazo: {
    titulo: () => "Prazo à frente do escopo", tom: "red", quem: "Gerente e líder",
    explicacao: "Já passou uma fatia do prazo do contrato maior do que a fatia de funcionalidades aprovadas, além da tolerância do projeto.",
  },
  meta_ruim: {
    titulo: () => "Meta da última sprint não cumprida", tom: "red", quem: "Gerente",
    explicacao: "Menos da metade das funcionalidades da meta foi entregue na última sprint fechada.",
  },
  travadas: {
    titulo: (t) => t.replace("travada", "task travada").replace("task travadas", "tasks travadas"), tom: "amber", quem: "Gerente",
    explicacao: "Tasks paradas tempo demais sem andar no kanban. Alguém precisa destravar ou registrar o bloqueio.",
  },
  spi_caindo: {
    titulo: () => "Ritmo caindo", tom: "amber", quem: "Gerente com o time",
    explicacao: "O SPI ficou abaixo de 0,9 nas três últimas sprints fechadas.",
  },
  sem_meta: {
    titulo: () => "Meta da sprint não definida", tom: "amber", quem: "Líder, pelo botão Definir meta",
    explicacao: "Ninguém escolheu quais funcionalidades esta sprint precisa entregar. Sem meta, no fim da sprint não dá para dizer se ela foi bem.",
  },
  sem_sprint: {
    titulo: () => "Nenhuma sprint iniciada", tom: "neutral", quem: "Gerente",
    explicacao: "O projeto ainda não começou a executar: falta iniciar a primeira sprint na aba Sprints.",
  },
  sem_planejamento: {
    titulo: () => "Sprint atual sem planejamento", tom: "neutral", quem: "Gerente",
    explicacao: "A sprint em andamento não tem tasks nem funcionalidades. Falta fazer a Planning.",
  },
  sem_datas: {
    titulo: () => "Sem datas do contrato", tom: "neutral", quem: "Gerente, em Configurações",
    explicacao: "Faltam início e fim contratados. Sem eles não dá para comparar quanto do prazo já passou com quanto do escopo foi entregue.",
  },
  sem_funcionalidades: {
    titulo: () => "Escopo vazio", tom: "neutral", quem: "Gerente, na aba Planejamento",
    explicacao: "O projeto não tem funcionalidades cadastradas, então não há como medir quanto dele já foi entregue.",
  },
  sem_gerente: {
    titulo: () => "Sem gerente vinculado", tom: "neutral", quem: "Líder, em Configurações do projeto",
    explicacao: "Ninguém está vinculado como gerente: o projeto não tem dono e ninguém recebe os lembretes.",
  },
};

export function pendencia(s: AcompSinal): { titulo: string; explicacao: string; quem: string; tom: Tone } {
  const p = PENDENCIAS[s.codigo];
  if (!p) return { titulo: s.texto, explicacao: s.texto, quem: "", tom: "neutral" };
  return { titulo: p.titulo(s.texto), explicacao: p.explicacao, quem: p.quem, tom: p.tom };
}

export function corDoSpi(spi: number | null): string {
  if (spi == null) return ds.chartGrey;
  if (spi >= 0.9) return ds.green;
  if (spi >= 0.7) return ds.amber;
  return ds.red;
}

export const COLUNAS_KANBAN: { chave: "planejado" | "em_andamento" | "pendente_aprovacao" | "concluida"; nome: string; cor: string }[] = [
  { chave: "planejado", nome: "Planejado", cor: ds.muted },
  { chave: "em_andamento", nome: "Em andamento", cor: ds.amber },
  { chave: "pendente_aprovacao", nome: "Pendente de aprovação", cor: ds.violet },
  { chave: "concluida", nome: "Concluída", cor: ds.green },
];

export function num(x: number, casas = 2): string {
  return x.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

export function pts(x: number): string {
  return Number.isInteger(x) ? String(x) : num(x, 1);
}
