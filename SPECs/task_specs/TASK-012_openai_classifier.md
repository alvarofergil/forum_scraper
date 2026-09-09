# TASK-012 - Adaptador OpenAI Configurable

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar clasificador OpenAI con modelo configurable y structured outputs.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila `TASK-012` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien:

- `SPECs/task_specs/TASK-011_classifier_interface.md`.
- Fragmentos de `SPECs/forum_scraper.md` sobre clasificacion, coste, privacidad y retencion de datos si cambia el payload enviado al modelo.

## Alcance Incluido

- Adaptador `OpenAIClassifier`.
- Construccion de input estructurado.
- No enviar HTML completo.
- Manejo de `ai.enabled` y `ai.model`.

## Alcance Excluido

- Elegir modelo concreto por defecto.
- Tests con llamadas reales.

## Guardrails Especificos

- No fijar un modelo por defecto en codigo; `ai.model` debe venir de configuracion y fallar claramente si falta cuando `ai.enabled=true`.
- No realizar llamadas reales a OpenAI en tests; usar cliente fake o mock.
- No enviar HTML completo, cookies, cabeceras, secrets ni datos no necesarios al modelo.
- No convertir candidatos en favoritos ni escribir en SQLite; esta tarea solo clasifica y devuelve resultados estructurados.
- No ocultar errores de configuracion, coste o salida invalida; deben ser explicitos y testeables.

## Dependencias

- TASK-011.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/classification/openai_classifier.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Si falta modelo con IA activa, error de configuracion claro.
- Usar schema/Pydantic para salida.
- Considerar prioridad temporal y mensajes del autor original.

## Requisitos De Tests

- Tests con cliente OpenAI fake.
- No se envia HTML.
- Error claro si IA activa sin modelo.
- Output invalido se rechaza.

## Criterios De Aceptacion

- Sin dependencia de red en tests.
- Adapter sustituible por fake.

## Verificacion Esperada

```bash
pytest
```

## Commit Sugerido

```text
feat: add openai structured classifier
```

## Rama Y PR

- Rama sugerida: `TASK-012_openai_classifier`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
