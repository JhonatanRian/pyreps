# Task: Imutabilidade do ReportSpec (Tuple vs List)

## Contexto
A `ReportSpec` é uma `frozen dataclass`, o que impede a reatribuição de campos. No entanto, o campo `columns` é definido como uma `list`, que é um objeto mutável.

## Problema
Embora não se possa trocar a lista por outra, é possível alterar o conteúdo da lista existente (ex: `spec.columns.append(...)`), o que quebra a garantia de imutabilidade da configuração durante o pipeline de geração.

## Requisitos
- [ ] Alterar o tipo de `columns` de `list[ColumnSpec]` para `tuple[ColumnSpec, ...]`.
- [ ] Atualizar o `__post_init__` caso necessário para garantir a conversão automática se uma lista for passada no construtor.
- [ ] Ajustar referências no `mapping.py` que iteram sobre as colunas.

## Impacto
- **Severidade**: MEDIUM
- **Arquivos afetados**: `src/py_reports/contracts.py`, `src/py_reports/mapping.py`
