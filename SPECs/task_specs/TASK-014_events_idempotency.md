# TASK-014 - Eventos E Idempotencia

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Crear servicio de eventos con deduplicacion robusta.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila `TASK-014` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien, si se cambian payloads o llamadores:

- `SPECs/task_specs/TASK-013_favorites_hashing_history.md`.
- Fragmentos de `SPECs/forum_scraper.md` sobre eventos, notificaciones, seguridad y retencion de datos.

## Alcance Incluido

- Crear eventos tipados.
- `deduplication_key` unica.
- Payload JSON estable.
- Estado de notificacion pendiente/enviada/fallida.

## Alcance Excluido

- Envio SMTP.
- Formato final de email.

## Guardrails Especificos

- No enviar emails, abrir conexiones SMTP ni implementar `retry-notifications`.
- No decidir reglas de favoritos, precios, disponibilidad o discovery; solo registrar eventos tipados e idempotentes.
- No permitir eventos sin `deduplication_key` estable ni payload JSON determinista.
- No guardar secrets, HTML completo, texto completo de posts ni datos sensibles en payloads.
- No duplicar eventos ante reintentos o ejecuciones repetidas con el mismo topic/evento/hash.

## Dependencias

- TASK-003.
- TASK-020.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/events/service.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Evitar duplicados por mismo topic/evento/hash.
- Crear eventos relevantes: `NEW_FAVORITE`, `PRICE_CHANGED`, `STATUS_CHANGED`, `BECAME_UNAVAILABLE`, `FAVORITE_REACTIVATED`, `ERROR`.
- No depender de reglas internas de favoritos; favoritos consumira este servicio en TASK-013.

## Requisitos De Tests

- Insertar mismo evento dos veces no duplica.
- Eventos distintos para mismo topic conviven.
- Payload serializa de forma determinista.

## Criterios De Aceptacion

- Servicio listo para notificaciones.

## Verificacion Esperada

```bash
pytest
```

## Commit Sugerido

```text
feat: add event deduplication
```

## Rama Y PR

- Rama sugerida: `TASK-014_events_idempotency`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
