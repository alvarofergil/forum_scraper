# TASK-020 - Correctivo Tecnico Post HITO-01

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Corregir la deuda tecnica detectada en el analisis adversarial de HITO-01 antes de continuar con HITO-02, reforzando la persistencia SQLite, la semantica temporal UTC, la estructura minima de favoritos/eventos, la clasificacion de errores HTTP y las defensas de tests sin red.

Esta tarea no cambia el producto funcional visible. Su objetivo es que las tareas de parsers, discovery, favoritos, eventos y notificaciones puedan construirse sobre contratos tecnicos fiables.

## Origen Del Correctivo

El analisis adversarial de HITO-01 fue realizado como revision adversarial tras sincronizar `main` con `origin/main`.

Hallazgos que esta tarea debe resolver:

- Los `datetime` UTC se persisten en SQLite pero se recuperan como naive.
- `favorites` no contiene todos los campos operativos que la SPEC v1 ya define.
- `events` no contiene `payload_json`.
- Los PRAGMAs SQLite no quedan garantizados en el camino de migraciones Alembic.
- La clasificacion de errores HTTP es insuficiente para distinguir errores transitorios, topic no encontrado y topic no disponible.
- La validacion de `source.base_url` y de URLs de topic es demasiado permisiva.
- El repositorio de candidatos no ofrece una operacion idempotente para overlaps futuros.
- La suite no tiene una guardia global que impida red accidental en tests unitarios.

## Alcance Incluido

- Ajustar almacenamiento de timestamps para que todo `datetime` persistido y recuperado por SQLite sea timezone-aware en UTC.
- Anadir tests de round-trip temporal en SQLite.
- Completar `favorites` con los campos conceptuales necesarios para v1:
  - `is_active`;
  - `last_checked_at`;
  - `last_content_hash`;
  - `last_classified_at`.
- Completar `events` con `payload_json` para conservar payload estructurado de evento.
- Crear una migracion Alembic correctiva compatible con la migracion inicial existente.
- Mantener ORM y migraciones sincronizados.
- Garantizar o documentar tecnicamente que los PRAGMAs `foreign_keys=ON` y `journal_mode=WAL` se aplican en las rutas operativas y de migracion que use la aplicacion.
- Endurecer `source.base_url` para exigir URL absoluta con scheme y host.
- Endurecer utilidades de URL de `armas_es` para no convertir enlaces externos arbitrarios con parametro `t` en topics canonicos internos.
- Anadir errores HTTP mas expresivos, como minimo para:
  - fallo transitorio agotado;
  - topic no encontrado;
  - topic no disponible o acceso no viable;
  - bloqueo explicito.
- Mantener retries acotados y delay secuencial.
- Anadir una operacion idempotente para candidatos, por ejemplo `get_or_create_pending`, sin eliminar la restriccion unica existente.
- Anadir una guardia de tests que impida sockets/red por defecto, dejando claro como se autorizan tests especiales de acceso real en TASK-006 si fueran necesarios.
- Actualizar README o notas minimas si alguna descripcion queda objetivamente desactualizada por HITO-01.

## Alcance Excluido

- No implementar parsers HTML de listing ni topic.
- No capturar fixtures reales de armas.es.
- No hacer requests reales a armas.es.
- No implementar discovery, bootstrap, run incremental, favoritos de negocio, eventos de negocio ni notificaciones SMTP.
- No integrar OpenAI ni crear clasificadores reales.
- No cambiar el formato funcional de la watchlist salvo validaciones de configuracion necesarias.
- No introducir scheduler interno, concurrencia, colas externas, Redis, PostgreSQL ni servicios adicionales.
- No redisenar todo el modelo de persistencia fuera de los campos y garantias indicados.
- No borrar historicos, favoritos ni datos existentes en migraciones.
- No marcar tareas anteriores como reabiertas ni modificar sus estados `DONE`; este correctivo debe quedar trazado como nueva tarea.

## Guardrails Especificos

- Cualquier cambio de esquema debe ir en una unica revision Alembic nueva, posterior a `0001_initial_schema`.
- La migracion debe ser aditiva o conservadora. Si se necesita transformar datos, debe preservar valores existentes.
- No almacenar texto completo de posts, HTML completo, cookies, cabeceras sensibles, tokens, API keys ni passwords.
- `payload_json` no debe convertirse en excusa para guardar HTML o datos sensibles; debe almacenar payloads estructurados de eventos.
- Las fechas deben normalizarse a UTC de forma explicita en la frontera de persistencia. No basta con confiar en `DateTime(timezone=True)` de SQLite.
- Tests unitarios no deben tocar red. Si se introduce una excepcion tecnica para TASK-006, debe quedar fuera de la suite unitaria por defecto y documentada.
- El cliente HTTP no debe anadir mecanismos de evasion, fingerprinting, proxies, login ni cookies persistentes.
- La validacion de URLs debe respetar `base_url` configurado, pero sin aceptar hosts externos como identidad interna.
- No relajar constraints existentes de unicidad:
  - `topics.external_topic_id`;
  - candidato por `topic_id` y `watch_item_id`;
  - `events.deduplication_key`.
- No usar `git reset`, force-push ni cambios destructivos.

## Dependencias

- TASK-002.
- TASK-003.
- TASK-004.
- TASK-005.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/app/config.py`
- `src/app/models.py`
- `src/storage/`
- `src/sources/armas_es/urls.py`
- `src/sources/armas_es/client.py`
- `alembic/`
- `tests/`
- `README.md`
- `SPECs/forum_scraper_tasks.md`
- `SPECs/task_specs/TASK-020_hito_01_corrective_hardening.md`

## Requisitos Funcionales

### Persistencia Temporal UTC

- Todo timestamp creado por la aplicacion debe almacenarse y recuperarse como `datetime` timezone-aware en UTC.
- Si una fecha naive llega a la frontera de persistencia, el comportamiento debe ser explicito:
  - rechazarla con error claro; o
  - interpretarla como UTC solo si esta decision queda documentada en codigo/test.
- Las comparaciones futuras entre fechas de dominio y fechas recuperadas de SQLite no deben mezclar aware/naive.

### Esquema De Favoritos

- `favorites` debe incluir:
  - `is_active`, booleano no nulo con default compatible;
  - `last_checked_at`, nullable;
  - `last_content_hash`, nullable;
  - `last_classified_at`, nullable.
- `status` debe seguir restringido a los valores de disponibilidad definidos.
- Los datos existentes deben migrar sin perdida.

### Esquema De Eventos

- `events` debe incluir `payload_json`, nullable o con default seguro.
- El repositorio de eventos debe permitir crear eventos con payload estructurado sin duplicar eventos por `deduplication_key`.
- El payload debe poder serializarse de forma determinista o al menos estable para tests.

### PRAGMAs SQLite

- Las conexiones creadas por la aplicacion deben activar `foreign_keys=ON` y `journal_mode=WAL`.
- El helper de migracion debe usar el mismo criterio o debe haber una verificacion automatizada que demuestre que la base resultante cumple los PRAGMAs cuando se usa por la app.
- Los tests deben cubrir la ruta `run_migrations()`.

### URL Y Configuracion

- `source.base_url` debe rechazarse si no es una URL absoluta con scheme HTTP/HTTPS y host.
- Las utilidades de topic de `armas_es` deben rechazar, al normalizar identidad, URLs absolutas cuyo host no corresponda al `base_url` configurado.
- URLs relativas validas del foro deben seguir resolviendo correctamente.
- URLs sin `t`, con `t` vacio o con host externo deben fallar de forma explicita.

### Cliente HTTP

- El cliente debe conservar:
  - User-Agent configurable;
  - timeout configurable;
  - retry acotado;
  - delay secuencial entre requests;
  - separacion total de parsing.
- Deben existir errores distinguibles para que tareas futuras puedan mapear:
  - error transitorio agotado;
  - no encontrado;
  - no disponible/acceso no viable;
  - bloqueo explicito.
- No debe reintentar indefinidamente ni ignorar bloqueos explicitos.

### Repositorios

- Debe existir una operacion idempotente para candidatos por topic/watch item.
- `TopicRepository.upsert_listing()` no debe borrar metadatos previamente conocidos cuando un parse parcial entregue `None`, salvo que la SPEC de parser futura decida explicitamente lo contrario.

### Tests Sin Red

- La suite unitaria debe fallar si un test intenta abrir red por accidente.
- Los tests del cliente HTTP deben seguir usando transporte fake/mock.
- TASK-006, que si puede requerir acceso controlado para politica/fixtures, debera separar cualquier acceso real de la suite unitaria normal.

## Requisitos De Tests

- Test de round-trip SQLite que inserta timestamps UTC y verifica que al recargar siguen siendo aware UTC.
- Test de rechazo o normalizacion explicita de timestamp naive en la capa elegida.
- Test de migracion que confirma columnas nuevas de `favorites` y `events`.
- Test de `payload_json` en `EventRepository.create_once`.
- Test de idempotencia de candidatos con la nueva operacion.
- Test de `TopicRepository.upsert_listing()` preservando metadatos existentes ante `None` parcial.
- Test de `run_migrations()` y PRAGMAs relevantes.
- Test de config que rechaza `source.base_url` invalida.
- Test de URL que rechaza host externo con parametro `t`.
- Tests de cliente HTTP para errores diferenciados:
  - 404 topic no encontrado;
  - 410 o equivalente como no disponible, si se modela;
  - transitorio agotado;
  - bloqueo explicito sin retry.
- Test o fixture autouse que bloquee red en tests unitarios.
- Suite completa verde.
- Ruff verde.

## Criterios De Aceptacion

- `pytest` pasa completo sin acceso a red.
- `ruff check .` pasa.
- La migracion correctiva se aplica desde una base creada por `0001_initial_schema`.
- ORM, repositorios y migraciones representan los mismos campos.
- No hay secrets, HTML real sin sanitizar ni bases de datos reales commiteadas.
- La revision valida que no se han roto limites entre config, storage, source adapter y cliente HTTP.
- QA valida que los hallazgos adversariales quedan cubiertos por tests.
- La tarea queda en `REVIEW` solo despues de commit, push y PR hacia `main`.

## Verificacion Esperada

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Commit Sugerido

```text
fix: harden hito 01 technical foundations
```

## Rama Y PR

- Rama sugerida: `TASK-020_hito_01_corrective_hardening`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
