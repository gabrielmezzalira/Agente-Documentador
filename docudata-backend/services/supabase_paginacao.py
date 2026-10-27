"""Leitura completa de tabelas grandes: o PostgREST corta selects sem paginação (~1000 linhas)."""


def ler_tudo(montar_query, lote: int = 1000) -> list[dict]:
    """`montar_query()` devolve a query já com `.order(...)` determinístico; paginamos com `.range`."""
    saida: list[dict] = []
    ini = 0
    while True:
        pagina = montar_query().range(ini, ini + lote - 1).execute().data or []
        saida += pagina
        if len(pagina) < lote:
            return saida
        ini += lote
