# TASK-013 - Favoritos, Hashing E Historicos

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar favoritos activos/inactivos, hash de contenido estable e historicos de precio/estado.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila `TASK-013` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien:

- `SPECs/task_specs/TASK-011_classifier_interface.md`.
- `SPECs/task_specs/TASK-014_events_idempotency.md`.
- Fragmentos de `SPECs/forum_scraper.md` sobre favoritos, favorites-check, hashing, clasificacion, eventos y retencion de datos.

## Alcance Incluido

- Crear favoritos desde clasificacion positiva.
- Monitorizar favoritos por URL canonica.
- Calcular `content_hash`.
- Evitar IA si hash no cambia.
- `price_history` y `status_history`.
- Desactivar `SOLD`/`WITHDRAWN`.

## Alcance Excluido

- SMTP.
- Discovery incremental completo.

## Guardrails Especificos

- No enviar emails ni implementar retry SMTP; solo crear eventos consumibles por notificaciones.
- No ejecutar discovery incremental ni decidir paginacion de listings.
- No guardar texto completo de posts ni HTML completo; persistir hashes y metadatos.
- No borrar fisicamente favoritos, historicos, topics ni posts; las bajas deben ser logicas.
- No llamar a IA cuando el hash de contenido no haya cambiado.
- No marcar un topic como inactivo por un unico fallo transitorio; respetar `favorites.unavailable_confirmation_runs`.

## Dependencias

- TASK-003.
- TASK-005.
- TASK-008.
- TASK-011.
- TASK-014.
- TASK-020.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/favorites/service.py`
- `src/storage/repositories.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- No guardar texto completo de posts, solo hashes/metadatos.
- Precio `None` no borra precio anterior.
- No borrar favoritos fisicamente.
- Confirmar inaccesibilidad segun config antes de inactivar por desaparicion.
- Usar el servicio de eventos para `NEW_FAVORITE`, cambios de precio/estado e indisponibilidad confirmada.

## Requisitos De Tests

- Favorite unchanged no llama a clasificador.
- Favorite changed llama a clasificador.
- Nuevo favorito crea evento idempotente.
- Cambio de precio crea historico.
- Cambio de estado crea historico.
- `SOLD`/`WITHDRAWN` inactiva favorito.

## Criterios De Aceptacion

- Servicio funciona con cliente/parser/clasificador fake.

## Verificacion Esperada

```bash
pytest
```

## Commit Sugerido

```text
feat: add favorites monitoring
```

## Rama Y PR

- Rama sugerida: `TASK-013_favorites_hashing_history`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
