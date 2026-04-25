# Renderers

Renderers transformam dados mapeados em arquivos de saída.

## CsvRenderer

::: pyreps.renderers.CsvRenderer

## XlsxRenderer

::: pyreps.renderers.XlsxRenderer

## PdfRenderer

::: pyreps.renderers.PdfRenderer

## Renderer (Protocol)

::: pyreps.contracts.Renderer

## Registry

A função `default_renderer_registry()` retorna os renderers padrão:

```python
{"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}
```

Você pode injetar renderers customizados via `renderer_registry` em `generate_report()`.
