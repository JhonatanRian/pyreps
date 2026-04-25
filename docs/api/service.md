# generate_report

Main library function — the entry point for generating any report.

::: pyreps.service.generate_report

## Example

```python
from pyreps import ColumnSpec, ReportSpec, generate_report

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
