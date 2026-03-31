## py-reports

Biblioteca para gerar relatórios a partir de entradas versáteis com saída em `csv`, `xlsx` e `pdf`.

### Arquitetura

- `InputAdapter` (Strategy/Adapter): normaliza fonte de dados para registros.
- `ReportSpec` e `ColumnSpec` (DTO/config): definem colunas, labels e mapeamento.
- Pipeline: `adapt -> map/validate -> render`.
- `Renderer` (Strategy): cada formato implementa seu renderizador.

### Formatos e adapters disponíveis

| Componente | Status |
|---|---|
| `ListDictAdapter` | ✅ |
| `JsonAdapter` | ✅ |
| `CsvRenderer` | ✅ |
| `XlsxRenderer` | ✅ |
| `PdfRenderer` | ✅ |
| `SqlAdapter` | 🔜 |

### Exemplo rápido

```python
from py_reports import ColumnSpec, ReportSpec, generate_report

data = [
    {"id": "1", "cliente": {"nome": "Ana"}, "total": 100.5},
    {"id": "2", "cliente": {"nome": "Bruno"}, "total": 250.0},
]

spec = ReportSpec(
    output_format="csv",  # ou "xlsx" ou "pdf"
    columns=[
        ColumnSpec(label="ID", source="id", required=True),
        ColumnSpec(label="Cliente", source="cliente.nome", required=True),
        ColumnSpec(label="Total", source="total", formatter=lambda v: f"{v:.2f}"),
    ],
)

generate_report(data_source=data, spec=spec, destination="reports/vendas.csv")
```

### CSV — opções

Use `metadata` para configurar o delimitador:

```python
spec = ReportSpec(
    output_format="csv",
    columns=[
        ColumnSpec(label="ID", source="id"),
        ColumnSpec(label="Cliente", source="cliente.nome"),
    ],
    metadata={"csv": {"delimiter": ";"}},
)
```

### XLSX — opções de largura de coluna

O renderer XLSX suporta três modos via `metadata`:

```python
spec = ReportSpec(
    output_format="xlsx",
    columns=[...],
    metadata={
        "xlsx": {
            "width_mode": "mixed",   # "manual" | "auto" | "mixed"
            "default_width": 14.0,
            "auto_padding": 2.0,
            "sheet_name": "Vendas",
            "columns": {
                "Descrição": {"min_width": 20.0, "max_width": 50.0},
                "ID": {"width": 8.0},
            },
        }
    },
)
```

| Modo | Comportamento |
|---|---|
| `manual` | Usa `default_width` para todas as colunas (ou a largura explícita por coluna) |
| `auto` | Calcula a largura com base no maior conteúdo de cada coluna |
| `mixed` | Usa largura explícita quando definida, senão calcula automaticamente |

### PDF

O renderer PDF gera um arquivo em orientação paisagem (A4) com uma tabela estilizada.
Basta usar `output_format="pdf"`:

```python
spec = ReportSpec(
    output_format="pdf",
    columns=[
        ColumnSpec(label="ID", source="id", required=True),
        ColumnSpec(label="Cliente", source="nome", required=True),
        ColumnSpec(label="Total", source="total", formatter=lambda v: f"R$ {v:.2f}"),
    ],
)

generate_report(data_source=data, spec=spec, destination="reports/vendas.pdf")
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

- Adicionar `SqlAdapter` (`query + connection`) para banco de dados.
- Incluir validação mais rica de tipos por coluna.
