# generate_report

Função principal da biblioteca — o ponto de entrada para gerar qualquer relatório.

::: pyreps.service.generate_report

## Exemplo

```python
from pyreps import ColumnSpec, ReportSpec, generate_report

spec = ReportSpec(
    output_format="xlsx",
    columns=[
        ColumnSpec(label="ID", source="id", type="int", required=True),
        ColumnSpec(label="Nome", source="nome"),
    ],
)

path = generate_report(
    data_source=[{"id": 1, "nome": "Ana"}],
    spec=spec,
    destination="relatorio.xlsx",
)
```
