from services.discovery_redacao import (
    TRANSCRICAO_MAX_BYTES, limitar_trecho, redigir_estrutura, redigir_segredos,
)

# Valores montados em pedaços para não parecerem segredos reais a scanners.
CHAVE_GOOGLE = "AIza" + "x" * 35
CHAVE_SK = "sk-" + "a" * 24
TOKEN_GH = "ghp_" + "b" * 36
JWT = "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12


def test_redige_chaves_conhecidas():
    texto = f"use {CHAVE_GOOGLE} e {CHAVE_SK} e {TOKEN_GH} e {JWT} ok"
    saida, redigiu = redigir_segredos(texto)
    assert redigiu is True
    for segredo in (CHAVE_GOOGLE, CHAVE_SK, TOKEN_GH, JWT):
        assert segredo not in saida
    assert saida.startswith("use ") and saida.endswith(" ok")


def test_redige_atribuicoes_de_senha_e_token():
    saida, redigiu = redigir_segredos("a senha: hunter2 e o token=abc123xyz foram ditos")
    assert redigiu is True
    assert "hunter2" not in saida and "abc123xyz" not in saida


def test_redige_chave_privada_em_bloco():
    bloco = "-----BEGIN PRIVATE KEY-----\nMIIEvQ\n-----END PRIVATE KEY-----"
    saida, redigiu = redigir_segredos(f"antes {bloco} depois")
    assert redigiu is True and "MIIEvQ" not in saida


def test_texto_comum_nao_muda():
    texto = "Precisamos integrar o ERP e exportar o relatório mensal."
    saida, redigiu = redigir_segredos(texto)
    assert saida == texto and redigiu is False


def test_redigir_estrutura_percorre_dict_e_listas():
    entrada = {"resumo": f"chave {CHAVE_GOOGLE}", "itens": [{"t": "senha: segredo1"}, 3, None]}
    saida = redigir_estrutura(entrada)
    assert CHAVE_GOOGLE not in str(saida) and "segredo1" not in str(saida)
    assert saida["itens"][1] == 3 and saida["itens"][2] is None


def test_limitar_trecho_corta_e_marca():
    assert limitar_trecho("a" * 700, 600) == "a" * 600 + "…"
    assert limitar_trecho("curto", 600) == "curto"


def test_teto_da_transcricao_e_2mb():
    assert TRANSCRICAO_MAX_BYTES == 2 * 1024 * 1024


# --- Fix round 1 ---
import time

AWS = "AKIA" + "Q" * 16
SLACK = "xox" + "b-" + "1" * 12 + "-" + "z" * 10
BEARER = "Bearer " + "t" * 20
URL_PWD = "pa55" + "w0rd"


def test_nomes_compostos_de_segredo_sao_redigidos():
    for nome in ("access_token", "client_secret", "SECRET_KEY", "AWS_SECRET_ACCESS_KEY"):
        saida, redigiu = redigir_segredos(f"x {nome}=valor123 y")
        assert redigiu is True and "valor123" not in saida, nome


def test_chave_privada_sem_end_nao_trava():
    entrada = "-----BEGIN PRIVATE KEY-----" * 55000
    t0 = time.perf_counter()
    saida, redigiu = redigir_segredos(entrada)
    assert time.perf_counter() - t0 < 2
    assert redigiu is True and "BEGIN" not in saida


def test_formatos_comuns_sao_redigidos():
    texto = f"Authorization: {BEARER} db postgres://user:{URL_PWD}@host/db {AWS} {SLACK}"
    saida, redigiu = redigir_segredos(texto)
    assert redigiu is True
    for segredo in ("t" * 20, URL_PWD, AWS, SLACK):
        assert segredo not in saida
    assert "postgres://user:" in saida and "@host/db" in saida


def test_limitar_trecho_no_limite():
    assert limitar_trecho("a" * 600, 600) == "a" * 600
    assert limitar_trecho("a" * 601, 600).endswith("…")


def test_redigir_estrutura_nao_muta_a_entrada():
    entrada = {"a": [f"chave {CHAVE_GOOGLE}"], "b": {"c": "senha: xyz"}}
    copia = {"a": [f"chave {CHAVE_GOOGLE}"], "b": {"c": "senha: xyz"}}
    redigir_estrutura(entrada)
    assert entrada == copia


def test_entradas_patologicas_sao_lineares():
    for entrada in ("token" * 300_000, "a" * 1_500_000, "password" * 190_000, "pwd_" * 400_000):
        t0 = time.perf_counter()
        redigir_segredos(entrada)
        assert time.perf_counter() - t0 < 2
