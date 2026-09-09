# TASK-009 - Normalizacion, Watchlist Y Matcher

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar normalizacion textual y matcher determinista barato basado en marca y modelo.

## Alcance Incluido

- Normalizacion Unicode/lowercase/espacios/guiones/puntuacion.
- Matching de `brand + model`.
- Matching de aliases.
- Resultado con watch items candidatos.

## Alcance Excluido

- IA.
- Persistencia.
- Fuzzy avanzado salvo utilidad simple justificada.

## Guardrails Especificos

- No llamar a IA ni introducir dependencias de OpenAI u otros servicios externos.
- No leer ni escribir SQLite, eventos, favoritos ni historicos.
- No descargar topics ni usar HTML completo; solo `title + snippet` del listing y datos de config.
- No convertir candidatos en favoritos ni descartar definitivamente topics por baja confianza.
- No hardcodear marcas, modelos, categorias ni aliases en Python; todo debe venir de `config/config.yaml` o fixtures de test.

## Dependencias

- TASK-002.
- TASK-020.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/discovery/matcher.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Usar `title + snippet` del listing.
- Favorecer recall frente a precision.
- No convertir favoritos por si solo.

## Requisitos De Tests

- Marca y modelo detectan candidato.
- Solo marca no debe bastar por defecto.
- Solo modelo no debe bastar por defecto salvo alias explicito.
- Alias detecta candidato.
- Normalizacion cubre mayusculas, acentos, guiones y espacios.

## Criterios De Aceptacion

- Matcher puro y rapido.
- Sin requests y sin IA.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

- PR: https://github.com/alvarofergil/forum_scraper/pull/11
- `.venv/bin/python -m pytest`: 68 passed.
- `.venv/bin/python -m ruff check .`: passed.

## Commit Sugerido

```text
feat: add watchlist matching
```

## Rama Y PR

- Rama sugerida: `TASK-009_watchlist_matcher`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
