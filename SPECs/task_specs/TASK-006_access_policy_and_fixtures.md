# TASK-006 - Politica De Acceso Y Fixtures Reales Sanitizadas

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Validar acceso publico responsable y capturar fixtures HTML reales sanitizadas para tests.

## Alcance Incluido

- Revisar `robots.txt`.
- Revisar condiciones aplicables si estan disponibles.
- Capturar un numero minimo de paginas reales.
- Sanitizar fixtures antes de commit.
- Documentar selectores candidatos y politica de acceso.

## Alcance Excluido

- Scraping masivo.
- Activacion periodica.
- Parser definitivo.

## Guardrails Especificos

- No realizar mas peticiones reales que las minimas indicadas en esta tarea; todo acceso debe ser secuencial, con delay y documentado.
- No usar proxies, login, cookies manuales, CAPTCHA bypass, fingerprint evasion ni ningun mecanismo de evasion.
- No commitear HTML bruto sin sanitizar, `sid`, cookies, tokens, datos sensibles o contenido innecesario.
- No implementar parsers definitivos ni logica de negocio; documentar selectores candidatos y crear fixtures.
- Si `robots.txt` o condiciones del sitio generan duda razonable, bloquear la tarea y preguntar antes de capturar fixtures.

## Dependencias

- TASK-005.
- TASK-020.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `tests/fixtures/armas_es/`
- `docs/access_policy.md`
- `docs/armas_es_parser.md`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Peticiones reales muy controladas, secuenciales y con delay.
- Capturar como minimo listings pagina 1 y 2.
- Capturar topics de una pagina y multipost/multipagina si se identifica sin exceso de navegacion.
- Eliminar `sid`, cookies, datos sensibles o contenido innecesario antes de commit.

## Requisitos De Tests

- Tests pueden leer fixtures.
- No requieren red.

## Criterios De Aceptacion

- Fixtures existen y son suficientes para TASK-007/TASK-008.
- Politica de acceso queda documentada.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- PR: https://github.com/alvarofergil/forum_scraper/pull/8
- `.venv/bin/python -m pytest`: 49 passed.
- `.venv/bin/python -m ruff check .`: passed.
- `rg --pcre2` sobre `tests/fixtures/armas_es`: sin coincidencias sensibles.
- QA: `env PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider`: 49 passed.

## Commit Sugerido

```text
test: add sanitized armas.es fixtures
```

## Rama Y PR

- Rama sugerida: `TASK-006_access_policy_and_fixtures`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
