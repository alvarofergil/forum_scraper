# TASK-010 - Bootstrap Service Y CLI

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar `python -m app bootstrap` y `debug-listing` respetando discovery barato.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`, esta sub-SPEC y la fila de `TASK-010` en `SPECs/forum_scraper_tasks.md`.
- Leer sub-SPECs de dependencias solo si hace falta aclarar contratos de parsers, matcher, clasificacion, eventos o favoritos.
- Leer fragmentos de `SPECs/forum_scraper.md` solo para reglas globales de discovery barato, armas.es, GitHub Flow o TDD que no esten claras aqui.
- Usar la checklist unica `SPECs/skills/forum-task-agent/SKILL.md`; no simular handoffs entre roles.

## Alcance Incluido

- Recorrer paginas configuradas.
- Ignorar anuncios.
- Persistir metadatos de topics.
- Abrir solo topics candidatos.
- Clasificar candidatos usando la interfaz configurada.
- Crear favoritos cuando la clasificacion confirme una oferta relevante.
- Persistir candidatos pendientes cuando la IA este desactivada o no se pueda clasificar.
- Registrar `bootstrap_completed_at`.
- Rechazar bootstrap repetido salvo `--force`.

## Alcance Excluido

- Implementar o modificar el adaptador OpenAI real.
- Email.
- Run incremental completo.

## Guardrails Especificos

- No abrir todos los topics del listing; solo los candidatos detectados por el matcher barato.
- No implementar scheduler, bucles infinitos, daemon ni ejecucion periodica.
- No enviar emails ni procesar retries de notificaciones.
- No modificar el adaptador OpenAI real; usar la interfaz ya disponible y fakes en tests.
- No borrar favoritos, historicos, eventos ni candidatos pendientes durante `--force`.
- No avanzar `bootstrap_completed_at` si la pasada falla de forma que pueda dejar estado inconsistente.

## Dependencias

- TASK-003.
- TASK-005.
- TASK-007.
- TASK-008.
- TASK-009.
- TASK-011.
- TASK-012.
- TASK-013.
- TASK-014.
- TASK-020.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/app/cli.py`
- `src/app/__main__.py`
- `src/discovery/service.py`
- `src/storage/repositories.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- `bootstrap.pages` controla numero de paginas.
- `--force` no borra favoritos ni historicos.
- Si IA esta desactivada, candidatos quedan pendientes y no favoritos automaticos.
- Si IA esta activa, solo se crean favoritos cuando el resultado sea `OFFER`, `matches_watch_item=true` y supere el umbral configurado.

## Requisitos De Tests

- Bootstrap recorre 10 paginas configuradas.
- Abre solo candidatos.
- Clasificacion positiva crea favorito.
- Clasificacion negativa no crea favorito.
- IA desactivada guarda candidato pendiente.
- Bootstrap idempotente rechaza segunda ejecucion.
- `--force` permite nueva pasada sin borrar historicos.

## Criterios De Aceptacion

- CLI usable con fakes.
- Tests sin red.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- `pytest tests/test_cli.py tests/test_discovery_bootstrap.py` - OK, 8 tests.
- `pytest` - OK, 135 tests.
- `ruff check .` - no ejecutado: `ruff` no esta instalado en el entorno local.
- `python -m ruff check .` - no ejecutado: modulo `ruff` no disponible.

## Commit Sugerido

```text
feat: add idempotent bootstrap
```

## Rama Y PR

- Rama sugerida: `TASK-010_bootstrap_cli`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
