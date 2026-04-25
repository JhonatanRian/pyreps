<div align="center">

# pyreps

**Geração de relatórios em Python — CSV, XLSX e PDF com performance de Rust.** ⚡

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Documentação](https://pyreps.readthedocs.io/) · [PyPI](https://pypi.org/project/pyreps/) · [Issues](https://github.com/jhonatan/pyreps/issues)

</div>

---

## ✨ Destaques

- **🚀 Alta Performance** — Pipeline 100% streaming. CSV e XLSX usam < 1 MB de RAM com 500K+ linhas.
- **🦀 Powered by Rust** — XLSX via `rustpy-xlsxwriter`, JSON via `orjson`.
- **📄 3 Formatos** — CSV, XLSX e PDF com uma única API.
- **🔌 Plugável** — Aceita `list[dict]`, JSON, SQL ou qualquer fonte custom.
- **🎯 Tipos Declarativos** — Coerção automática para `int`, `float`, `bool`, `date`, `datetime`.
- **🪶 Leve** — 3 dependências de runtime. Sem pandas, sem numpy.

## Instalação

```bash
pip install pyreps
```

## Exemplo Rápido

```python
from pyreps import ColumnSpec, ReportSpec, generate_report

data = [
    {"id": 1, "cliente": {"nome": "Ana"}, "total": 100.50},
    {"id": 2, "cliente": {"nome": "Bruno"}, "total": 250.00},
]

spec = ReportSpec(
    output_format="csv",  # ou "xlsx" ou "pdf"
    columns=[
        ColumnSpec(label="ID", source="id", type="int", required=True),
        ColumnSpec(label="Cliente", source="cliente.nome"),
        ColumnSpec(label="Total", source="total", type="float",
                   formatter=lambda v: f"R$ {v:.2f}"),
    ],
)

path = generate_report(data_source=data, spec=spec, destination="vendas.csv")
```

## Formatos Suportados

| Formato | Renderer | Motor | Streaming |
|---------|----------|-------|-----------|
| CSV | `CsvRenderer` | `csv` stdlib (C) | ✅ Memória constante |
| XLSX | `XlsxRenderer` | `rustpy-xlsxwriter` (Rust) | ✅ Memória constante |
| PDF | `PdfRenderer` | `reportlab` (C) | ⚠️ Materializa (layout) |

## Fontes de Dados

| Fonte | Adapter | Detecção |
|-------|---------|----------|
| `list[dict]` / generator | `ListDictAdapter` | Automática |
| JSON string / bytes | `JsonAdapter` | Automática |
| `dict` / `Mapping` | `JsonAdapter` | Automática |
| SQL query | `SqlAdapter` | Explícito |
| Custom | Implemente `InputAdapter` | Explícito |

## Tipos Declarativos

```python
ColumnSpec(label="Criado", source="created_at", type="date")
ColumnSpec(label="Ativo", source="active", type="bool")    # "sim" → True
ColumnSpec(label="Total", source="total", type="float")     # "3.14" → 3.14
```

Tipos: `str`, `int`, `float`, `bool`, `date`, `datetime`. Opcional — `type=None` mantém pass-through.

## XLSX — Largura de Colunas

```python
spec = ReportSpec(
    output_format="xlsx",
    columns=[...],
    metadata={
        "xlsx": {
            "width_mode": "auto",     # "manual" | "auto" | "mixed"
            "sheet_name": "Vendas",
            "columns": {
                "ID": {"width": 8.0},
                "Descrição": {"min_width": 20.0, "max_width": 50.0},
            },
        }
    },
)
```

## SQL

```python
from pyreps import SqlAdapter

generate_report(
    data_source=None,
    spec=spec,
    destination="vendas.csv",
    input_adapter=SqlAdapter(
        query="SELECT id, name, total FROM sales",
        connection=connection,
    ),
)
```

## Performance

Benchmark com 6 colunas e tipos declarativos:

| Formato | 500K linhas | Peak RAM | rows/s |
|---------|------------|----------|--------|
| CSV | 15s | **0.16 MB** | ~33K |
| XLSX | 24s | **0.62 MB** | ~21K |

> CSV e XLSX mantêm memória constante independente do volume.

## Documentação

📖 Documentação completa em [pyreps.readthedocs.io](https://pyreps.readthedocs.io/)

## Licença

MIT
