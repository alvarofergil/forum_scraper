# Documento Maestro De Tareas - Forum Scraper v1

SPEC maestra: [forum_scraper.md](forum_scraper.md)  
Directorio de codigo: [`../`](../)  
Directorio de sub-SPECs: [`task_specs/`](task_specs/)

## Uso Obligatorio Por Agentes IA

Este documento es la fuente de verdad de project management.

Antes de trabajar, usar lectura progresiva:

1. leer [AGENT_START.md](AGENT_START.md);
2. usar este documento como indice: leer la fila de la tarea activa, dependencias directas y notas aplicables;
3. leer la sub-SPEC enlazada de la tarea activa;
4. leer [forum-task-agent](skills/forum-task-agent/SKILL.md) como checklist unico;
5. leer fragmentos de [forum_scraper.md](forum_scraper.md) solo cuando la tarea o duda actual lo requiera;
6. respetar archivos, dependencias y alcance de la sub-SPEC.

No leer este documento completo por defecto si una busqueda dirigida, la fila de tarea y las notas aplicables bastan para decidir. No leer sub-SPECs de otras tareas salvo que sean dependencias directas cuyo contrato sea necesario.

Usar un unico agente por defecto. PM, Arquitectura, Desarrollo, QA y Release son fases de una checklist interna; no se escriben handoffs ni se invocan subagentes salvo peticion explicita.

Antes de implementar cambios de repo, si la tarea se va a entregar en PR:

1. cambiar a `main` y ejecutar `git pull --ff-only origin main`;
2. crear una rama local descriptiva desde `main` con formato `TASK-XXX_slug_descriptivo`;
3. cambiar el estado de la tarea a `CLAIMED` o `IN_PROGRESS`.

Al terminar la implementacion local:

1. ejecutar todos los tests unitarios;
2. anotar comandos de verificacion;
3. no mezclar cambios de tareas distintas;
4. hacer commit, push y PR solo si el usuario lo pide o si la tarea activa lo exige expresamente.

Cuando se pida release:

1. hacer un commit de esa tarea;
2. hacer push de la rama de tarea;
3. crear PR desde la rama de tarea hacia `main`;
4. resolver cualquier conflicto del PR contra `main`;
5. usar `REVIEW` para PR abierto con tests verdes;
6. tras el merge, sincronizar `main`, actualizar la tarea a `DONE` y confirmar que la documentacion refleja el commit integrado.

## Estados Permitidos

| Estado | Significado |
|---|---|
| `TODO` | Lista para ser reclamada cuando sus dependencias esten completas. |
| `CLAIMED` | Un agente la ha reservado, pero todavia no hay cambios sustanciales. |
| `IN_PROGRESS` | Trabajo activo. No debe ser tomada por otro agente. |
| `BLOCKED` | Bloqueada por dependencia, acceso, decision o fallo externo. |
| `REVIEW` | Tests verdes, documentacion actualizada, commit realizado, rama subida y PR abierto hacia `main`; estado transitorio mientras el agente pertinente resuelve conflictos y cierra/mergea el PR. |
| `DONE` | PR mergeado en `main` y estado sincronizado en la documentacion. |

## Reglas Anti-Solapamiento

- Un agente no debe modificar archivos fuera del alcance de su sub-SPEC salvo que actualice la sub-SPEC y deje nota en esta tabla.
- Si dos tareas necesitan el mismo archivo, la dependencia debe quedar explicitada.
- Las migraciones Alembic se crean en una sola tarea activa cada vez.
- Las fixtures reales se capturan solo en la tarea autorizada para acceso controlado a armas.es.
- Los cambios de configuracion compartida deben coordinarse mediante el estado `BLOCKED` o una nueva tarea.
- Cada tarea usa [forum-task-agent](skills/forum-task-agent/SKILL.md) como checklist unico.
- No se simulan roles ni handoffs internos si no aportan una decision, implementacion, verificacion o release real.
- No se debe trabajar contra `develop` como rama de integracion normal; cada tarea usa una rama propia basada en `main`.
- No se debe hacer push directo a `main`.
- La rama local debe crearse despues de `git pull --ff-only origin main`.

## Guardrails Obligatorios Para Sub-SPECs

Cada tarea debe explicar tan bien sus limites como su objetivo. Al crear o modificar una sub-SPEC, el agente debe incluir guardrails concretos que indiquen:

- operaciones prohibidas en esa tarea;
- archivos o directorios que no deben tocarse;
- llamadas de red o servicios externos permitidos o prohibidos;
- datos que no deben persistirse, registrarse ni commitearse;
- decisiones funcionales, de coste, privacidad, legalidad, seguridad o arquitectura que requieren preguntar;
- funcionalidades tentadoras que quedan fuera porque pertenecen a otra tarea, otro hito o una version futura.

El apartado `Alcance Excluido` debe ser especifico y verificable. No basta con poner exclusiones genericas si existe riesgo de que un agente sobredimensione la tarea.

Si durante la implementacion aparece un comportamiento necesario pero fuera de los guardrails, el agente debe parar, actualizar la sub-SPEC o elevar la duda al usuario antes de implementarlo.

## Hitos Del Proyecto

| Hito | Objetivo | Tareas | Resultado esperado |
|---|---|---|---|
| HITO-00 | Base ejecutable del repo | TASK-001 | Proyecto Python testeable en la raiz del repo. |
| HITO-01 | Nucleo de configuracion, dominio y persistencia | TASK-002, TASK-003, TASK-004, TASK-005 | Config validada, SQLite/Alembic, URLs canonicas y cliente HTTP respetuoso. |
| HITO-01R | Correctivo tecnico post HITO-01 | TASK-020 | Persistencia UTC, esquema operativo minimo, errores HTTP y tests sin red endurecidos antes de HITO-02. |
| HITO-02 | Comprension controlada de armas.es | TASK-006, TASK-007, TASK-008, TASK-009 | Fixtures sanitizadas, parsers puros y matcher barato sin red. |
| HITO-02R | Correctivo tecnico post HITO-02 | TASK-021 | Contratos de parser y paginacion endurecidos antes de flujos consumidores. |
| HITO-03 | Clasificacion, eventos y favoritos | TASK-011, TASK-012, TASK-014, TASK-013 | Clasificador intercambiable, eventos idempotentes, favoritos con hashes e historicos. |
| HITO-03R | Correctivo tecnico post HITO-03 | TASK-022 | Contratos de favoritos, fuente, multipagina, umbrales y lint endurecidos antes de HITO-04. |
| HITO-04 | Flujos principales de ejecucion | TASK-010, TASK-016 | `bootstrap` y `run` funcionales, idempotentes y recuperables tras apagado. |
| HITO-04R | Correctivo tecnico post HITO-04 | TASK-023 | Checkpoints, favorites check, logging y consumo de IA endurecidos antes de HITO-05. |
| HITO-05 | Operacion diaria y notificaciones | TASK-015, TASK-017 | Email configurable, reintentos, status, inspeccion, favoritos manuales y backup. |
| HITO-05R | Correctivo tecnico post HITO-05 | TASK-024 | Backup con nombres seguros, notificaciones integradas en `run` y estado de eventos no notificables antes de HITO-06. |
| HITO-06 | Despliegue y cierre v1 | TASK-018, TASK-019 | Docker/Raspberry listo y DoD v1 verificada. |
| HITO-06R | Correctivo tecnico post HITO-06 | TASK-025 | Recuperacion de candidatos pendientes, resiliencia de favoritos y arranque operativo alineado. |

Notas de arquitectura del plan:

- Los IDs son estables, pero el orden real de ejecucion lo marcan las dependencias y los hitos.
- `candidate_matches` se incluye como persistencia tecnica para candidatos pendientes de clasificacion cuando `ai.enabled=false` o cuando una clasificacion no pueda completarse.
- El servicio de eventos se implementa antes de favoritos para que favoritos no tenga que inventar idempotencia propia.
- TASK-022 nace del sanity check post HITO-03 y debe completarse antes de implementar flujos que creen o monitoricen favoritos automaticamente en TASK-010.
- TASK-023 nace del sanity check post HITO-04 y debe completarse antes de HITO-05 para evitar derivar notificaciones y CLI operativa sobre checkpoints ambiguos.

## Tabla Maestra

| Hito | ID | Estado | Tarea | Modo | Sub-SPEC | Dependencias | Archivos principales | Commit sugerido |
|---|---|---|---|---|---|---|---|---|
| HITO-00 | TASK-001 | DONE | Scaffold Python, tooling y layout limpio | Agente unico | [TASK-001](task_specs/TASK-001_project_scaffold.md) | Ninguna | `pyproject.toml`, `src/`, `tests/` | `chore: scaffold python project` |
| HITO-01 | TASK-002 | DONE | Configuracion y modelos de dominio | Agente unico | [TASK-002](task_specs/TASK-002_config_and_domain_models.md) | TASK-001 | `src/app/config.py`, `src/app/models.py`, `config/` | `feat: add config and domain models` |
| HITO-01 | TASK-003 | DONE | SQLite, SQLAlchemy y Alembic | Agente unico | [TASK-003](task_specs/TASK-003_sqlite_alembic.md) | TASK-001, TASK-002 | `src/storage/`, `alembic/`, `alembic.ini` | `feat: add sqlite persistence with alembic` |
| HITO-01 | TASK-004 | DONE | URLs canonicas de armas.es | Agente unico | [TASK-004](task_specs/TASK-004_armas_urls.md) | TASK-002 | `src/sources/armas_es/urls.py` | `feat: add armas.es canonical urls` |
| HITO-01 | TASK-005 | DONE | Cliente HTTP respetuoso | Agente unico | [TASK-005](task_specs/TASK-005_armas_http_client.md) | TASK-002, TASK-004 | `src/sources/armas_es/client.py` | `feat: add armas.es http client` |
| HITO-01R | TASK-020 | DONE | Correctivo tecnico post HITO-01 | Agente unico | [TASK-020](task_specs/TASK-020_hito_01_corrective_hardening.md) | TASK-002, TASK-003, TASK-004, TASK-005 | `src/app/config.py`, `src/storage/`, `src/sources/armas_es/`, `tests/` | `fix: harden hito 01 technical foundations` |
| HITO-02 | TASK-006 | DONE | Politica de acceso y fixtures reales sanitizadas | Agente unico | [TASK-006](task_specs/TASK-006_access_policy_and_fixtures.md) | TASK-005, TASK-020 | `tests/fixtures/armas_es/`, `docs/` | `test: add sanitized armas.es fixtures` |
| HITO-02 | TASK-007 | DONE | Parser de listing `viewforum` | Agente unico | [TASK-007](task_specs/TASK-007_listing_parser.md) | TASK-004, TASK-006 | `src/sources/armas_es/listing_parser.py` | `feat: parse armas.es forum listings` |
| HITO-02 | TASK-008 | DONE | Parser de topic `viewtopic` | Agente unico | [TASK-008](task_specs/TASK-008_topic_parser.md) | TASK-004, TASK-006 | `src/sources/armas_es/topic_parser.py` | `feat: parse armas.es topics` |
| HITO-02 | TASK-009 | DONE | Normalizacion, watchlist y matcher | Agente unico | [TASK-009](task_specs/TASK-009_watchlist_matcher.md) | TASK-002, TASK-020 | `src/discovery/matcher.py` | `feat: add watchlist matching` |
| HITO-02R | TASK-021 | DONE | Correctivo tecnico post HITO-02 | Agente unico | [TASK-021](task_specs/TASK-021_hito_02_sanity_remediation.md) | TASK-006, TASK-007, TASK-008, TASK-009 | `src/sources/armas_es/listing_parser.py`, `src/sources/armas_es/urls.py`, `src/app/models.py`, `tests/test_listing_parser.py`, `tests/test_armas_urls.py`, `docs/armas_es_parser.md` | `fix: harden hito 02 parser contracts` |
| HITO-03 | TASK-011 | DONE | Interfaz de clasificacion y FakeClassifier | Agente unico | [TASK-011](task_specs/TASK-011_classifier_interface.md) | TASK-002, TASK-008 | `src/classification/` | `feat: add structured classifier interface` |
| HITO-03 | TASK-012 | DONE | Adaptador OpenAI configurable | Agente unico | [TASK-012](task_specs/TASK-012_openai_classifier.md) | TASK-011 | `src/classification/openai_classifier.py` | `feat: add openai structured classifier` |
| HITO-03 | TASK-014 | DONE | Eventos e idempotencia | Agente unico | [TASK-014](task_specs/TASK-014_events_idempotency.md) | TASK-003, TASK-020 | `src/events/service.py` | `feat: add event deduplication` |
| HITO-03 | TASK-013 | DONE | Favoritos, hashing e historicos | Agente unico | [TASK-013](task_specs/TASK-013_favorites_hashing_history.md) | TASK-003, TASK-005, TASK-008, TASK-011, TASK-014, TASK-020 | `src/favorites/` | `feat: add favorites monitoring` |
| HITO-03R | TASK-022 | DONE | Correctivo tecnico post HITO-03 | Agente unico | [TASK-022](task_specs/TASK-022_hito_03_sanity_remediation.md) | TASK-011, TASK-012, TASK-014, TASK-013 | `src/favorites/`, `src/sources/base.py`, `src/sources/armas_es/`, `tests/`, `SPECs/task_specs/TASK-011_classifier_interface.md`, `SPECs/task_specs/TASK-012_openai_classifier.md`, `SPECs/task_specs/TASK-014_events_idempotency.md`, `SPECs/task_specs/TASK-013_favorites_hashing_history.md` | `fix: harden hito 03 favorite contracts` |
| HITO-04 | TASK-010 | DONE | Bootstrap service y CLI | Agente unico | [TASK-010](task_specs/TASK-010_bootstrap_cli.md) | TASK-003, TASK-005, TASK-007, TASK-008, TASK-009, TASK-011, TASK-012, TASK-013, TASK-014, TASK-020, TASK-022 | `src/discovery/`, `src/app/cli.py` | `feat: add idempotent bootstrap` |
| HITO-04 | TASK-016 | DONE | Run incremental y recuperacion tras apagado | Agente unico | [TASK-016](task_specs/TASK-016_incremental_recovery.md) | TASK-010, TASK-013, TASK-014 | `src/discovery/service.py`, `src/app/cli.py` | `feat: add incremental recovery` |
| HITO-04R | TASK-023 | DONE | Correctivo tecnico post HITO-04 | Agente unico | [TASK-023](task_specs/TASK-023_hito_04_sanity_remediation.md) | TASK-010, TASK-016 | `src/discovery/service.py`, `src/favorites/service.py`, `src/app/cli.py`, `tests/` | `fix: harden hito 04 run contracts` |
| HITO-05 | TASK-015 | DONE | Email SMTP y retry de notificaciones | Agente unico | [TASK-015](task_specs/TASK-015_email_notifications.md) | TASK-014 | `src/notifications/email.py` | `feat: add configurable email notifications` |
| HITO-05 | TASK-017 | DONE | CLI operativa: status, favorites, inspect, backup | Agente unico | [TASK-017](task_specs/TASK-017_operational_cli.md) | TASK-003, TASK-013, TASK-015, TASK-016 | `src/app/cli.py`, `src/storage/` | `feat: add operational cli commands` |
| HITO-05R | TASK-024 | DONE | Correctivo tecnico post HITO-05 | Agente unico | [TASK-024](task_specs/TASK-024_hito_05_sanity_remediation.md) | TASK-015, TASK-017, TASK-023 | `src/app/cli.py`, `src/notifications/email.py`, `src/storage/operational.py`, `tests/`, `README.md` | `fix: harden hito 05 operational contracts` |
| HITO-06 | TASK-018 | DONE | Docker, Raspberry readiness y README | Agente unico | [TASK-018](task_specs/TASK-018_docker_raspberry.md) | TASK-024 | `Dockerfile`, `docker-compose.yml`, `README.md` | `feat: add portable docker deployment` |
| HITO-06 | TASK-019 | DONE | Hardening final y DoD v1 | Agente unico | [TASK-019](task_specs/TASK-019_final_acceptance.md) | TASK-001..TASK-018, TASK-020 | todo el proyecto | `test: complete v1 acceptance coverage` |
| HITO-06R | TASK-025 | DONE | Correctivo post HITO-06: recuperacion de pendientes y arranque operativo | Agente unico | [TASK-025](task_specs/TASK-025_hito_06_sanity_remediation.md) | TASK-018, TASK-019, TASK-024 | `src/discovery/service.py`, `src/favorites/service.py`, `src/storage/repositories.py`, `src/app/cli.py`, `config/config.example.yaml`, `README.md`, `tests/` | `fix: harden pending recovery after hito 06` |

## Notas De Coordinacion

- Git se inicializa al comenzar TASK-001 si no existe repositorio.
- Cada tarea debe actualizar su propia sub-SPEC si durante la implementacion se descubre una decision relevante.
- Las sub-SPECs son contratos vivos, pero todo cambio debe ser pequeno, trazable y compatible con la SPEC maestra.
- El proyecto se considera desplegable desde la raiz del repo.
- TASK-020 nace del analisis adversarial de HITO-01 y debe completarse antes de iniciar nuevas tareas de HITO-02, salvo decision explicita del usuario.
- TASK-021 nace del sanity check post HITO-02 y debe completarse antes de implementar servicios que consuman automaticamente `ParsedListingPage.next_page_url`.
- TASK-022 nace del sanity check post HITO-03 y debe completarse antes de `TASK-010`.
- TASK-023 nace del sanity check post HITO-04 y debe completarse antes de `TASK-015` y `TASK-017`.
- TASK-024 nace del sanity check post HITO-05 y debe completarse antes de `TASK-018` para no construir Docker/Raspberry sobre contratos operativos ambiguos.
- TASK-025 nace del sanity check post HITO-06 y quedo completada tras el merge del PR #26.
