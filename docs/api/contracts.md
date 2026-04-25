# ColumnSpec & ReportSpec

Core contracts that define the structure and behavior of the report.

## ColumnSpec

::: pyreps.contracts.ColumnSpec

## ColumnType

```python
ColumnType = Literal["str", "int", "float", "bool", "date", "datetime"]
```

See [Declarative Types](../guide/types.md) for coercion details.

## ReportSpec

::: pyreps.contracts.ReportSpec

## Auxiliary Types

```python
OutputFormat = Literal["csv", "xlsx", "pdf"]
Record = Mapping[str, Any]
Formatter = Callable[[Any], Any]
```
