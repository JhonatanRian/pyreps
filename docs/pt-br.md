# 🇧🇷 Visão Geral (Português)

Bem-vindo ao **{{ project_name }}**! Esta página foi criada para fornecer um resumo rápido e guia de início para desenvolvedores que falam Português.

O **{{ project_name }}** é uma biblioteca Python de alta performance projetada para gerar relatórios complexos (CSV, XLSX e PDF) com foco em baixo consumo de memória e velocidade extrema, utilizando componentes escritos em Rust.

## Principais Diferenciais

- **🚀 Performance de Rust**: Utiliza bibliotecas como `{{ rust_lib }}` e `orjson` para garantir que a geração de arquivos seja a mais rápida possível.
- **💧 Streaming 100%**: Projetado para processar milhões de linhas sem estourar a memória RAM, mantendo um pipeline de streaming contínuo.
- **🛠️ Tipagem Declarativa**: Use `ReportSpec` e `ColumnSpec` para definir como seus dados devem ser mapeados e formatados de forma limpa e segura.
- **🔌 Adaptadores Flexíveis**: Suporte nativo para listas de dicionários, JSON e bancos de dados SQL.

## Instalação

Você pode instalar o **{{ project_name }}** usando seu gerenciador de pacotes favorito:

```bash
# Usando uv (Recomendado)
uv add {{ project_name }}

# Usando pip
pip install {{ project_name }}
```

## Exemplo Rápido

Aqui está como gerar um relatório Excel simples a partir de uma lista de dados:

```python
from {{ project_name }} import ColumnSpec, ReportSpec, generate_report

# 1. Defina a especificação do relatório
spec = ReportSpec(
    columns=[
        ColumnSpec(key="name", label="Nome Completo"),
        ColumnSpec(key="email", label="E-mail"),
        ColumnSpec(key="balance", label="Saldo", type="decimal"),
    ],
    output_format="xlsx"
)

# 2. Seus dados (podem vir de um gerador ou banco de dados)
data = [
    {"name": "João Silva", "email": "joao@example.com", "balance": 1250.50},
    {"name": "Maria Souza", "email": "maria@example.com", "balance": 3400.00},
]

# 3. Gere o relatório de forma eficiente
generate_report(
    data_source=data,
    spec=spec,
    destination="meu_relatorio.xlsx"
)
```

## Próximos Passos

Embora a documentação completa esteja em **Inglês**, você pode explorar:

- [Guia de Início Rápido (Quickstart)](guide/quickstart.md)
- [Formatos de Saída](guide/formats.md)
- [Dicas de Performance](guide/performance.md)

---
*Nota: Para manter a consistência e o suporte global, a documentação técnica detalhada e o código-fonte utilizam o Inglês como idioma principal.*
