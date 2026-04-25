# Renderers

Renderers transform mapped data into output files.

## CsvRenderer

::: {{ project_name }}.renderers.CsvRenderer

## XlsxRenderer

::: {{ project_name }}.renderers.XlsxRenderer

## PdfRenderer

::: {{ project_name }}.renderers.PdfRenderer

## Renderer (Protocol)

::: {{ project_name }}.contracts.Renderer

## Registry

The `default_renderer_registry()` function returns the default renderers:

```python
{"csv": CsvRenderer(), "xlsx": XlsxRenderer(), "pdf": PdfRenderer()}
```

You can inject custom renderers via `renderer_registry` in `generate_report()`.
