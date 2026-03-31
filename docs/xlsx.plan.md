XlsxRenderer - Plano de Implementação Detalhado (Spec agnóstico)
================================================================

Objetivo
--------
Implementar `XlsxRenderer` com geração real de `.xlsx` usando biblioteca Rust-backed (`rust_xlsxwriter`), sem poluir `ColumnSpec` com campos específicos de XLSX.

Diretriz arquitetural
---------------------
`ColumnSpec` permanece agnóstico de formato (`label`, `source`, `required`, `default`, `formatter`).

Configurações de XLSX ficam em opções do renderer, dentro de `ReportSpec.metadata` (v1), com caminho de evolução para DTO tipado (`XlsxRenderOptions`) em v2.


1) Pré-requisitos e setup
-------------------------
1. Adicionar dependência:

```bash
uv add rust_xlsxwriter
```

2. Rodar baseline:

```bash
uv run pytest -q
```


2) Contrato recomendado para opções de XLSX
-------------------------------------------
Não alterar `ColumnSpec`.

Usar `ReportSpec.metadata["xlsx"]` com estrutura:

```python
{
  "width_mode": "manual" | "auto" | "mixed",   # default: mixed
  "default_width": 12.0,                        # default: 12.0
  "auto_padding": 1.5,                          # default: 1.5
  "columns": {
    "ID": {"width": 10.0, "min_width": 8.0, "max_width": 20.0},
    "Cliente": {"min_width": 12.0}
  }
}
```

Observação:
- chave de `columns` usa `label` da coluna (pós-mapeamento), evitando acoplamento com path de origem.


3) Tipagem interna (recomendado)
--------------------------------
Arquivo sugerido: `src/py_reports/xlsx_options.py`

```python
from dataclasses import dataclass, field
from typing import Literal

WidthMode = Literal["manual", "auto", "mixed"]

@dataclass(slots=True, frozen=True)
class XlsxColumnOptions:
    width: float | None = None
    min_width: float | None = None
    max_width: float | None = None

@dataclass(slots=True, frozen=True)
class XlsxRenderOptions:
    width_mode: WidthMode = "mixed"
    default_width: float = 12.0
    auto_padding: float = 1.5
    columns: dict[str, XlsxColumnOptions] = field(default_factory=dict)
```

Parser de metadata:
- criar função `parse_xlsx_options(metadata: dict[str, object]) -> XlsxRenderOptions`
- aplicar defaults e validações básicas (`width > 0`, `min<=max`).


4) Regras de largura
--------------------
Prioridade por coluna:
1. `column_options.width`
2. auto-detect (modo `auto` ou `mixed`)
3. `default_width`

Depois aplicar clamp:
- `max(width, min_width)` quando existir
- `min(width, max_width)` quando existir

Auto-detect:
- calcular `max_len = max(len(header), len(str(valor))...)`
- `width = max_len + auto_padding`


5) Implementação do XlsxRenderer
--------------------------------
Arquivo: `src/py_reports/renderers.py`

Passo a passo:
1. Materializar `rows` em lista.
2. Criar `Workbook`/`Worksheet`.
3. Escrever headers (`spec.columns[i].label`).
4. Escrever linhas.
5. Ler `xlsx` options via parser.
6. Resolver largura por coluna com helper puro.
7. Aplicar `worksheet.set_column_width`.
8. `workbook.save(path)` e retornar `Path`.

Snippet base:

```python
from rust_xlsxwriter import Workbook

def _resolve_width_for_label(
    *,
    label: str,
    values: list[object],
    options: XlsxRenderOptions,
) -> float:
    col_opts = options.columns.get(label)
    explicit = col_opts.width if col_opts else None
    min_w = col_opts.min_width if col_opts else None
    max_w = col_opts.max_width if col_opts else None

    if explicit is not None:
        width = explicit
    elif options.width_mode in {"auto", "mixed"}:
        max_len = max([len(label), *(len("" if v is None else str(v)) for v in values)])
        width = float(max_len) + options.auto_padding
    else:
        width = options.default_width

    if min_w is not None:
        width = max(width, min_w)
    if max_w is not None:
        width = min(width, max_w)
    return width
```


6) Testes (TDD)
---------------
Arquivos:
- existente: `tests/test_remaining_features_contract.py`
- novo: `tests/test_xlsx_renderer.py`

Casos mínimos:
1. assinatura de arquivo XLSX (`PK`) -> já existe.
2. modo manual: largura explícita por label.
3. modo auto: conteúdo maior aumenta largura.
4. modo mixed: explícito vence auto.
5. clamp: `min_width`/`max_width`.
6. fallback: sem config usa `default_width`.

Para validar largura, usar `openpyxl` em testes:

```bash
uv add --dev openpyxl
```

Exemplo:

```python
from openpyxl import load_workbook
wb = load_workbook(output)
ws = wb.active
assert ws.column_dimensions["A"].width == 30
```


7) Sequência de execução recomendada
------------------------------------
1. `uv add rust_xlsxwriter`
2. criar `xlsx_options.py` (tipos + parser)
3. implementar helper de largura
4. implementar `XlsxRenderer.render`
5. escrever testes de largura
6. `uv run pytest -q`
7. corrigir regressões
8. commit


8) Critérios de aceite
----------------------
- `ColumnSpec` permanece agnóstico de formato.
- `.xlsx` válido gerado (`PK`).
- largura manual/auto/mixed funcionando.
- clamps respeitados.
- sem regressão no fluxo CSV e testes existentes.
