# TASK-015 - Email SMTP Y Retry De Notificaciones

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Enviar emails de texto plano para eventos configurados y permitir reintentos.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`, esta sub-SPEC y la fila de `TASK-015` en `SPECs/forum_scraper_tasks.md`.
- Leer sub-SPECs de dependencias solo si hace falta aclarar el contrato de eventos.
- Leer fragmentos de `SPECs/forum_scraper.md` solo para reglas globales de secrets, coste, acceso externo, GitHub Flow o TDD que no esten claras aqui.
- Usar la checklist unica `SPECs/skills/forum-task-agent/SKILL.md`; no simular handoffs entre roles.

## Alcance Incluido

- SMTP Gmail configurable por entorno.
- Texto plano.
- Filtro `notifications.notify_event_types`.
- Marcar enviado/fallido/pendiente.
- `retry-notifications`.

## Alcance Excluido

- HTML email.
- OAuth Gmail.
- Almacenar credenciales.

## Guardrails Especificos

- No almacenar credenciales SMTP en SQLite, YAML, tests, logs ni fixtures; solo leerlas del entorno.
- No enviar HTML email, adjuntos ni formatos enriquecidos en v1.
- No implementar OAuth, gestion de cuentas Gmail ni refresco de tokens.
- No crear nuevos tipos de evento ni cambiar deduplicacion; consumir eventos existentes.
- No hacer llamadas SMTP reales en tests; usar servidor fake/mock.
- No perder eventos ante fallo de envio; deben quedar pendientes o fallidos reintentables.

## Dependencias

- TASK-014.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/notifications/email.py`
- `src/app/cli.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Secrets solo en env.
- Fallo SMTP deja evento pendiente o fallido reintentable.
- Eventos no configurados no se envian.

## Requisitos De Tests

- SMTP fake envia evento configurado.
- Evento no configurado no envia email.
- Fallo SMTP no pierde evento.
- Retry procesa pendientes.

## Criterios De Aceptacion

- Sin llamadas SMTP reales en tests.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- `pytest tests/test_email_notifications.py tests/test_cli.py` - 7 passed.
- `pytest` - 153 passed.
- `git diff --check` - sin salida.
- `ruff check .` / `python -m ruff check .` - no disponible en el entorno local (`ruff` no instalado).

## Commit Sugerido

```text
feat: add configurable email notifications
```

## Rama Y PR

- Rama sugerida: `TASK-015_email_notifications`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
