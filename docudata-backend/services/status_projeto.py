"""Status do projeto no dashboard (B1): sinais → status, motivos e diagnóstico."""

ORDEM_STATUS = {"critico": 0, "atencao": 1, "sem_dados": 2, "saudavel": 3}
PRIORIDADE = ["spi_critico", "prazo", "meta_ruim", "travadas", "spi_caindo", "sem_meta",
              "sem_sprint", "sem_planejamento", "sem_datas", "sem_gerente"]
FALTA = {"sem_sprint", "sem_planejamento", "sem_datas", "sem_gerente"}
ROTULO = {"critico": "Crítico.", "atencao": "Atenção.", "sem_dados": "Faltam dados.", "saudavel": "Saudável."}


def _num(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".rstrip("0").rstrip(".").replace(".", ",") if casas else f"{v:.0f}"


def sinais_do_projeto(d: dict) -> list[dict]:
    s: list[dict] = []

    def add(codigo, texto):
        s.append({"codigo": codigo, "texto": texto})

    spi = d.get("spi_atual")
    if spi is not None and spi < 0.7:
        add("spi_critico", f"SPI {_num(spi)}")
    pe = d.get("prazo_escopo") or {}
    if not pe.get("sem_dados", True):
        if pe["pct_prazo_consumido"] - pe["pct_escopo_concluido"] > (d.get("tolerancia") or 0):
            add("prazo", f"{_num(pe['pct_prazo_consumido'], 0)}% do prazo · {_num(pe['pct_escopo_concluido'], 0)}% entregue")
    uf = d.get("ultima_fechada") or {}
    if uf.get("meta_total"):
        if uf["meta_entregues"] / uf["meta_total"] < 0.5:
            add("meta_ruim", f"meta da última sprint {uf['meta_entregues']}/{uf['meta_total']}")
    if d.get("travadas", 0) > 0:
        add("travadas", f"{d['travadas']} travada" + ("s" if d["travadas"] > 1 else ""))
    rec = [x for x in d.get("spis_recentes") or [] if x is not None][:3]
    if len(rec) == 3 and all(x < 0.9 for x in rec) and not any(x["codigo"] == "spi_critico" for x in s):
        add("spi_caindo", "SPI abaixo de 0,9 há 3 sprints")
    if not d.get("tem_sprint"):
        add("sem_sprint", "nenhuma sprint iniciada")
    else:
        if not d.get("tem_meta_atual"):
            add("sem_meta", "sem meta")
        if not d.get("tem_planejamento_atual"):
            add("sem_planejamento", "sem planejamento")
    if pe.get("sem_dados", True):
        add("sem_datas", "sem datas do contrato")
    if not d.get("tem_gerente"):
        add("sem_gerente", "sem gerente")
    return sorted(s, key=lambda x: PRIORIDADE.index(x["codigo"]))


def status_de(sinais: list[dict]) -> str:
    cods = {x["codigo"] for x in sinais}
    travadas = next((int(x["texto"].split()[0]) for x in sinais if x["codigo"] == "travadas"), 0)
    if cods & {"spi_critico", "prazo", "meta_ruim"} or travadas >= 5:
        return "critico"
    if cods & {"spi_caindo", "travadas", "sem_meta"}:
        return "atencao"
    if cods & FALTA:
        return "sem_dados"
    return "saudavel"


def motivos(sinais: list[dict], n: int = 2) -> list[str]:
    return [x["texto"] for x in sinais[:n]]


def diagnostico(status: str, sinais: list[dict]) -> str:
    partes = [ROTULO[status]]
    fatos = [x["texto"] for x in sinais if x["codigo"] not in FALTA]
    if fatos:
        partes.append(" · ".join(fatos) + ".")
    falta = [x["texto"] for x in sinais if x["codigo"] in FALTA]
    if falta:
        partes.append("Falta preencher: " + ", ".join(falta) + ".")
    return " ".join(partes)
