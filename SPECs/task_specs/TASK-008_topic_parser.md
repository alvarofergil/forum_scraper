# TASK-008 - Parser De Topic viewtopic

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Parsear paginas de topic y extraer posts visibles, autor original y paginacion interna.

## Alcance Incluido

- `topic_parser.py`.
- Extraccion de posts.
- Deteccion de `current_page` y `total_pages`.
- Autor original desde primer post.
- Limpieza de texto para clasificacion/hashing.

## Alcance Excluido

- Descargar todas las paginas.
- Clasificacion IA.
- Persistencia.

## Guardrails Especificos

- No realizar requests HTTP ni paginar por cuenta propia; el parser solo analiza la pagina HTML entregada.
- No llamar a IA, construir prompts ni decidir si un topic es favorito.
- No escribir en SQLite ni guardar hashes/historicos.
- No conservar HTML completo ni preparar datos que incluyan navegacion, publicidad, firmas o contenido no relevante si puede limpiarse.
- No asumir que todos los posts del topic estan en una sola pagina; debe exponer la paginacion para servicios posteriores.

## Dependencias

- TASK-004.
- TASK-006.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/sources/armas_es/topic_parser.py`
- `src/sources/armas_es/dates.py`
- `tests/`
- `docs/armas_es_parser.md`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Extraer `post_id` estable si existe.
- Extraer autor y fecha por post.
- Preservar texto raw limpio, sin navegacion/publicidad/firmas cuando sea posible.
- No enviar ni preparar HTML completo para IA.

## Requisitos De Tests

- Topic de una pagina.
- Topic con multiples posts.
- Topic multipagina.
- Autor original correcto.
- Fecha individual por post.

## Criterios De Aceptacion

- Parser puro sin requests.
- Tests pasan sin red.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- PR: https://github.com/alvarofergil/forum_scraper/pull/10
- `.venv/bin/python -m pytest`: 62 passed.
- `.venv/bin/python -m ruff check .`: passed.

## Commit Sugerido

```text
feat: parse armas.es topics
```

## Rama Y PR

- Rama sugerida: `TASK-008_topic_parser`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
