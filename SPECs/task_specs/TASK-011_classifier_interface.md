# TASK-011 - Interfaz De Clasificacion Y FakeClassifier

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Aislar la clasificacion tras una interfaz testeable y definir resultado estructurado.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila `TASK-011` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien, solo si se modifica el contrato o sus consumidores:

- `SPECs/task_specs/TASK-012_openai_classifier.md`.
- `SPECs/task_specs/TASK-013_favorites_hashing_history.md`.
- Fragmentos de `SPECs/forum_scraper.md` sobre clasificacion y retencion de datos.

## Alcance Incluido

- Protocol `ListingClassifier`.
- `ClassificationResult` Pydantic.
- Enums de listing y availability si no existen.
- `FakeClassifier` para tests.

## Alcance Excluido

- OpenAI real.
- Prompt final.
- Networking externo.

## Guardrails Especificos

- No importar ni inicializar el SDK de OpenAI ni ningun cliente externo.
- No definir prompts definitivos ni hacer llamadas de red.
- No persistir resultados ni crear favoritos/eventos desde esta tarea.
- No permitir resultados libres sin validacion estructurada.
- No acoplar servicios posteriores a una implementacion concreta; deben depender del protocolo/interfaz.

## Dependencias

- TASK-002.
- TASK-008.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/classification/base.py`
- `src/classification/fake.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Metodos `classify_new_candidate` y `classify_favorite_update`.
- Resultado estructurado, no JSON libre.
- Capaz de representar `matches_watch_item=false`.

## Requisitos De Tests

- Fake devuelve respuestas controladas.
- Validacion Pydantic rechaza availability invalida.
- Precio `None` no implica borrado.

## Criterios De Aceptacion

- Servicios posteriores pueden depender de la interfaz, no de OpenAI.

## Verificacion Esperada

```bash
pytest
```

## Commit Sugerido

```text
feat: add structured classifier interface
```

## Rama Y PR

- Rama sugerida: `TASK-011_classifier_interface`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
