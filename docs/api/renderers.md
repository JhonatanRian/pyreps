# Renderers

Renderers transformam dados mapeados em arquivos de saída.

## CsvRenderer

::: py_reports.renderers.CsvRenderer

## XlsxRenderer

::: py_reports.renderers.XlsxRenderer

## PdfRenderer

::: py_reports.renderers.PdfRenderer

## Renderer (Protocol)

::: py_reports.contracts.Renderer

## Registry

A função `default_renderer_registry()` retorna os renderers padrão:

```python
{"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}
```

Você pode injetar renderers customizados via `renderer_registry` em `generate_report()`.
