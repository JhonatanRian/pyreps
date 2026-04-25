# generate_report

Main library function — the entry point for generating any report.

::: {{ project_name }}.service.generate_report

## Example

```python
from {{ project_name }} import ColumnSpec, ReportSpec, generate_report

spec = ReportSpec(
    output_format="xlsx",
    columns=[
        ColumnSpec(label="ID", source="id", type="int", required=True),
        ColumnSpec(label="Name", source="name"),
    ],
)

path = generate_report(
    data_source=[{"id": 1, "name": "Ana"}],
    spec=spec,
    destination="report.xlsx",
)
```
