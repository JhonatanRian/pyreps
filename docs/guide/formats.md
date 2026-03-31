# Formatos de Saída

O **py-reports** suporta três formatos de saída, todos configuráveis via `ReportSpec.metadata`.

## CSV

O formato mais simples e performático. Streaming puro — memória constante.

```python
spec = ReportSpec(
    output_format="csv",
    columns=[...],
    metadata={
        "csv": {
            "delimiter": ";",  # padrão: ","
        }
    },
)
```

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `delimiter` | `str` | `","` | Separador de campos |

---

## XLSX

Gerado via **Rust** (`rustpy-xlsxwriter`) com suporte a largura automática de colunas.

### Exemplo Completo

```python
spec = ReportSpec(
    output_format="xlsx",
    columns=[...],
    metadata={
        "xlsx": {
            "width_mode": "mixed",
            "default_width": 14.0,
            "auto_padding": 2.0,
            "sheet_name": "Relatório",
            "columns": {
                "Descrição": {"min_width": 20.0, "max_width": 50.0},
                "ID": {"width": 8.0},
            },
        }
    },
)
```

### Opções Globais

| Opção | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `width_mode` | `str` | `"mixed"` | Modo de cálculo de largura |
| `default_width` | `float` | `12.0` | Largura padrão (modo manual) |
| `auto_padding` | `float` | `1.5` | Padding extra (modo auto) |
| `sheet_name` | `str` | `"Report"` | Nome da aba |
| `columns` | `dict` | `{}` | Config por coluna |

### Modos de Largura

=== "manual"

    Todas as colunas usam `default_width`, exceto as que têm `width` explícito.

    ```python
    {"width_mode": "manual", "default_width": 15.0}
    ```

=== "auto"

    Calcula largura baseada no maior conteúdo de cada coluna.

    ```python
    {"width_mode": "auto", "auto_padding": 2.0}
    ```

=== "mixed (recomendado)"

    Usa `width` explícito quando definido, senão calcula automaticamente.

    ```python
    {
        "width_mode": "mixed",
        "columns": {"ID": {"width": 8.0}}  # ID fixo, resto auto
    }
    ```

### Opções por Coluna

| Opção | Tipo | Descrição |
|-------|------|-----------|
| `width` | `float` | Largura fixa (override) |
| `min_width` | `float` | Largura mínima |
| `max_width` | `float` | Largura máxima |

---

## PDF

Gerado via **ReportLab** em orientação paisagem A4 com tabela estilizada.

```python
spec = ReportSpec(
    output_format="pdf",
    columns=[
        ColumnSpec(label="ID", source="id", type="int"),
        ColumnSpec(label="Nome", source="nome"),
        ColumnSpec(label="Total", source="total", type="float",
                   formatter=lambda v: f"R$ {v:.2f}"),
    ],
)
```

!!! info "Características do PDF"
    - **Orientação**: Paisagem (A4)
    - **Cabeçalho**: Azul (#2563EB) com texto branco em negrito
    - **Linhas alternadas**: Branco / cinza claro (#F1F5F9)
    - **Largura de colunas**: Proporcional ao conteúdo (automática)

!!! warning "Performance"
    O PDF **materializa todos os dados** em memória (necessário para layout de tabela).
    Para datasets muito grandes (>50K linhas), prefira CSV ou XLSX.
