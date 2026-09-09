# TASK-XXX - Titulo

Estado: `TODO`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Describir el resultado verificable de la tarea.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila de esta tarea en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer solo si aplica:

- Fragmentos concretos de `SPECs/forum_scraper.md` cuando haya impacto global, duda de alcance, arquitectura, privacidad, coste, legalidad, seguridad o acceso externo.
- Sub-SPECs de dependencias directas cuando su contrato no este claro por esta sub-SPEC.
- Docs locales bajo `docs/` cuando esten enlazadas aqui o sean necesarias para los archivos tocados.
- Flujo de release solo cuando el usuario pida commit, push o PR.

Usar un unico agente por defecto; los roles son checklist interna, no subagentes ni handoffs escritos.

## Alcance Incluido

- Punto incluido.

## Alcance Excluido

- Punto excluido especifico.
- Comportamiento tentador que pertenece a otra tarea o version.

## Guardrails Especificos

- No tocar archivos fuera de `Archivos Permitidos O Esperados` sin actualizar esta sub-SPEC y el documento maestro.
- No introducir llamadas de red, servicios externos, credenciales, cambios de persistencia, cambios de arquitectura o nuevos comandos CLI salvo que esta tarea lo permita expresamente.
- No ampliar el alcance funcional por conveniencia; si aparece una necesidad nueva, dejarla documentada y preguntar al usuario cuando afecte alcance, privacidad, coste, legalidad, seguridad o arquitectura.
- No marcar la tarea como `DONE` ni hacer commit si los tests requeridos no pasan.

## Dependencias

- `TASK-000`

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/...`, `tests/...`, `docs/...` o el archivo concreto que aplique
- `SPECs/forum_scraper_tasks.md`
- esta sub-SPEC si se descubre una decision relevante.

## Requisitos Funcionales

- Requisito.

## Requisitos De Tests

- Test primero.
- Todos los tests unitarios deben pasar antes del commit.

## Criterios De Aceptacion

- Criterio verificable.

## Verificacion Esperada

```bash
pytest
```

## Commit Sugerido

```text
feat: describe change
```

## Rama Y PR

- Rama: `TASK-XXX_slug_descriptivo`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
