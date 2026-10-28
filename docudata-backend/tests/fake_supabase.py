"""Supabase em memória para testes de rota — cobre só o subconjunto da API
usado pelos routers (select/eq/in_/order/limit/insert/update)."""


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, tables, name, op, payload=None, defaults=None, on_conflict=None):
        self._on_conflict = on_conflict
        self._defaults = defaults or {}
        self._tables = tables
        self._name = name
        self._op = op
        self._payload = payload
        self._filtros = []
        self._ordens = []
        self._limite = None
        self._faixa = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, col, val):
        self._filtros.append(lambda r: r.get(col) == val)
        return self

    def neq(self, col, val):
        self._filtros.append(lambda r: r.get(col) != val)
        return self

    def gte(self, col, val):
        """Comparação lexicográfica de strings ISO (os testes usam o mesmo formato nos dois lados)."""
        self._filtros.append(lambda r: r.get(col) is not None and str(r.get(col)) >= str(val))
        return self

    def is_(self, col, val):
        """Só o caso `.is_(col, "null")` (IS NULL), usado pelo compare-and-swap da reserva de análise."""
        if val != "null":
            raise NotImplementedError("FakeClient.is_ só suporta 'null'")
        self._filtros.append(lambda r: r.get(col) is None)
        return self

    def in_(self, col, vals):
        conjunto = set(vals)
        self._filtros.append(lambda r: r.get(col) in conjunto)
        return self

    def order(self, col, desc=False):
        self._ordens.append((col, desc))
        return self

    def range(self, ini, fim):
        self._faixa = (ini, fim)
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
                row = {**self._defaults, **item}
                row.setdefault("id", f"{self._name}-{len(linhas) + 1}")
                linhas.append(row)
                saida.append(dict(row))
            return _Resp(saida)
        if self._op == "upsert":
            chaves = [c.strip() for c in (self._on_conflict or "id").split(",")]
            itens = self._payload if isinstance(self._payload, list) else [self._payload]
            saida = []
            for item in itens:
                alvo = next((r for r in linhas if all(r.get(c) == item.get(c) for c in chaves)), None)
                if alvo is not None:
                    alvo.update(item)
                    saida.append(dict(alvo))
                else:
                    row = {**self._defaults, **item}
                    linhas.append(row)
                    saida.append(dict(row))
            return _Resp(saida)
        casadas = [r for r in linhas if all(f(r) for f in self._filtros)]
        if self._op == "delete":
            for r in casadas:
                linhas.remove(r)
            return _Resp([dict(r) for r in casadas])
        if self._op == "update":
            for r in casadas:
                r.update(self._payload)
            return _Resp([dict(r) for r in casadas])
        for col, desc in reversed(self._ordens):  # ordenações estáveis, da menos à mais significativa
            casadas = sorted(casadas, key=lambda r, c=col: str(r.get(c) or ""), reverse=desc)
        if self._faixa is not None:
            casadas = casadas[self._faixa[0]: self._faixa[1] + 1]
        if self._limite is not None:
            casadas = casadas[: self._limite]
        return _Resp([dict(r) for r in casadas])


class _Table:
    def __init__(self, tables, name, defaults=None):
        self._tables = tables
        self._name = name
        self._defaults = defaults

    def select(self, *_args, **_kwargs):
        return _Query(self._tables, self._name, "select")

    def insert(self, payload):
        return _Query(self._tables, self._name, "insert", payload, self._defaults)

    def update(self, payload):
        return _Query(self._tables, self._name, "update", payload)

    def upsert(self, payload, on_conflict=None):
        """Substitui a linha com os mesmos valores nas colunas de `on_conflict`
        ("a,b") ou insere; sem `on_conflict`, a chave é `id`."""
        return _Query(self._tables, self._name, "upsert", payload, self._defaults, on_conflict)

    def delete(self):
        return _Query(self._tables, self._name, "delete")


class _RpcQuery:
    def __init__(self, fn, params):
        self._fn = fn
        self._params = params

    def execute(self):
        return _Resp(self._fn(self._params))


class FakeClient:
    def __init__(self, tables=None, defaults=None):
        """`defaults` ({tabela: {coluna: valor}}) simula os DEFAULTs de coluna do banco nos inserts."""
        self.tables = {k: [dict(r) for r in v] for k, v in (tables or {}).items()}
        self._defaults = defaults or {}
        self.rpcs = {}

    def rpc(self, nome, params):
        """`rpcs` ({nome: função(params) -> dados}) é injetado pelo teste."""
        return _RpcQuery(self.rpcs[nome], params)

    def table(self, name):
        return _Table(self.tables, name, self._defaults.get(name))
