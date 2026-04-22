# Fontes de Dados

O **py-reports** aceita dados de múltiplas fontes via adapters. A detecção é automática para os tipos mais comuns.

## list[dict] — ListDictAdapter

A forma mais direta. Aceita qualquer iterável de dicts:

```python
data = [
    {"id": 1, "nome": "Ana"},
    {"id": 2, "nome": "Bruno"},
]

generate_report(data_source=data, spec=spec, destination="out.csv")
```

!!! tip "Generators"
    Aceita generators e iteráveis lazy — perfeito para processar dados sob demanda:

    ```python
    def fetch_records():
        for page in api.paginate():
            yield from page["items"]

    generate_report(data_source=fetch_records(), spec=spec, destination="out.csv")
    ```

## JSON — JsonAdapter

Aceita strings JSON, bytes, dicts e listas. Parsing via **orjson** (Rust, ~6x mais rápido que stdlib).

=== "String JSON"

    ```python
    payload = '[{"id": 1, "nome": "Ana"}, {"id": 2, "nome": "Bruno"}]'
    generate_report(data_source=payload, spec=spec, destination="out.csv")
    ```

=== "Objeto com items"

    ```python
    # Extrai automaticamente a chave "items"
    payload = '{"total": 2, "items": [{"id": 1}, {"id": 2}]}'
    generate_report(data_source=payload, spec=spec, destination="out.csv")
    ```

=== "Objeto único"

    ```python
    payload = '{"id": 1, "nome": "Ana"}'  # wrap automático em lista
    generate_report(data_source=payload, spec=spec, destination="out.csv")
    ```

## JSON Streaming — JsonStreamingAdapter

Para arquivos JSON gigantescos (500MB+) ou streams I/O, utilize o `JsonStreamingAdapter`. Ele utiliza a biblioteca **ijson** para ler o arquivo iterativamente, mantendo o consumo de memória constante.

```python
from py_reports import JsonStreamingAdapter, generate_report

# Lendo de um caminho de arquivo
generate_report(
    data_source="gigante.json",
    spec=spec,
    destination="out.csv",
    input_adapter=JsonStreamingAdapter(item_path="item")
)

# Lendo de um stream binário (ex: file object aberto em 'rb')
with open("dump.json", "rb") as f:
    generate_report(
        data_source=f,
        spec=spec,
        destination="out.xlsx",
        input_adapter=JsonStreamingAdapter()
    )
```

!!! info "Caminhos ijson (item_path)"
    O parâmetro `item_path` define onde os registros estão localizados no JSON:
    - `"item"`: Para um array na raiz `[{}, {}]`.
    - `"data.item"`: Para um array dentro de uma chave `{"data": [{}, {}]}`.

## SQL — SqlAdapter

Para queries SQL, use o `SqlAdapter` explicitamente:

```python
import sqlite3
from py_reports import SqlAdapter, generate_report

conn = sqlite3.connect("app.db")

generate_report(
    data_source=None,  # dados vêm do adapter
    spec=spec,
    destination="out.csv",
    input_adapter=SqlAdapter(
        query="SELECT id, name, total FROM orders WHERE status = 'active'",
        connection=conn,
    ),
)
```

!!! note "Streaming do cursor"
    O `SqlAdapter` itera sobre o cursor SQL sem chamar `fetchall()` —
    ideal para queries que retornam muitos registros.

## Custom Adapter

Implemente o protocolo `InputAdapter` para qualquer fonte de dados:

```python
from collections.abc import Iterable, Mapping
from typing import Any

from py_reports.contracts import InputAdapter, Record


class MongoAdapter(InputAdapter):
    def __init__(self, collection, query: dict):
        self._collection = collection
        self._query = query

    def adapt(self, data_source: Any) -> Iterable[Record]:
        for doc in self._collection.find(self._query):
            yield doc  # MongoDB docs já são dicts
```

```python
generate_report(
    data_source=None,
    spec=spec,
    destination="out.xlsx",
    input_adapter=MongoAdapter(db.orders, {"status": "active"}),
)
```

## Detecção Automática

| Tipo do `data_source` | Adapter selecionado |
|----------------------|---------------------|
| `str`, `bytes`, `bytearray` | `JsonAdapter` |
| `dict` (Mapping) | `JsonAdapter` |
| Qualquer `Iterable` | `ListDictAdapter` |
| Outro | Erro — passe `input_adapter` explicitamente |
