# TASK-003 - SQLite, SQLAlchemy Y Alembic

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Crear persistencia SQLite mantenible con SQLAlchemy y migraciones Alembic.

## Alcance Incluido

- Engine SQLite.
- Modelos ORM.
- Alembic configurado.
- Migracion inicial.
- Repositorios basicos.
- PRAGMAs `WAL` y `foreign_keys=ON`.

## Alcance Excluido

- Servicios de negocio completos.
- Backup.
- Docker.

## Guardrails Especificos

- No implementar discovery, scraping, matching, clasificacion, favoritos, eventos de negocio, email ni comandos CLI operativos.
- No introducir PostgreSQL, Redis, colas externas ni otra fuente de estado operativo distinta de SQLite.
- No almacenar texto completo de posts, HTML completo, cookies, secrets ni payloads sensibles.
- No crear mas de una linea de migracion activa ni cambios de esquema fuera del alcance conceptual aprobado.
- No usar la base de datos real del usuario en tests; todas las pruebas deben usar SQLite temporal o aislado.

## Dependencias

- TASK-001.
- TASK-002.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/storage/`
- `alembic/`
- `alembic.ini`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Tablas: `topics`, `candidate_matches`, `favorites`, `price_history`, `status_history`, `topic_posts`, `events`, `app_state`.
- `topics.external_topic_id` debe ser unico y no nulo.
- `candidate_matches` debe poder guardar candidatos por `topic_id` y `watch_item_id`, con estado de clasificacion pendiente/clasificado/descartado.
- `events.deduplication_key` debe ser unico.
- No almacenar texto completo de posts en v1, solo hashes/metadatos.

## Requisitos De Tests

- Migracion inicial crea todas las tablas.
- Unicidad de topic externo.
- Unicidad de candidato por topic y watch item.
- Unicidad de deduplicacion de eventos.
- Foreign keys activas.

## Criterios De Aceptacion

- Base temporal de tests se crea y migra desde cero.
- Repositorios permiten operaciones minimas para tareas posteriores.

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
feat: add sqlite persistence with alembic
```

## Rama Y PR

- Rama sugerida: `TASK-003_sqlite_alembic`
- PR: https://github.com/alvarofergil/forum_scraper/pull/4
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
