# TASK-022 - Correctivo Tecnico Post HITO-03

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Subsanar las desviaciones y gaps detectados en el sanity check post HITO-03 antes de implementar HITO-04, endureciendo los contratos de favoritos, clasificacion, eventos y calidad automatizada.

El resultado verificable debe ser:

- `FavoriteService` no depende directamente de `sources.armas_es`.
- Los favoritos solo se crean cuando la clasificacion supera el umbral configurado.
- El check de favoritos puede incorporar topic multipagina sin concurrencia ni sobre-fetch.
- Los eventos emitidos por favoritos no filtran HTML, texto completo de posts, cookies, cabeceras ni secrets.
- `ruff check` y `pytest` pasan sobre los archivos del proyecto.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila de `TASK-022` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien:

- `SPECs/task_specs/TASK-011_classifier_interface.md`.
- `SPECs/task_specs/TASK-012_openai_classifier.md`.
- `SPECs/task_specs/TASK-014_events_idempotency.md`.
- `SPECs/task_specs/TASK-013_favorites_hashing_history.md`.
- Fragmentos de `SPECs/forum_scraper.md`:
  - `#4-fuente-monitorizada`
  - `#8-informacion-de-topic`
  - `#14-favorites`
  - `#15-favorites-check`
  - `#16-hashing-y-almacenamiento-de-posts`
  - `#17-clasificacion`
  - `#19-eventos`

Usar un unico agente por defecto; los roles son checklist interna, no subagentes ni handoffs escritos.

## Observaciones Del Sanity Check

### P1 - Creacion De Favoritos Sin Umbral Configurado

La SPEC maestra exige que un topic sea `OFFER`, relevante y supere umbrales configurados antes de convertirse en favorito. `AiConfig.match_confidence_threshold` existe, pero `FavoriteService.create_from_classification` solo comprueba `matches_watch_item` y `listing_type == OFFER`.

Riesgo: candidatos de baja confianza pueden entrar como favoritos y generar historicos/eventos falsos cuando HITO-04 conecte bootstrap/discovery.

### P1 - FavoriteService Acoplado A armas.es

`src/favorites/service.py` importa cliente, parser y excepciones de `sources.armas_es`, y construye la URL canonica con host y `f=96` hardcodeados.

Riesgo: se rompe la frontera definida por la SPEC maestra: el dominio de favoritos conoce detalles de URL, errores y parser de la fuente. HITO-04 heredaria ese acoplamiento.

### P1 - Check De Favoritos Sin Contrato Multipagina

Los topics pueden tener varias paginas y no se debe asumir que todo el contenido esta en una unica pagina. El check actual de favoritos consume una sola respuesta parseada. Si una rebaja, reserva, venta o retirada aparece en una respuesta posterior no incluida en la primera pagina, el hash puede no cambiar y la IA no se invocaria.

Riesgo: perdida de eventos `PRICE_CHANGED`, `STATUS_CHANGED` o `BECAME_UNAVAILABLE`.

### P2 - Errores Transitorios Y Payloads Seguros Poco Blindados Por Tests

La suite cubre confirmacion de no disponibilidad, pero no cubre explicitamente que un error transitorio no incremente confirmaciones ni desactive favoritos. Tampoco inspecciona de forma directa que los payloads emitidos por favoritos no incluyen HTML, texto completo de posts, cabeceras, cookies o secrets.

Riesgo: regresiones silenciosas en eventos y retencion de datos.

### P2 - Linting Rojo En HITO-03

`./.venv/bin/ruff check .` falla por imports desordenados, docstrings duplicados en `__init__.py` de eventos/favoritos y lineas demasiado largas en `src/favorites/service.py` y tests relacionados.

Riesgo: incumplimiento del estandar de calidad declarado en `pyproject.toml`.

### P3 - Sub-SPECs De HITO-03 Sin Seccion Explicita De Contexto Minimo

Las sub-SPECs `TASK-011`, `TASK-012`, `TASK-014` y `TASK-013` son implementables, pero no incluyen el apartado `Contexto Minimo Para Agentes` que el estandar actual exige para nuevas tareas.

Riesgo: menor eficiencia y consistencia para agentes futuros que auditen o modifiquen HITO-03.

## Alcance Incluido

- Introducir un contrato fuente-neutral para obtener topics completos usados por favoritos.
- Adaptar `FavoriteService.check_favorite` para depender de ese contrato, no de `ArmasEsClient`, `parse_topic_page` ni excepciones `Armas*`.
- Mantener el adapter especifico de armas.es bajo `src/sources/armas_es/`.
- Eliminar construccion hardcodeada de URLs de armas.es dentro de `src/favorites/`.
- Hacer que la creacion de favoritos respete un umbral de confianza configurable.
- Asegurar que el adapter de topic completo puede obtener paginas adicionales de un topic de forma secuencial cuando `ParsedTopic.total_pages > 1`.
- Fusionar posts multipagina en un unico `ParsedTopic` manteniendo orden estable, `external_post_id`, autor, fecha y texto limpio para hashing/clasificacion.
- Deduplicar posts por `external_post_id` cuando exista; si falta, usar orden de pagina y posicion como fallback estable.
- Cubrir errores transitorios frente a no disponibilidad confirmada.
- Cubrir payloads emitidos por favoritos para demostrar que no guardan texto completo, HTML ni datos sensibles.
- Corregir incidencias de Ruff en archivos tocados por HITO-03 y en `__init__.py` relacionados.
- Añadir `Contexto Minimo Para Agentes` a las sub-SPECs de HITO-03.

## Alcance Excluido

- No implementar `bootstrap`, `run`, scheduler ni CLI operativa.
- No implementar SMTP, retry de notificaciones ni formato final de email.
- No hacer llamadas reales a armas.es, OpenAI, SMTP ni GitHub desde tests.
- No introducir concurrencia ni paralelismo de requests.
- No cambiar la fuente monitorizada ni ampliar v1 a otros foros o webs.
- No persistir texto completo de posts ni HTML completo en SQLite.
- No modificar reglas de parsing de listing salvo que sea imprescindible para construir URLs de paginas de topic dentro del adapter armas.es.
- No elegir un modelo OpenAI por defecto.
- No borrar historicos, eventos, candidatos, topics ni favoritos existentes.
- No cambiar estados `DONE` de tareas ya mergeadas.

## Guardrails Especificos

- `src/favorites/` no puede importar desde `sources.armas_es`.
- Cualquier codigo que conozca `viewtopic.php`, `start`, `f=96`, `Armas*Error` o `parse_topic_page` debe vivir en `src/sources/armas_es/` o en tests especificos de esa fuente.
- El contrato fuente-neutral debe ser pequeno y testeable con fakes. No crear un framework de plugins de fuentes.
- El umbral debe venir de configuracion o de un parametro explicito del servicio. No hardcodear `0.85` fuera del default ya definido en config.
- Una clasificacion con `confidence < match_confidence_threshold` no puede crear favorito ni emitir `NEW_FAVORITE`.
- Una clasificacion con `confidence == match_confidence_threshold` si puede crear favorito si tambien cumple `matches_watch_item=true` y `listing_type=OFFER`.
- Los errores transitorios no deben incrementar `unavailable_confirmation_count`, no deben inactivar favoritos y no deben emitir `BECAME_UNAVAILABLE`.
- Las no disponibilidades confirmadas deben seguir respetando `favorites.unavailable_confirmation_runs`.
- La obtencion multipagina debe ser secuencial y acotada por `total_pages`; si una pagina adicional falla de forma transitoria, el check no debe aplicar una clasificacion parcial como si fuese estado completo.
- Si el parser informa `total_pages` invalido o menor que `current_page`, tratarlo como error recuperable y no crear evento de cambio.
- No commitear `.venv`, caches, bases de datos, HTML nuevo sin sanitizar, `.env`, credenciales ni artefactos locales.

## Dependencias

- TASK-011.
- TASK-012.
- TASK-014.
- TASK-013.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/favorites/service.py`
- `src/sources/base.py`
- `src/sources/armas_es/topic_fetcher.py`
- `src/sources/armas_es/urls.py`
- `src/app/config.py`
- `tests/test_favorites_service.py`
- `tests/test_openai_classifier.py`
- `tests/test_events_service.py`
- `tests/test_armas_urls.py`
- `tests/test_armas_topic_fetcher.py`
- `src/events/__init__.py`
- `src/favorites/__init__.py`
- `SPECs/task_specs/TASK-011_classifier_interface.md`
- `SPECs/task_specs/TASK-012_openai_classifier.md`
- `SPECs/task_specs/TASK-014_events_idempotency.md`
- `SPECs/task_specs/TASK-013_favorites_hashing_history.md`
- `SPECs/forum_scraper_tasks.md`
- Esta sub-SPEC si durante la implementacion se descubre una decision relevante.

Si el agente necesita tocar otro archivo, debe parar y justificarlo al usuario antes de editar.

## Requisitos Funcionales

### Contrato Fuente-Neutral Para Favoritos

- Crear un contrato pequeno, por ejemplo `TopicFetcher` o nombre equivalente, que permita a `FavoriteService` obtener un `ParsedTopic` completo por `external_topic_id` y/o `canonical_url`.
- El contrato debe exponer errores fuente-neutrales suficientes para favoritos:
  - transitorio;
  - topic no encontrado;
  - topic no disponible;
  - parseo incompleto o inconsistente.
- `FavoriteService` debe depender de ese contrato y de `ListingClassifier`; no debe conocer clases `Armas*`.

### Adapter armas.es Para Topic Completo

- Implementar el adapter bajo `src/sources/armas_es/`.
- Usar `ArmasEsClient` y `parse_topic_page` internamente.
- Obtener la primera pagina via URL canonica del topic.
- Si `total_pages == 1`, devolver el `ParsedTopic` de la primera pagina.
- Si `total_pages > 1`, obtener paginas adicionales secuencialmente con `start` de phpBB.
- No lanzar requests concurrentes.
- No superar el numero de paginas anunciado por el parser.
- Un fallo transitorio en cualquier pagina adicional debe propagarse como error transitorio fuente-neutral y evitar clasificacion parcial.
- Combinar posts manteniendo:
  - `topic_title`;
  - `external_topic_id`;
  - `original_author`;
  - `total_posts`;
  - `current_page=1`;
  - `total_pages`;
  - posts en orden global estable.

### Umbral De Confianza

- `FavoriteService.create_from_classification` debe recibir o conocer `match_confidence_threshold`.
- Solo crear favorito si:
  - `result.matches_watch_item is True`;
  - `result.listing_type == ListingType.OFFER`;
  - `result.confidence >= match_confidence_threshold`.
- No crear eventos ni historicos cuando el resultado queda bajo umbral.
- Mantener `price=None` sin borrar precio previo en updates.

### Seguridad De Eventos Y Retencion

- Los eventos emitidos por favoritos deben conservar solo payload estructurado minimo:
  - IDs de topic/favorite/watch item;
  - disponibilidad anterior/nueva;
  - precio anterior/nuevo;
  - moneda;
  - contador de confirmaciones cuando aplique.
- No incluir `TopicPost.text`, HTML, snippets completos, headers, cookies, API keys, passwords ni variables `.env`.
- Si se introduce validacion defensiva en `EventService`, debe aceptar los payloads existentes y rechazar de forma explicita strings con marcadores obvios de HTML/secrets. Esta validacion es opcional si los tests cubren exhaustivamente los llamadores de favoritos.

### Limpieza Documental

- Añadir `Contexto Minimo Para Agentes` a `TASK-011`, `TASK-012`, `TASK-014` y `TASK-013`, sin cambiar su estado `DONE`.
- Documentar en esta SPEC las verificaciones finales ejecutadas.

## Requisitos De Tests

Escribir o ajustar tests antes de la implementacion cuando el comportamiento actual no cumpla.

Tests minimos:

- `FavoriteService` no crea favorito con `confidence` bajo umbral.
- `FavoriteService` si crea favorito con `confidence == threshold`.
- `FavoriteService` no emite `NEW_FAVORITE`, `PriceHistoryORM` ni `StatusHistoryORM` cuando el resultado queda bajo umbral.
- `src/favorites/service.py` no importa `sources.armas_es`.
- `check_favorite` usa un fetcher fake fuente-neutral y no necesita parser/client armas.es.
- Error transitorio durante `check_favorite`:
  - actualiza `last_checked_at`;
  - no incrementa `unavailable_confirmation_count`;
  - no cambia `is_active`;
  - no emite `STATUS_CHANGED` ni `BECAME_UNAVAILABLE`;
  - devuelve `False`.
- No disponibilidad confirmada conserva la cobertura existente:
  - primera confirmacion no inactiva;
  - confirmacion configurada inactiva;
  - emite `STATUS_CHANGED` y `BECAME_UNAVAILABLE` una sola vez.
- Adapter armas.es multipagina:
  - primera pagina con `total_pages=2` provoca exactamente dos requests secuenciales;
  - combina posts de ambas paginas;
  - no duplica posts con el mismo `external_post_id`;
  - fallo transitorio en pagina 2 no devuelve topic parcial.
- Eventos generados por favoritos no contienen:
  - texto literal de posts de fixtures/test;
  - `<html`, `<div`, `<br`, `Cookie`, `Set-Cookie`, `Authorization`, `SMTP_PASSWORD`, `OPENAI_API_KEY`, `password`.
- OpenAI classifier mantiene input estructurado con:
  - `original_author`;
  - `posted_at`;
  - orden de posts;
  - sin headers/cookies/HTML.
- `ruff check` pasa para `src`, `tests` y `alembic`.

## Criterios De Aceptacion

- `pytest` completo pasa sin red.
- `./.venv/bin/ruff check src tests alembic` pasa.
- `src/favorites/` no contiene imports desde `sources.armas_es`.
- No hay URLs de armas.es hardcodeadas dentro de `src/favorites/`.
- Clasificaciones positivas bajo umbral no crean favoritos.
- Topics multipagina quedan representados en el hash de favoritos antes de llamar a IA.
- No se persiste texto completo de posts ni HTML completo en SQLite.
- No hay secrets, cookies ni HTML nuevo sin sanitizar en los archivos modificados.
- Las sub-SPECs de HITO-03 mantienen `Estado: DONE` y ganan contexto minimo explicito.
- `TASK-010` queda dependiente de `TASK-022` en el documento maestro.

## Verificacion Esperada

```bash
./.venv/bin/ruff check src tests alembic
pytest tests/test_favorites_service.py tests/test_armas_topic_fetcher.py tests/test_openai_classifier.py tests/test_events_service.py
pytest
rg -n "from sources\\.armas_es|import sources\\.armas_es|www\\.armas\\.es|viewtopic\\.php|viewforum\\.php" src/favorites
rg -n --pcre2 "Set-Cookie|Cookie:|PHPSESSID|Authorization|BEGIN (RSA|OPENSSH|PRIVATE)|api[_-]?key|password|SMTP_PASSWORD|OPENAI_API_KEY" src tests docs config
```

La penultima verificacion debe no devolver coincidencias. La ultima puede devolver referencias nominales de configuracion/tests, pero no secretos reales.

## Verificaciones Ejecutadas

Durante la implementacion de `TASK-022` se ha verificado:

```bash
pytest tests/test_favorites_service.py tests/test_armas_topic_fetcher.py tests/test_armas_urls.py
# 38 passed

pytest tests/test_favorites_service.py tests/test_armas_topic_fetcher.py tests/test_openai_classifier.py tests/test_events_service.py
# 34 passed

./.venv/bin/ruff check src tests alembic
# All checks passed

pytest
# 127 passed

rg -n "from sources\\.armas_es|import sources\\.armas_es|www\\.armas\\.es|viewtopic\\.php|viewforum\\.php" src/favorites
# Sin coincidencias

rg -n --pcre2 "Set-Cookie|Cookie:|PHPSESSID|Authorization|BEGIN (RSA|OPENSSH|PRIVATE)|api[_-]?key|password|SMTP_PASSWORD|OPENAI_API_KEY" src tests docs config
# Solo referencias nominales controladas en tests/config; sin secretos reales.
```

QA aprobo la tarea sin hallazgos bloqueantes. Riesgo residual: `TASK-010` debe cablear `ArmasEsTopicFetcher` con `ArmasEsClient` y pasar `canonical_url` desde discovery/bootstrap.

## Commit Sugerido

```text
fix: harden hito 03 favorite contracts
```

## Rama Y PR

- Rama sugerida: `TASK-022_hito_03_sanity_remediation`
- PR: https://github.com/alvarofergil/forum_scraper/pull/17
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
