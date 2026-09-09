# TASK-004 - URLs Canonicas De armas.es

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar utilidades puras para construir y normalizar URLs de armas.es.

## Alcance Incluido

- Extraer `external_topic_id` desde parametro `t`.
- Construir URL canonica.
- Eliminar `sid`, `start`, `p` y anchors de identidad.
- Resolver URLs relativas contra `base_url`.

## Alcance Excluido

- Networking.
- Parsing HTML.

## Guardrails Especificos

- No realizar requests HTTP, leer fixtures HTML ni depender de BeautifulSoup/lxml.
- No tocar persistencia, config global, cliente HTTP, discovery ni parsers.
- No usar titulo, posicion, `sid`, `start`, `p`, anchors ni hash HTML como identidad de topic.
- No aceptar silenciosamente URLs sin `t` cuando la operacion requiera identidad; debe fallar de forma explicita.
- No introducir reglas de otros sitios; todo lo especifico queda limitado a `sources/armas_es/`.

## Dependencias

- TASK-002.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/sources/armas_es/urls.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Canonical topic URL: `https://www.armas.es/foros/viewtopic.php?f=96&t=<ID>`.
- No aceptar URLs sin `t` cuando se requiere identidad de topic.

## Requisitos De Tests

- URL con `sid` produce misma canonica.
- URL con `start`, `p` y anchor produce misma identidad.
- URL relativa se resuelve correctamente.
- URL sin `t` falla de forma explicita.

## Criterios De Aceptacion

- Funciones puras, sin IO.
- Cubierto por tests unitarios.

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
feat: add armas.es canonical urls
```

## Rama Y PR

- Rama sugerida: `TASK-004_armas_urls`
- PR: https://github.com/alvarofergil/forum_scraper/pull/5
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
