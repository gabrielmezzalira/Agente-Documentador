import pytest
from services.status_projeto import sinais_do_projeto, status_de, motivos, diagnostico

BASE = dict(spi_atual=0.95, spis_recentes=[0.95, 0.92, 0.91], prazo_escopo={"sem_dados": False, "pct_prazo_consumido": 40.0, "pct_escopo_concluido": 35.0},
            tolerancia=20, ultima_fechada={"meta_total": 2, "meta_entregues": 2}, travadas=0,
            tem_meta_atual=True, tem_planejamento_atual=True, tem_gerente=True, tem_sprint=True)

def caso(**kw):
    d = dict(BASE); d.update(kw); return d

def codigos(d):
    return [s["codigo"] for s in sinais_do_projeto(d)]

def test_saudavel():
    s = sinais_do_projeto(caso())
    assert s == [] and status_de(s) == "saudavel"

@pytest.mark.parametrize("kw,cod,status", [
    (dict(spi_atual=0.33), "spi_critico", "critico"),
    (dict(prazo_escopo={"sem_dados": False, "pct_prazo_consumido": 95.0, "pct_escopo_concluido": 0.0}), "prazo", "critico"),
    (dict(ultima_fechada={"meta_total": 3, "meta_entregues": 1}), "meta_ruim", "critico"),
    (dict(travadas=5), "travadas", "critico"),
    (dict(travadas=2), "travadas", "atencao"),
    (dict(spi_atual=0.85, spis_recentes=[0.85, 0.8, 0.88]), "spi_caindo", "atencao"),
    (dict(tem_meta_atual=False), "sem_meta", "atencao"),
    (dict(tem_planejamento_atual=False), "sem_planejamento", "sem_dados"),
    (dict(prazo_escopo={"sem_dados": True}), "sem_datas", "sem_dados"),
    (dict(tem_gerente=False), "sem_gerente", "sem_dados"),
    (dict(tem_sprint=False, spi_atual=None, spis_recentes=[], tem_meta_atual=False, tem_planejamento_atual=False), "sem_sprint", "sem_dados"),
])
def test_sinal_e_status(kw, cod, status):
    s = sinais_do_projeto(caso(**kw))
    assert cod in [x["codigo"] for x in s]
    assert status_de(s) == status

def test_spi_caindo_exige_tres_sprints_abaixo_de_09():
    assert "spi_caindo" not in codigos(caso(spi_atual=0.85, spis_recentes=[0.85, 0.95, 0.8]))
    assert "spi_caindo" not in codigos(caso(spi_atual=0.85, spis_recentes=[0.85, 0.8]))

def test_meta_ruim_ignora_sprint_sem_meta():
    assert "meta_ruim" not in codigos(caso(ultima_fechada={"meta_total": 0, "meta_entregues": 0}))
    assert "meta_ruim" not in codigos(caso(ultima_fechada={"meta_total": 2, "meta_entregues": 1}))  # 50% não dispara

def test_sem_sprint_nao_gera_sem_meta_nem_sem_planejamento():
    c = codigos(caso(tem_sprint=False, spi_atual=None, spis_recentes=[], tem_meta_atual=False, tem_planejamento_atual=False))
    assert "sem_meta" not in c and "sem_planejamento" not in c

def test_textos_e_prioridade_dos_motivos():
    s = sinais_do_projeto(caso(spi_atual=0.33, travadas=6, tem_meta_atual=False, tem_gerente=False,
                               prazo_escopo={"sem_dados": False, "pct_prazo_consumido": 95.0, "pct_escopo_concluido": 0.0}))
    assert motivos(s) == ["SPI 0,33", "95% do prazo · 0% entregue"]
    textos = {x["codigo"]: x["texto"] for x in s}
    assert textos["travadas"] == "6 travadas"
    assert textos["sem_meta"] == "sem meta"
    assert textos["sem_gerente"] == "sem gerente"

def test_diagnostico():
    s = sinais_do_projeto(caso(spi_atual=0.33, tem_gerente=False))
    txt = diagnostico(status_de(s), s)
    assert txt.startswith("Crítico.")
    assert "SPI 0,33" in txt
    assert txt.endswith("Falta preencher: sem gerente.")
    assert diagnostico("saudavel", []) == "Saudável."
