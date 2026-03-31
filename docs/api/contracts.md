# ColumnSpec & ReportSpec

Contratos centrais que definem a estrutura e o comportamento do relatório.

## ColumnSpec

::: py_reports.contracts.ColumnSpec

## ColumnType

```python
ColumnType = Literal["str", "int", "float", "bool", "date", "datetime"]
```

Veja [Tipos Declarativos](../guide/types.md) para detalhes de coerção.

## ReportSpec

::: py_reports.contracts.ReportSpec

## Tipos Auxiliares

```python
OutputFormat = Literal["csv", "xlsx", "pdf"]
Record = Mapping[str, Any]
Formatter = Callable[[Any], Any]
```
