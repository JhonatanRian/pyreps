## py-reports

Biblioteca para gerar relatórios a partir de entradas versáteis com saída em `csv`, `xlsx` e `pdf`.

### Arquitetura (v1)

- `InputAdapter` (Strategy/Adapter): normaliza fonte de dados para registros.
- `ReportSpec` e `ColumnSpec` (DTO/config): definem colunas, labels e mapeamento.
- Pipeline: `adapt -> map/validate -> render`.
- `Renderer` (Strategy): cada formato implementa seu renderizador.

Implementado agora:
- `ListDictAdapter`
- `JsonAdapter`
- `CsvRenderer`

Scaffold criado:
- `XlsxRenderer` (não implementado)
- `PdfRenderer` (não implementado)

### Exemplo rápido

```python
from py_reports import ColumnSpec, ReportSpec, generate_report

data = [
    {"id": "1", "cliente": {"nome": "Ana"}, "total": 100.5},
    {"id": "2", "cliente": {"nome": "Bruno"}, "total": 250.0},
]

spec = ReportSpec(
    output_format="csv",
    columns=[
        ColumnSpec(label="ID", source="id", required=True),
        ColumnSpec(label="Cliente", source="cliente.nome", required=True),
        ColumnSpec(label="Total", source="total", formatter=lambda v: f"{v:.2f}"),
    ],
)

generate_report(data_source=data, spec=spec, destination="reports/vendas.csv")
```

### Usando com JSON

```python
json_payload = """
[
  {"id":"1","cliente":{"nome":"Ana"},"total":100.5},
  {"id":"2","cliente":{"nome":"Bruno"},"total":250.0}
]
"""

generate_report(data_source=json_payload, spec=spec, destination="reports/vendas.csv")
```

### Próximos passos

- Implementar renderização real de `xlsx` e `pdf`.
- Adicionar adapter SQL (`query + connection`) para banco de dados.
- Incluir validação mais rica de tipos por coluna.
