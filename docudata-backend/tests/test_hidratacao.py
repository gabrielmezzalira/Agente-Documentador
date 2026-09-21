from services.hidratacao import calcular_hidratacao


def test_task_completa_nao_e_rascunho():
    task = {"titulo": "Fazer X", "pontos": 3, "descricao": "detalhe", "checklist": [{"texto": "a", "done": False}]}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is False
    assert motivo is None


def test_task_sem_descricao_nem_checklist_e_rascunho_com_motivo():
    task = {"titulo": "Fazer X", "pontos": 3, "descricao": None, "checklist": []}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is True
    assert motivo == "Faltam: descrição, checklist"


def test_task_sem_pontos_e_rascunho():
    task = {"titulo": "Fazer X", "pontos": 0, "descricao": "detalhe", "checklist": [{"texto": "a", "done": False}]}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is True
    assert motivo == "Faltam: pontos"


def test_task_sem_titulo_e_rascunho():
    task = {"titulo": "", "pontos": 3, "descricao": "detalhe", "checklist": [{"texto": "a", "done": False}]}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is True
    assert motivo == "Faltam: título"
