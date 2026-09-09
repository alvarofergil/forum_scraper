# TASK-019 - Hardening Final Y DoD v1

Estado: `DONE`
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Verificar la Definition of Done completa de v1 y cerrar riesgos de integracion.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`, esta sub-SPEC y la fila de `TASK-019` en `SPECs/forum_scraper_tasks.md`.
- Leer sub-SPECs de dependencias solo para validar evidencias, contratos incumplidos o dudas de cierre.
- Leer fragmentos de `SPECs/forum_scraper.md` por secciones de DoD, alcance v1, guardrails globales y criterios de aceptacion; leerla completa solo si la revision final lo requiere.
- Usar la checklist unica `SPECs/skills/forum-task-agent/SKILL.md`; no simular handoffs entre roles.

## Alcance Incluido

- Revisar DoD de la SPEC maestra.
- Completar tests de comportamiento faltantes.
- Revisar logs y secrets.
- Revisar documentacion final.
- Confirmar que el proyecto desplegable vive en la raiz del repo.

## Alcance Excluido

- Nuevas features fuera de v1.
- Frontend.
- Optimizaciones no necesarias.

## Guardrails Especificos

- No introducir features nuevas para compensar hallazgos de QA; crear tarea futura o preguntar si excede v1.
- No crear frontend, API web, scheduler interno, colas externas ni nuevas bases de datos.
- No relajar criterios de aceptacion, tests, guardrails o DoD para cerrar la version.
- No marcar tareas como `DONE` sin evidencia real de tests/documentacion/commit correspondiente y PR mergeado en `main`.
- No hacer requests reales amplios durante aceptacion; cualquier acceso externo debe estar justificado por la SPEC y documentado.
- No commitear secrets, HTML sin sanitizar, bases de datos reales ni artefactos locales.

## Dependencias

- TASK-001 a TASK-018.
- TASK-020.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- Todo el proyecto si el cambio esta justificado por cierre de DoD.
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- No perder eventos.
- No duplicar eventos.
- No requests innecesarios.
- No secrets en Git.
- No mecanismos de evasion.

## Requisitos De Tests

- Suite completa verde.
- Tests de comportamiento cubren bootstrap, incremental, favoritos, eventos y notificaciones.

## Criterios De Aceptacion

- Cada punto de DoD v1 queda validado o documentado con evidencia.
- Documento maestro marca todas las tareas como `DONE`.

## Verificacion Esperada

```bash
pytest
docker compose build
```

## Commit Sugerido

```text
test: complete v1 acceptance coverage
```

## Rama Y PR

- Rama sugerida: `TASK-019_final_acceptance`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
