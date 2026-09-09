# TASK-007 - Parser De Listing viewforum

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Parsear el bloque `Temas` de armas.es y devolver topics ordinarios estructurados.

## Alcance Incluido

- `listing_parser.py`.
- `ParseError`.
- Extraccion de metadatos disponibles.
- Deteccion de siguiente pagina.
- Exclusion estructural de `Anuncios`.

## Alcance Excluido

- Networking.
- Persistencia.
- Matching.

## Guardrails Especificos

- No realizar requests HTTP ni depender del cliente real; el parser solo consume HTML recibido o fixtures.
- No escribir en SQLite, crear repositorios ni actualizar estado de aplicacion.
- No hacer matching de watchlist, clasificacion IA ni descarga de topics.
- No excluir `Anuncios` por texto visible del titulo; debe usarse estructura DOM.
- No normalizar identidad con campos inestables como `sid`, `start`, `p`, anchors, posicion o titulo.

## Dependencias

- TASK-004.
- TASK-006.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/sources/armas_es/listing_parser.py`
- `src/sources/armas_es/dates.py`
- `tests/`
- `docs/armas_es_parser.md`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Extraer `external_topic_id`, URL canonica, titulo, snippet, autor, fechas, replies y views.
- Distinguir `created_at` de `last_activity_at`.
- Usar estructura DOM antes que texto visible.
- Fallar con `ParseError` ante campos obligatorios imposibles.

## Requisitos De Tests

- Detecta exactamente `Temas`.
- Excluye `Anuncios`.
- Extrae `t`.
- Elimina `sid`.
- Detecta `Siguiente`.
- Fixtures cubren variacion con adjuntos/texto de autor.

## Criterios De Aceptacion

- Parser puro sin requests.
- Tests pasan sin red.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- PR: https://github.com/alvarofergil/forum_scraper/pull/9
- `.venv/bin/python -m pytest`: 56 passed.
- `.venv/bin/python -m ruff check .`: passed.

## Commit Sugerido

```text
feat: parse armas.es forum listings
```

## Rama Y PR

- Rama sugerida: `TASK-007_listing_parser`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
