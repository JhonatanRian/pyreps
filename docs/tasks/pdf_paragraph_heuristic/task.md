# Task: Parametrização da Heurística de Paragraph no PDF

## Contexto
O `PdfRenderer` utiliza o objeto `Paragraph` do ReportLab para permitir quebra de linha automática em células. Por questões de performance, ele só usa `Paragraph` se o texto exceder 30 caracteres ou contiver `\n`.

## Problema
O limite de 30 caracteres é arbitrário e fixo (hardcoded). Dependendo da fonte e da largura da coluna, textos menores podem precisar de quebra de linha, ou textos maiores podem caber sem o overhead do `Paragraph`.

## Requisitos
- [ ] Adicionar `paragraph_threshold: int = 30` ao `PdfRenderOptions` em `pdf_options.py`.
- [ ] Atualizar o `PdfRenderer.render` para utilizar este valor da metadata.
- [ ] Documentar a opção no guia de formatos de saída.

## Impacto
- **Severidade**: MEDIUM
- **Arquivos afetados**: `src/py_reports/pdf_options.py`, `src/py_reports/renderers.py`, `docs/guide/formats.md`
