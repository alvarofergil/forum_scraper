# TASK-016 - Run Incremental Y Recuperacion Tras Apagado

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar `python -m app run` con discovery incremental, overlap y favorites check.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`, esta sub-SPEC y la fila de `TASK-016` en `SPECs/forum_scraper_tasks.md`.
- Leer sub-SPECs de dependencias solo si hace falta aclarar contratos de bootstrap, favoritos o eventos.
- Leer fragmentos de `SPECs/forum_scraper.md` solo para reglas globales de acceso respetuoso, checkpoints, GitHub Flow o TDD que no esten claras aqui.
- Usar la checklist unica `SPECs/skills/forum-task-agent/SKILL.md`; no simular handoffs entre roles.

## Alcance Incluido

- Fase discovery.
- Fase favorites check.
- `last_successful_discovery_at`.
- `last_successful_favorites_check_at`.
- Cutoff con overlap.
- Safety limit de paginas.

## Alcance Excluido

- Scheduler externo.
- Docker.

## Guardrails Especificos

- No implementar cron, systemd timer, daemon, bucle infinito ni scheduler interno.
- No cambiar Docker, compose ni documentacion de despliegue.
- No avanzar `last_successful_discovery_at` si se alcanza `max_pages_per_run` sin llegar al cutoff.
- No descargar topics no candidatos salvo que ya sean favoritos activos.
- No generar eventos duplicados en runs repetidos sin cambios.
- No hacer concurrencia contra armas.es; mantener acceso secuencial y respetuoso.

## Dependencias

- TASK-010.
- TASK-013.
- TASK-014.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/discovery/service.py`
- `src/favorites/service.py`
- `src/app/cli.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Navegar hasta `last_activity_at < cutoff`.
- Si se alcanza `max_pages_per_run` sin cutoff, registrar warning y no avanzar checkpoint como completo.
- Favorites check no depende de discovery.
- Dos runs sin cambios no generan eventos duplicados.

## Requisitos De Tests

- Recupera actividad tras hueco temporal.
- Usa overlap.
- Safety limit impide falso checkpoint.
- Topic no relevante activo no se descarga completo.
- Favorito antiguo se chequea aunque no aparezca en listing.

## Criterios De Aceptacion

- `run` ejecuta una pasada y termina.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- `pytest tests/test_cli.py tests/test_discovery_bootstrap.py` - OK, 14 tests.
- `pytest` - OK, 141 tests.
- `ruff check .` - no ejecutado: `ruff` no esta instalado en el entorno local.
- `python -m ruff check .` - no ejecutado: modulo `ruff` no disponible.

## Commit Sugerido

```text
feat: add incremental recovery
```

## Rama Y PR

- Rama sugerida: `TASK-016_incremental_recovery`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
