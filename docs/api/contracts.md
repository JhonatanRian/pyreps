# ColumnSpec & ReportSpec

Core contracts that define the structure and behavior of the report.

## ColumnSpec

::: {{ project_name }}.contracts.ColumnSpec

## ColumnType

```python
ColumnType = Literal["str", "int", "float", "bool", "date", "datetime"]
```

See [Declarative Types](../guide/types.md) for coercion details.

## ReportSpec

::: {{ project_name }}.contracts.ReportSpec

## Auxiliary Types

```python
OutputFormat = Literal["csv", "xlsx", "pdf"]
Record = Mapping[str, Any]
Formatter = Callable[[Any], Any]
```
