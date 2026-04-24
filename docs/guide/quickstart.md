# Início Rápido

## Instalação

=== "pip"

    ```bash
    pip install pyreps
    ```

=== "uv"

    ```bash
    uv add pyreps
    ```

=== "poetry"

    ```bash
    poetry add pyreps
    ```

## Conceitos Básicos

O **pyreps** funciona em 3 passos:

1. **Definir colunas** com `ColumnSpec` — o que extrair e como formatar.
2. **Criar a spec** com `ReportSpec` — formato de saída e metadados.
3. **Gerar** com `generate_report` — passar os dados e o destino.

```mermaid
graph LR
    A["Seus Dados"] --> B["ColumnSpec[]"]
    B --> C["ReportSpec"]
    C --> D["generate_report()"]
    D --> E["📄 Arquivo"]
```

## Gerando um CSV

```python
from py_reports import ColumnSpec, ReportSpec, generate_report

data = [
    {"id": 1, "nome": "Ana Silva", "valor": 1500.00},
    {"id": 2, "nome": "Bruno Costa", "valor": 3200.50},
    {"id": 3, "nome": "Carla Lima", "valor": 890.75},
]

spec = ReportSpec(
    output_format="csv",
    columns=[
        ColumnSpec(label="ID", source="id", type="int", required=True),
        ColumnSpec(label="Nome", source="nome", type="str"),
        ColumnSpec(label="Valor", source="valor", type="float",
                   formatter=lambda v: f"R$ {v:,.2f}"),
    ],
)

path = generate_report(data_source=data, spec=spec, destination="relatorio.csv")
print(f"Relatório gerado em: {path}")
```

??? example "Saída: relatorio.csv"

    ```csv
    ID,Nome,Valor
    1,Ana Silva,"R$ 1,500.00"
    2,Bruno Costa,"R$ 3,200.50"
    3,Carla Lima,"R$ 890.75"
    ```

## Gerando um XLSX

Basta trocar `output_format`:

```python
spec = ReportSpec(
    output_format="xlsx",
    columns=[
        ColumnSpec(label="ID", source="id", type="int"),
        ColumnSpec(label="Nome", source="nome"),
        ColumnSpec(label="Valor", source="valor", type="float"),
    ],
    metadata={
        "xlsx": {
            "width_mode": "auto",
            "sheet_name": "Vendas",
        }
    },
)

generate_report(data_source=data, spec=spec, destination="relatorio.xlsx")
```

## Gerando um PDF

```python
spec = ReportSpec(
    output_format="pdf",
    columns=[
        ColumnSpec(label="ID", source="id", type="int"),
        ColumnSpec(label="Nome", source="nome"),
        ColumnSpec(label="Valor", source="valor", type="float",
                   formatter=lambda v: f"R$ {v:.2f}"),
    ],
)

generate_report(data_source=data, spec=spec, destination="relatorio.pdf")
```

!!! info "PDF"
    O PDF é gerado em orientação paisagem (A4) com tabela estilizada,
    cabeçalho em azul e linhas alternadas.

## Dados Aninhados

O `ColumnSpec` suporta **dot notation** para extrair campos aninhados:

```python
data = [
    {"pedido": {"id": 1}, "cliente": {"nome": "Ana", "endereco": {"cidade": "SP"}}},
]

spec = ReportSpec(
    output_format="csv",
    columns=[
        ColumnSpec(label="Pedido", source="pedido.id"),
        ColumnSpec(label="Cliente", source="cliente.nome"),
        ColumnSpec(label="Cidade", source="cliente.endereco.cidade"),
    ],
)
```

## Campos Opcionais e Defaults

```python
ColumnSpec(label="Status", source="status", default="Pendente")
ColumnSpec(label="Email", source="contato.email", required=True)  # erro se faltar
```

!!! tip "Próximo passo"
    Veja [Tipos Declarativos](types.md) para coerção automática e [Formatos de Saída](formats.md) para opções avançadas.
