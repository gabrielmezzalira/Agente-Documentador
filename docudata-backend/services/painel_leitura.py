"""Leitura para o Painel do Projeto CITi (somente leitura, sem efeito colateral).

Funções puras que transformam linhas do Supabase no formato que o painel consome
(docs/painel-api.md). Nomes em camelCase e datas ISO. Campo sem valor é OMITIDO (não vai
`null`), exceto onde o contrato diz que `null` é um valor válido (spi, saude, data).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

# coluna do kanban do DocuData -> tipo que o painel entende
_TIPO_COLUNA = {
    "planejado": "A_FAZER",
    "em_andamento": "OUTRA",
    "pendente_aprovacao": "OUTRA",
    "concluida": "CONCLUIDO",
}
_ROTULO_COLUNA = {
    "planejado": "Planejado",
    "em_andamento": "Em andamento",
    "pendente_aprovacao": "Pendente de aprovação",
    "concluida": "Concluída",
}
_PRIORIDADE = {"must": "MUST", "should": "SHOULD", "could": "COULD", "wont": "COULD"}
_SAUDE = {"verde": "VERDE", "amarelo": "AMARELO", "vermelho": "VERMELHO"}
_DOC_ATA = "ata_reuniao"
_ROTULO_DOC = {
    "repasse_semanal": "Repasse semanal",
    "retrospectiva": "Retrospectiva",
    "log_decisoes": "Log de decisões",
    "documentacao_final": "Documentação final",
    "adr": "ADR",
    "onboarding": "Onboarding",
    "planning": "Planning",
    "daily": "Daily",
    "review": "Review",
}


def _dia(valor) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _iso(valor) -> str | None:
    """Data ou instante em ISO 8601; None se vazio."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return str(valor)


def _sem_nulos(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def escolher_sprint(sprints: list[dict], numero: int | None) -> dict | None:
    """A pedida; senão a de maior número entre as iniciadas; senão a de maior número."""
    if numero is not None:
        return next((s for s in sprints if s.get("numero") == numero), None)
    if not sprints:
        return None
    iniciadas = [s for s in sprints if s.get("iniciada", True)]
    return max(iniciadas or sprints, key=lambda s: s.get("numero") or 0)


def progresso_do_checklist(checklist) -> int | None:
    itens = [i for i in (checklist or []) if isinstance(i, dict)]
    if not itens:
        return None
    return round(100 * sum(1 for i in itens if i.get("done")) / len(itens))


def concluidas_em(transicoes: list[dict]) -> dict[str, str]:
    """Instante mais recente em que cada task foi para 'concluida'."""
    melhor: dict[str, str] = {}
    for tr in transicoes:
        if tr.get("para") != "concluida":
            continue
        quando = _iso(tr.get("timestamp"))
        chave = str(tr["task_id"])
        if quando and (chave not in melhor or quando > melhor[chave]):
            melhor[chave] = quando
    return melhor


def mapear_kanban(
    tasks: list[dict],
    nomes_por_operacional: dict[str, str],
    concluida_em_por_task: dict[str, str],
) -> list[dict]:
    saida = []
    for t in tasks:
        coluna = t.get("coluna_kanban") or "planejado"
        bloqueada_cliente = bool(t.get("bloqueado_manual")) and t.get("bloqueio_tipo") == "cliente"
        saida.append(
            _sem_nulos(
                {
                    "id": str(t["id"]),
                    "titulo": t.get("titulo") or "",
                    "coluna": _ROTULO_COLUNA.get(coluna, coluna),
                    "colunaTipo": _TIPO_COLUNA.get(coluna, "OUTRA"),
                    "progresso": progresso_do_checklist(t.get("checklist")),
                    "bloqueadoPorCliente": bloqueada_cliente,
                    "bloqueadaDesde": _iso(t.get("bloqueado_em")) if bloqueada_cliente else None,
                    "concluidaEm": concluida_em_por_task.get(str(t["id"])) if coluna == "concluida" else None,
                    "responsavel": nomes_por_operacional.get(str(t.get("operacional_id") or "")),
                }
            )
        )
    return saida


def _spi(tasks_da_sprint: list[dict], previsto: int) -> tuple[float | None, int]:
    realizados = sum(
        t["pontos"] for t in tasks_da_sprint if t.get("coluna_kanban") == "concluida" and not t.get("extra")
    )
    spi = round(realizados / previsto, 2) if previsto > 0 else None
    return spi, realizados


def _saude_pelo_spi(spi: float | None) -> str | None:
    if spi is None:
        return None
    if spi >= 0.9:
        return "VERDE"
    return "AMARELO" if spi >= 0.7 else "VERMELHO"


def mapear_indicadores(
    projeto: dict,
    sprint: dict,
    tasks_da_sprint: list[dict],
    tasks_do_projeto: list[dict],
    previsto: int,
    hoje: date,
) -> dict:
    inicio_proj = _dia(projeto.get("data_inicio"))
    fim_proj = _dia(projeto.get("data_fim_contratada"))
    numero = int(sprint["numero"])

    # Cada sprint dura uma semana: sem datas na sprint, deriva do início do contrato.
    inicio = _dia(sprint.get("data_inicio"))
    fim = _dia(sprint.get("data_fim"))
    if inicio is None and inicio_proj is not None:
        inicio = inicio_proj + timedelta(days=7 * (numero - 1))
    if fim is None and inicio is not None:
        fim = inicio + timedelta(days=6)

    if inicio_proj and fim_proj and fim_proj > inicio_proj:
        total = max(numero, -(-((fim_proj - inicio_proj).days + 1) // 7))
        consumido = (hoje - inicio_proj).days / (fim_proj - inicio_proj).days
        prazo = max(0, min(100, round(100 * consumido)))
    else:
        total, prazo = numero, 0

    do_escopo = [t for t in tasks_do_projeto if not t.get("extra")]
    pontos_total = sum(t["pontos"] for t in do_escopo)
    pontos_feitos = sum(t["pontos"] for t in do_escopo if t.get("coluna_kanban") == "concluida")
    escopo = round(100 * pontos_feitos / pontos_total) if pontos_total else 0

    spi, realizados = _spi(tasks_da_sprint, previsto)
    saude = _SAUDE.get(sprint.get("status_saude") or "") or _saude_pelo_spi(spi)
    tolerancia = projeto.get("tolerancia_desvio_pontos")

    return {
        "sprintNumero": numero,
        "sprintTotal": total,
        "inicio": _iso(inicio),
        "fim": _iso(fim),
        "prazoConsumidoPct": prazo,
        "escopoConcluidoPct": escopo,
        "spi": spi,  # null: a sprint não tem pontos previstos
        "desvioPontos": realizados - previsto,
        "toleranciaPct": 20 if tolerancia is None else tolerancia,
        "saude": saude,  # null: sem saúde manual e sem pontos previstos
    }


def mapear_escopo(funcionalidades: list[dict], sprints: list[dict]) -> list[dict]:
    fim_por_numero = {str(s["numero"]): _iso(_dia(s.get("data_fim"))) for s in sprints}
    saida = []
    for f in funcionalidades:
        concluida = f.get("status") == "concluida"
        saida.append(
            {
                "id": str(f["id"]),
                "codigo": f.get("id_funcional") or "",
                "nome": f.get("titulo") or "",
                "prioridade": _PRIORIDADE.get(f.get("prioridade") or "", "SHOULD"),
                # null: sem sprint alvo com data. O DocuData não guarda data por funcionalidade.
                "data": fim_por_numero.get(str(f.get("sprint_alvo") or "").strip()),
                # O DocuData só sabe se a funcionalidade inteira concluiu, não critério a critério.
                "criterios": [{"texto": c, "atendido": concluida} for c in (f.get("criterios_aceite") or [])],
            }
        )
    return saida


def _titulo_ata(conteudo: str, data) -> str:
    for linha in (conteudo or "").splitlines():
        limpo = linha.strip().lstrip("#").strip()
        if limpo:
            return limpo[:200]
    return f"Ata de {_iso(_dia(data)) or 'data desconhecida'}"


def mapear_atas(docs: list[dict]) -> list[dict]:
    return [
        {
            "id": str(d["id"]),
            "data": _iso(d.get("created_at")),
            "titulo": _titulo_ata(d.get("content") or "", d.get("created_at")),
            "markdown": d.get("content") or "",
        }
        for d in docs
        if d.get("doc_type") == _DOC_ATA
    ]


def mapear_documentos(docs: list[dict]) -> list[dict]:
    saida = []
    for d in docs:
        tipo = d.get("doc_type") or ""
        if tipo == _DOC_ATA:
            continue  # as atas têm rota própria
        nome = _ROTULO_DOC.get(tipo) or tipo.replace("_", " ").capitalize() or "Documento"
        sprint = d.get("sprint_number")
        saida.append(
            _sem_nulos(
                {
                    "id": str(d["id"]),
                    "nome": f"{nome} · sprint {sprint}" if sprint is not None else nome,
                    "ext": "MD",
                    "data": _iso(d.get("created_at")),
                    "tamanhoBytes": len((d.get("content") or "").encode("utf-8")),
                }
            )
        )
    return saida


def mapear_pessoas(operacionais: list[dict]) -> list[dict]:
    return [
        {"id": str(o["id"]), "nome": o.get("nome") or "", "papel": o.get("papel") or "Operacional"}
        for o in operacionais
        if o.get("ativo", True)
    ]


def contar_commits(linhas: list[dict], desde: datetime, ate: datetime) -> int:
    """Commits analisados (`commit_qualidade`) com `criado_em` em [desde, ate] (instantes com fuso)."""
    n = 0
    for linha in linhas:
        quando = linha.get("criado_em")
        if quando is None:
            continue
        try:
            instante = datetime.fromisoformat(str(quando).replace("Z", "+00:00"))
        except ValueError:
            continue
        if instante.tzinfo is None:
            continue
        if desde <= instante <= ate:
            n += 1
    return n
