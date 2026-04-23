# Task: Robustez do Streaming Patch no XLSX (Tag Boundary)

## Contexto
O `XlsxRenderer` utiliza uma técnica de patching de arquivos ZIP para inserir configurações de largura de coluna sem carregar o XML inteiro em memória. Atualmente, ele busca a tag `<sheetData>` em chunks de 64KB.

## Problema
Se a string `<sheetData` for dividida exatamente entre dois chunks (ex: `<she` no fim de um chunk e `etData` no início do próximo), o regex atual não encontrará a tag, causando a falha do patch ou inserção no local errado.

## Requisitos
- [ ] Implementar uma janela deslizante ou overlap de busca em `_stream_patch_sheet_xml`.
- [ ] Garantir que pelo menos 20 bytes do final do chunk anterior sejam mantidos no início da próxima busca.
- [ ] Adicionar um teste de stress que simula a quebra da tag exatamente no limite do chunk.

## Impacto
- **Severidade**: HIGH
- **Arquivos afetados**: `src/py_reports/renderers.py`
