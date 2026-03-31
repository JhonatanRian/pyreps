Problema
- Projetar uma arquitetura de biblioteca Python para gerar relatórios CSV, XLSX e PDF com entrada versátil (list[dict], JSON e fontes SQL), usando padrões de projeto, interfaces e DTOs.

Abordagem
- Criar um núcleo orientado a contratos:
  - DTOs e tipos de schema para mapear dados de entrada em colunas de relatório.
  - Interfaces (Protocols/ABCs) para adaptadores de entrada, processadores e renderizadores.
  - Implementações iniciais de adaptadores (list[dict], JSON em memória) e renderizadores (CSV/XLSX stub-ready).
  - Serviço orquestrador com fluxo: adaptar -> validar/mapear -> renderizar.
- Manter API simples para o usuário e extensível para novos adapters/renderers.

Todos
- map-domain-contracts: Definir DTOs e contratos centrais (colunas, spec, registros normalizados).
- implement-input-adapters: Implementar adapters para list[dict] e JSON em memória.
- implement-renderer-contracts: Definir contratos e factory/registry de renderização por formato.
- implement-csv-renderer: Implementar renderizador CSV funcional.
- scaffold-xlsx-pdf-renderers: Criar scaffolding de XLSX/PDF para extensão futura.
- implement-orchestrator-api: Criar serviço principal e API pública de uso.
- add-usage-docs: Documentar arquitetura e exemplo de uso no README.
- run-validation: Executar testes/checagem disponíveis para validar baseline.

Notas
- Priorizar padrões Strategy + Adapter + Factory.
- Usar typing forte (Protocol, dataclass, TypedDict quando fizer sentido).
- Evitar acoplamento dos renderers com o formato original dos dados de entrada.

---

Fase 2 - Testes de contrato da API

Objetivo
- Criar uma suíte de testes que descreva o uso correto da API pública, servindo como base de desenvolvimento guiado por testes.

Escopo dos testes
- Fluxo feliz para geração CSV com `list[dict]`.
- Fluxo feliz para geração CSV com payload JSON.
- Mapeamento: nested path, `required`, `default`, `formatter`.
- Erros de uso incorreto (adapter não resolvido, campo obrigatório ausente, JSON inválido).
- Contratos de renderização registrados (`csv`, `xlsx`, `pdf`) e stubs de formatos não implementados.

Entregáveis
- Estrutura `tests/` com casos de unidade/comportamento.
- Dependência de teste configurada no projeto (`pytest`).
- Comando de execução documentado implicitamente pelo padrão `uv run pytest`.

---

Fase 3 - Implementação do XlsxRenderer (Rust-backed)

Objetivo
- Implementar `XlsxRenderer` com geração real de arquivo e controle de largura de coluna, suportando configuração manual e auto-detect.

Decisão de design (recomendada)
- Suportar os dois modos:
  - Manual: largura definida por coluna (`width` no `ColumnSpec`).
  - Auto-detect: calcula largura com base no maior conteúdo (header + células).
- Regra de precedência: `width` explícito da coluna > auto-detect > largura padrão.

Contrato proposto (v1)
- Em `ColumnSpec`:
  - `width: float | None = None`
  - `min_width: float | None = None`
  - `max_width: float | None = None`
- Em `ReportSpec.metadata` (ou campo dedicado futuro):
  - `xlsx_width_mode`: `"manual" | "auto" | "mixed"` (default `"mixed"`)
  - `xlsx_default_width`: `float` (ex.: 12)
  - `xlsx_auto_padding`: `float` (ex.: 1.5)

Algoritmo de auto-detect
1. Para cada coluna, coletar header + valores formatados como string.
2. Calcular `max_len` por coluna.
3. Converter para largura: `max_len + padding`.
4. Aplicar clamp em `min_width`/`max_width` quando definidos.
5. Aplicar no worksheet via API da lib.

Etapas de implementação
1. Confirmar dependência Rust-backed escolhida (assumido: `rust_xlsxwriter`) e adicionar no projeto.
2. Evoluir contratos (`ColumnSpec`) preservando compatibilidade.
3. Implementar helper de cálculo de largura reutilizável/testável.
4. Implementar `XlsxRenderer.render` (header, linhas, tipos básicos, largura).
5. Criar testes específicos do renderer:
   - arquivo `.xlsx` válido.
   - modo manual respeitando `width`.
   - modo auto/mixed aplicando cálculo.
   - fallback para largura padrão.
6. Rodar suíte completa e ajustar regressões.

Critérios de aceite
- Teste de contrato `test_generate_xlsx_file_signature` passa.
- Novos testes de largura passam.
- Não quebra fluxo atual de CSV nem mapeamento.
