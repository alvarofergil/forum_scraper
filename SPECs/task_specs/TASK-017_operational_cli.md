# TASK-017 - CLI Operativa

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Completar comandos operativos para uso diario, inspeccion y backups.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`, esta sub-SPEC y la fila de `TASK-017` en `SPECs/forum_scraper_tasks.md`.
- Leer sub-SPECs de dependencias solo si hace falta aclarar contratos de almacenamiento, favoritos, notificaciones o run incremental.
- Leer fragmentos de `SPECs/forum_scraper.md` solo para reglas globales de CLI, secrets, retencion de datos, GitHub Flow o TDD que no esten claras aqui.
- Usar la checklist unica `SPECs/skills/forum-task-agent/SKILL.md`; no simular handoffs entre roles.

## Alcance Incluido

- `status`.
- `favorites`.
- `inspect <TOPIC_ID>`.
- `favorite deactivate`.
- `favorite reactivate`.
- `backup`.
- Refinar `retry-notifications` si quedo parcial.

## Alcance Excluido

- UI web.
- Scheduler.

## Guardrails Especificos

- No crear interfaz web, API HTTP, dashboard ni frontend.
- No instalar ni configurar scheduler externo; solo comandos manuales/operativos.
- No exponer secrets, variables sensibles, HTML completo ni texto completo de posts en `status` o `inspect`.
- No modificar reglas de discovery, favoritos, eventos o email salvo cableado necesario para comandos existentes.
- No implementar backups copiando el archivo SQLite en caliente si la API de backup esta disponible.
- No borrar datos operativos; desactivar/reactivar favoritos debe ser reversible y auditable.

## Dependencias

- TASK-003.
- TASK-013.
- TASK-015.
- TASK-016.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/app/cli.py`
- `src/storage/`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- `status` muestra resumen legible.
- `backup` usa API de backup de SQLite.
- Reactivar/desactivar crea evento cuando corresponda.
- `inspect` no expone secrets.

## Requisitos De Tests

- Status con DB fake/temporal.
- Backup crea DB consistente.
- Reactivar favorito cambia estado.
- Desactivar favorito cambia estado.

## Criterios De Aceptacion

- CLI documentada en README o ayuda integrada.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- `pytest tests/test_operational_cli.py` - 6 passed.
- `pytest tests/test_cli.py tests/test_operational_cli.py` - 9 passed.
- `pytest` - 159 passed.
- `git diff --check` - sin salida.
- `ruff check .` / `python -m ruff check .` - no disponible en el entorno local (`ruff` no instalado).

## Commit Sugerido

```text
feat: add operational cli commands
```

## Rama Y PR

- Rama sugerida: `TASK-017_operational_cli`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
