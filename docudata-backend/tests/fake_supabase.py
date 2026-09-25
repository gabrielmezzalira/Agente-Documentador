"""Supabase em memória para testes de rota — cobre só o subconjunto da API
usado pelos routers (select/eq/in_/order/limit/insert/update)."""


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, tables, name, op, payload=None):
        self._tables = tables
        self._name = name
        self._op = op
        self._payload = payload
        self._filtros = []
        self._ordem = None
        self._limite = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, col, val):
        self._filtros.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        conjunto = set(vals)
        self._filtros.append(lambda r: r.get(col) in conjunto)
        return self

    def order(self, col, desc=False):
        self._ordem = (col, desc)
        return self

    def limit(self, n):
        self._limite = n
        return self

    def execute(self):
        linhas = self._tables.setdefault(self._name, [])
        if self._op == "insert":
            itens = self._payload if isinstance(self._payload, list) else [self._payload]
            saida = []
            for item in itens:
                row = dict(item)
                row.setdefault("id", f"{self._name}-{len(linhas) + 1}")
                linhas.append(row)
                saida.append(dict(row))
            return _Resp(saida)
        casadas = [r for r in linhas if all(f(r) for f in self._filtros)]
        if self._op == "update":
            for r in casadas:
                r.update(self._payload)
            return _Resp([dict(r) for r in casadas])
        if self._ordem:
            col, desc = self._ordem
            casadas = sorted(casadas, key=lambda r: str(r.get(col) or ""), reverse=desc)
        if self._limite is not None:
            casadas = casadas[: self._limite]
        return _Resp([dict(r) for r in casadas])


class _Table:
    def __init__(self, tables, name):
        self._tables = tables
        self._name = name

    def select(self, *_args, **_kwargs):
        return _Query(self._tables, self._name, "select")

    def insert(self, payload):
        return _Query(self._tables, self._name, "insert", payload)

    def update(self, payload):
        return _Query(self._tables, self._name, "update", payload)


class FakeClient:
    def __init__(self, tables=None):
        self.tables = {k: [dict(r) for r in v] for k, v in (tables or {}).items()}

    def table(self, name):
        return _Table(self.tables, name)
