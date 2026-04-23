# Task: Validação de Conexão no SqlAdapter

## Contexto
O `SqlAdapter` recebe um objeto que satisfaz o protocolo `DBConnection`. Ele tenta criar um cursor e executar a query imediatamente ao iniciar o streaming.

## Problema
Se a conexão fornecida estiver fechada ou inválida, o erro pode ocorrer em um nível muito baixo do driver (ex: `sqlite3.ProgrammingError` ou `psycopg2.InterfaceError`), o que pode ser confuso para o usuário final da biblioteca.

## Requisitos
- [ ] Adicionar uma verificação proativa de estado (se o driver permitir) ou melhorar o wrapping de exceções durante `adapter.adapt()`.
- [ ] Garantir que erros de "Connection Closed" sejam capturados e relançados como `InputAdapterError` com uma mensagem amigável.
- [ ] Adicionar um teste unitário simulando uma conexão que falha especificamente na criação do cursor.

## Impacto
- **Severidade**: MEDIUM
- **Arquivos afetados**: `src/py_reports/adapters.py`
