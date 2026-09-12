from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from models.schemas import ResumoSemanalRequest
from routers.painel import calcular_bloco_a, calcular_bloco_b
from services.supabase_client import get_client

router = APIRouter(prefix="/boletins", tags=["boletins"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/resumo_semanal")
async def gerar_resumo_semanal(body: ResumoSemanalRequest):
    """Gera resumo semanal de anomalias do projeto de forma determinística, sem Gemini.

    M8 (§5): listagem estruturada — sem custo de token, zero risco de hallucination.
    D-08: markdown estruturado puro.
    D-09: período dom–sáb da semana em curso.
    D-10: salvo em generated_docs com doc_type='resumo_semanal', sprint_number=None.
    §4.5 (RevisaoDiaria): achados críticos de revisoes_diarias via calcular_bloco_b.

    IMPORTANTE: esta rota NÃO chama Gemini em nenhuma hipótese (RESEARCH Pitfall 6).
    """
    client = get_client()
    project_id = body.project_id

    # Buscar projeto (404 se não existe)
    proj_resp = (
        client.table("projects")
        .select("id, name, client, data_inicio, data_fim_contratada, tolerancia_desvio_pontos")
        .eq("id", project_id)
        .execute()
    )
    if not proj_resp.data:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    projeto = proj_resp.data[0]

    # Calcular período da semana atual (D-09 — dom–sáb)
    # weekday() retorna 0=seg, 6=dom; (weekday+1)%7 calcula dias desde o domingo
    hoje = date.today()
    dias_desde_domingo = (hoje.weekday() + 1) % 7
    inicio_semana = hoje - timedelta(days=dias_desde_domingo)
    fim_semana = inicio_semana + timedelta(days=6)

    # Buscar dados para cálculo das anomalias (replicar queries de painel.py)
    funcs_resp = (
        client.table("funcionalidades")
        .select("*")
        .eq("project_id", project_id)
        .execute()
    )
    funcs = funcs_resp.data or []

    func_ids = [f["id"] for f in funcs]

    # Buscar transições de status (necessário para calcular_bloco_b)
    if func_ids:
        transicoes_resp = (
            client.table("transicoes_status")
            .select("*")
            .in_("funcionalidade_id", func_ids)
            .execute()
        )
        transicoes = transicoes_resp.data or []
    else:
        transicoes = []

    # Buscar revisão diária mais recente (§4.5 RevisaoDiaria — achados críticos)
    revisao_resp = (
        client.table("revisoes_diarias")
        .select("*")
        .eq("project_id", project_id)
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )
    revisao_recente = revisao_resp.data[0] if revisao_resp.data else None

    # Calcular blocos reutilizando funções de painel.py (Don't Hand-Roll)
    bloco_a = calcular_bloco_a(projeto, funcs)
    bloco_b = calcular_bloco_b(funcs, transicoes, revisao_recente)

    # Montar markdown estruturado — determinístico, sem Gemini (D-08)
    periodo_str = f"{inicio_semana.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}"
    project_name = projeto.get("name", project_id)

    linhas: list[str] = [
        f"# Resumo Semanal — {project_name} — {periodo_str}",
        f"_Gerado em: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}_",
        "",
    ]

    # Verificar se há qualquer anomalia
    travadas = bloco_b.get("travadas") or []
    achados_criticos = bloco_b.get("achados_criticos") or []

    tem_anomalia = bool(travadas or achados_criticos)

    if not tem_anomalia:
        # Sem anomalias — declarar explicitamente (D-08, must_haves D-10)
        linhas.append("## Status")
        linhas.append("Nenhuma anomalia identificada nesta semana.")
    else:
        # Seção: Funcionalidades Travadas (status=em_andamento > 7 dias)
        if travadas:
            linhas.append("## Funcionalidades Travadas")
            for item in travadas:
                titulo = item.get("titulo", item.get("id", ""))
                dias = item.get("dias", "?")
                linhas.append(f"- **{titulo}** — em andamento há {dias} dias")
            linhas.append("")

        # Seção: Achados Críticos de Revisão de Código (§4.5 RevisaoDiaria)
        if achados_criticos:
            linhas.append("## Achados Críticos (Revisão de Código)")
            for achado in achados_criticos:
                descricao = achado.get("descricao") or achado.get("titulo") or str(achado)
                severidade = achado.get("severidade", "")
                linhas.append(f"- [{severidade}] {descricao}")
            linhas.append("")

    # Seção: Leitura Tempo × Escopo (bloco_a — opcional, depende de datas de contrato)
    linhas.append("## Leitura Tempo × Escopo")
    if bloco_a.get("sem_dados"):
        linhas.append("Datas de contrato não configuradas — sem leitura de tempo × escopo")
    else:
        linhas.append(f"% prazo consumido: {bloco_a.get('pct_prazo_consumido', 'N/A')}%")
        linhas.append(f"% escopo concluído: {bloco_a.get('pct_escopo_concluido', 'N/A')}%")

    markdown_content = "\n".join(linhas)

    # Salvar em generated_docs (D-10): doc_type='resumo_semanal', sprint_number=None
    client.table("generated_docs").insert(
        {
            "project_id": project_id,
            "doc_type": "resumo_semanal",
            "sprint_number": None,
            "content": markdown_content,
        }
    ).execute()

    return {"content": markdown_content}
