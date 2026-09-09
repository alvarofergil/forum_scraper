# TASK-005 - Cliente HTTP Respetuoso

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Crear `ArmasEsClient` con timeouts, retry, User-Agent y rate limit secuencial.

## Alcance Incluido

- GET de listings y topics.
- Delay entre requests.
- Max retries configurable.
- Clasificacion de errores HTTP/transitorios.
- User-Agent configurable e identificable.

## Alcance Excluido

- Parsing HTML.
- Requests concurrentes.
- Evasion antibot.

## Guardrails Especificos

- No parsear HTML, extraer topics, guardar fixtures reales ni decidir candidatos.
- No implementar concurrencia, proxy rotation, CAPTCHA bypass, fingerprint evasion, login, cookies persistentes ni account automation.
- No hacer peticiones reales en tests unitarios; usar fakes/mocks.
- No persistir respuestas HTTP, HTML completo, cookies ni cabeceras sensibles.
- Si el sitio devuelve bloqueo explicito o condiciones dudosas, devolver error claro y dejar la decision a TASK-006/PM.

## Dependencias

- TASK-002.
- TASK-004.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/sources/armas_es/client.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- No realizar concurrencia contra armas.es en v1.
- Si hay bloqueo explicito, devolver error claro.
- No registrar secrets ni cookies sensibles.

## Requisitos De Tests

- Tests con HTTP fake/mock.
- Retry ante fallo transitorio.
- No retry ilimitado.
- Delay invocado entre requests consecutivos.

## Criterios De Aceptacion

- Cliente separado de parsers.
- Sin peticiones reales en tests unitarios.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Resultado: ambos comandos pasan.

## Commit Sugerido

```text
feat: add armas.es http client
```

## Rama Y PR

- Rama sugerida: `TASK-005_armas_http_client`
- PR: https://github.com/alvarofergil/forum_scraper/pull/6
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
