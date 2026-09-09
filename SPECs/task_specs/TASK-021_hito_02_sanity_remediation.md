# TASK-021 - Correctivo Tecnico Post HITO-02

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Subsanar las desviaciones menores detectadas tras el sanity check de HITO-02 antes de que los servicios de discovery, bootstrap o run consuman automaticamente los parsers y sus URLs de paginacion.

## Alcance Incluido

- Endurecer la generacion y validacion de `next_page_url` en el parser de listing.
- Eliminar el hardcode de `f=96` en el fallback de paginacion y usar siempre el `forum_id` configurado.
- Impedir que `next_page_url` pueda apuntar fuera del host configurado, fuera de `/foros/viewforum.php` o a otro foro no configurado.
- Resolver y documentar la ambiguedad entre `ParsedListingPage.next_page_url` y `TopicListing.next_page_url`.
- Alinear tests y documentacion tecnica de parser con el contrato final elegido.

## Alcance Excluido

- Implementar `bootstrap`, `run`, discovery incremental o descarga de topics.
- Implementar clasificacion IA, favoritos, eventos, notificaciones o CLI.
- Refrescar fixtures mediante nuevas peticiones reales a armas.es.
- Cambiar el cliente HTTP salvo que sea estrictamente necesario para compartir validacion de URLs y quede documentado en esta SPEC.
- Cambiar migraciones Alembic o esquema SQLite.
- Redisenar los parsers o sustituir el parser HTML actual por otra libreria.

## Guardrails Especificos

- No realizar llamadas de red durante la tarea; los tests deben usar HTML inline o fixtures ya sanitizadas.
- No introducir dependencias runtime nuevas salvo aprobacion explicita del revision.
- No aceptar enlaces absolutos externos como `next_page_url`; deben fallar explicitamente o descartarse de forma documentada y testeada.
- No volver a introducir `sid`, `p`, anchors, posicion de pagina o titulo como identidad o paginacion persistible.
- No alterar el matching de watchlist salvo tests de no regresion necesarios para verificar que sigue fuera de este cambio.
- Si la resolucion de `TopicListing.next_page_url` exige cambiar la SPEC maestra, hacerlo de forma minima y dejar una nota de decision.
- Si aparece una necesidad de acceso real a armas.es, bloquear la tarea y pedir decision antes de avanzar.

## Dependencias

- TASK-006.
- TASK-007.
- TASK-008.
- TASK-009.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/sources/armas_es/listing_parser.py`
- `src/sources/armas_es/urls.py`, solo si se reutiliza una validacion comun.
- `src/app/models.py`, solo si se decide eliminar o ajustar `TopicListing.next_page_url`.
- `tests/test_listing_parser.py`
- `tests/test_armas_urls.py`, solo si se toca `urls.py`.
- `docs/armas_es_parser.md`
- `SPECs/forum_scraper.md`, solo para aclarar el contrato pagina-vs-topic de `next_page_url`.
- `SPECs/forum_scraper_tasks.md`
- esta sub-SPEC si se descubre una decision relevante.

## Requisitos Funcionales

- `parse_listing_page(..., forum_id=<N>)` debe usar `<N>` al construir la URL fallback de siguiente pagina.
- `next_page_url` debe normalizarse sin `sid`, sin `p` y sin anchor.
- Un enlace de siguiente pagina absoluto hacia otro host debe producir `next_page_url=None` y quedar cubierto por test.
- Un enlace de siguiente pagina hacia un path distinto de `/foros/viewforum.php` debe producir `next_page_url=None` y quedar cubierto por test.
- Un enlace de siguiente pagina con `f` distinto del `forum_id` configurado debe producir `next_page_url=None` y quedar cubierto por test.
- El contrato final debe dejar claro que la paginacion del listing es informacion de pagina (`ParsedListingPage.next_page_url`) y que `TopicListing` no duplica esa semantica.

## Requisitos De Tests

- Test primero para demostrar que el fallback no debe devolver `f=96` cuando `forum_id` configurado es otro.
- Test primero para enlace `li.next a[rel="next"]` externo con `sid`, verificando que nunca se devuelve una URL externa.
- Test primero para enlace `li.next a[rel="next"]` a otro path o foro no configurado.
- Test de no regresion para fixture real: `listing_page_2.html` sigue devolviendo `https://www.armas.es/foros/viewforum.php?f=96&start=36`.
- Test de no regresion para exclusión de `Anuncios` y extraccion de topics ordinarios.
- Ejecutar todos los tests unitarios sin red.

## Criterios De Aceptacion

- `pytest` pasa completo sin conexion externa.
- `ruff check .` pasa completo desde la raiz del repo.
- No hay nuevos secretos, cookies, `sid` persistible ni HTML bruto sin sanitizar en el repositorio.
- El parser de listing no inventa URLs hacia foros no configurados ni hosts externos.
- La ambiguedad de `next_page_url` queda resuelta en codigo, tests y documentacion.
- No se modifica funcionalidad de IA, favoritos, eventos, notificaciones, CLI ni persistencia.

## Verificacion Esperada

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
rg -n --pcre2 "sid=|Set-Cookie|Cookie:|PHPSESSID|csrf|token|Authorization|BEGIN (RSA|OPENSSH|PRIVATE)|api[_-]?key|password" tests/fixtures docs config src
```

## Verificacion Ejecutada

- PR: https://github.com/alvarofergil/forum_scraper/pull/12
- Merge commit: `657e40cffe7ec197a218ddc577821436e684f495`.
- `.venv/bin/python -m pytest -q`: 80 passed.
- `.venv/bin/python -m ruff check .`: passed.
- `git diff --check`: passed.
- `rg --pcre2` sobre `tests/fixtures docs config src`: sin coincidencias sensibles reales; solo referencias nominales a `smtp_password` en `src/app/config.py`.
- QA: verificacion independiente sin red sobre tests de listing, URLs, lint y whitespace; sin secretos reales detectados.

## Commit Sugerido

```text
fix: harden hito 02 parser contracts
```

## Rama Y PR

- Rama: `TASK-021_hito_02_sanity_remediation`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
