# Renderers

Renderers transform mapped data into output files.

## CsvRenderer

::: pyreps.renderers.CsvRenderer

## XlsxRenderer

::: pyreps.renderers.XlsxRenderer

## PdfRenderer

::: pyreps.renderers.PdfRenderer

## Renderer (Protocol)

::: pyreps.contracts.Renderer

## Registry

The `default_renderer_registry()` function returns the default renderers:

```python
{"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}
```

You can inject custom renderers via `renderer_registry` in `generate_report()`.
