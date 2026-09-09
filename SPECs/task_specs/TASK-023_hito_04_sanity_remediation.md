# TASK-023 - Correctivo Tecnico Post HITO-04

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Endurecer los contratos de `bootstrap` y `run` entregados en HITO-04 antes de construir notificaciones y CLI operativa sobre ellos. La tarea debe corregir desviaciones detectadas en el sanity check post HITO-04: checkpoints ambiguos, falta de warning al alcanzar el safety limit, respeto de `favorites.check_every_run`, y trabajo repetido/evitable sobre candidatos ya clasificados o descartados.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila de `TASK-023` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien:

- `SPECs/task_specs/TASK-010_bootstrap_cli.md`.
- `SPECs/task_specs/TASK-016_incremental_recovery.md`.
- Fragmentos de `SPECs/forum_scraper.md`:
  - `#11-bootstrap`.
  - `#12-run-incremental`.
  - `#13-discovery-incremental`.
  - `#15-favorites-check`.
  - `#17-clasificacion`.
  - `#26-logs`.
  - `#28-tests-obligatorios`.
- Codigo afectado:
  - `src/discovery/service.py`.
  - `src/favorites/service.py`.
  - `src/app/cli.py`.
  - tests relacionados bajo `tests/`.

## Observaciones Del Sanity Check

1. `src/discovery/service.py` alcanza `max_pages_per_run` sin registrar ningun warning, aunque `TASK-016` y la SPEC maestra exigen warning cuando no se llega al cutoff.
2. `favorites.check_every_run` se parsea en configuracion, pero no se respeta en runtime; `run_once()` ejecuta `_run_favorites_check()` siempre.
3. `_run_favorites_check()` marca `last_successful_favorites_check_at` aunque `self.classifier is None` y existan favoritos activos, devolviendo `favorites_checked=0`. Esto puede hacer que la operacion parezca correcta cuando en realidad no ha comprobado favoritos.
4. `_process_listings()` vuelve a descargar y clasificar candidatos aunque exista un `candidate_matches` previo con estado `CLASSIFIED` o `DISCARDED`. Esto aumenta coste de IA y peticiones de topic sin necesidad clara.
5. La primera ejecucion incremental sin `last_successful_discovery_at` no tiene una politica explicita. Tras bootstrap solo existe `bootstrap_completed_at`, por lo que el primer `run` puede recorrer hasta `max_pages_per_run` y no avanzar checkpoint si no encuentra pagina vacia. La tarea debe cerrar este contrato con comportamiento testeado.

## Alcance Incluido

- Anadir logging estructurado minimo en `DiscoveryService` para el caso `max_pages_per_run` sin cutoff.
- Hacer que `run_once()` respete `config.favorites.check_every_run`.
- Definir y aplicar una semantica segura para favorites check cuando no hay clasificador disponible:
  - si no hay favoritos activos, puede considerarse check completo;
  - si hay favoritos activos y no hay clasificador, no debe marcarse `last_successful_favorites_check_at` como exito silencioso;
  - el resultado de `RunResult` debe permitir distinguir check saltado o incompleto si hace falta.
- Evitar reclasificar candidatos con estado terminal (`CLASSIFIED` o `DISCARDED`) durante discovery normal, salvo que exista una razon funcional documentada y cubierta por tests.
- Mantener reintento de candidatos `PENDING` cuando la IA este activa y haya clasificador disponible.
- Definir y testear el comportamiento del primer `run` sin `last_successful_discovery_at`:
  - opcion preferida: usar `bootstrap_completed_at` como checkpoint inicial si existe;
  - si no existe bootstrap previo, permitir discovery acotado, pero no fingir checkpoint completo si se alcanza el safety limit.
- Ajustar salida CLI de `run` si se amplian campos de `RunResult` para indicar `favorites_skipped`, `favorites_completed` o equivalente.
- Actualizar tests existentes o anadir nuevos tests unitarios sin red.

## Alcance Excluido

- No implementar email, retries de notificaciones ni SMTP.
- No implementar comandos `status`, `favorites`, `inspect`, `backup`, `retry-notifications` ni `favorite deactivate/reactivate`.
- No introducir scheduler, daemon, bucles periodicos, cron ni systemd.
- No modificar el adaptador OpenAI salvo que sea imprescindible para tipos o tests; no cambiar prompts ni modelo por defecto.
- No cambiar parsers HTML ni fixtures reales salvo que un test unitario focalizado lo requiera de forma directa.
- No introducir nuevas tablas o migraciones Alembic salvo aprobacion explicita del usuario; la correccion debe preferir `app_state` y campos existentes.
- No hacer llamadas de red en tests.

## Guardrails Especificos

- Mantener acceso secuencial y de baja carga: no concurrencia, no prefetch, no apertura de topics no candidatos salvo favoritos activos.
- No borrar favoritos, historicos, eventos ni candidatos existentes.
- No marcar checkpoints de exito cuando una fase requerida se haya saltado por falta de clasificador, limite de paginas o excepcion recuperable.
- No convertir automaticamente candidatos pendientes en favoritos si `ai.enabled=false`.
- No descartar candidatos `PENDING` solo porque falte clasificador.
- No reclasificar `DISCARDED` o `CLASSIFIED` en discovery normal sin cambio persistido que lo justifique.
- No registrar HTML completo, secretos, cookies, API keys ni datos de entorno sensibles.
- Si se decide cambiar la forma publica de `RunResult`, actualizar todos los tests y la salida CLI afectada en la misma tarea.

## Dependencias

- `TASK-010`.
- `TASK-016`.
- Contratos de soporte ya completados:
  - `TASK-013` favoritos.
  - `TASK-014` eventos.
  - `TASK-022` correctivo post HITO-03.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/discovery/service.py`
- `src/favorites/service.py`
- `src/app/cli.py`
- `src/app/__main__.py` (solo ajuste mecanico de lint del entrypoint CLI si `ruff check .` lo exige)
- `tests/test_discovery_bootstrap.py`
- `tests/test_cli.py`
- `tests/test_favorites_service.py`
- `SPECs/task_specs/TASK-023_hito_04_sanity_remediation.md`
- `SPECs/forum_scraper_tasks.md`

Si se necesita tocar otro archivo, actualizar primero esta sub-SPEC explicando el motivo.

## Requisitos Funcionales

1. Cuando discovery alcance `max_pages_per_run` sin encontrar cutoff:
   - `RunResult.discovery_completed` debe ser `False`;
   - `RunResult.discovery_limit_reached` debe ser `True`;
   - `last_successful_discovery_at` no debe avanzar;
   - debe registrarse un warning con datos suficientes: pagina/offset, limite configurado y si habia checkpoint previo.
2. Si `favorites.check_every_run=false`:
   - `run_once()` debe saltar favorites check;
   - no debe descargar topics de favoritos por esa fase;
   - no debe avanzar `last_successful_favorites_check_at`;
   - la salida CLI debe reflejar que la fase fue saltada si `RunResult` lo modela.
3. Si `favorites.check_every_run=true`, hay favoritos activos y no hay clasificador disponible:
   - no debe tratarse como check exitoso silencioso;
   - no debe avanzar `last_successful_favorites_check_at`;
   - debe emitirse resultado o warning que permita diagnosticar la fase incompleta;
   - no debe lanzar una excepcion no controlada desde CLI por este caso.
4. Si no hay favoritos activos:
   - la fase puede completarse sin llamadas a topic fetcher;
   - `last_successful_favorites_check_at` puede avanzar si la fase no fue saltada por configuracion.
5. Durante discovery, un candidato existente con estado `PENDING` debe poder reintentarse cuando `ai.enabled=true` y haya clasificador.
6. Durante discovery, un candidato existente con estado `CLASSIFIED` o `DISCARDED` no debe volver a descargar topic ni llamar a IA por defecto.
7. La primera ejecucion de `run` posterior a bootstrap debe tener checkpoint inicial definido:
   - si `last_successful_discovery_at` no existe y `bootstrap_completed_at` existe, usar `bootstrap_completed_at` como referencia de cutoff;
   - documentar con test que no se hace una exploracion innecesaria hasta `max_pages_per_run` cuando el bootstrap ya establece un punto operativo razonable.
8. La salida de `python -m app run` debe seguir siendo de una sola pasada y terminar con codigo `0` salvo errores no recuperables.

## Requisitos De Tests

Implementar tests antes o junto al cambio. Minimo:

- Test de logging con `caplog`: al alcanzar `max_pages_per_run` sin cutoff se emite warning y no avanza checkpoint.
- Test con `FavoritesConfig(check_every_run=False)`: no se llama a `topic_fetcher`, no avanza `last_successful_favorites_check_at` y `RunResult` refleja skip/incompleto segun diseno.
- Test con favorito activo y `classifier=None`: no avanza `last_successful_favorites_check_at` y CLI/runtime no falla de forma no controlada.
- Test sin favoritos activos: favorites check completa sin fetches y puede avanzar checkpoint.
- Test de candidato `PENDING` existente: si vuelve a aparecer y hay clasificador, se reintenta y puede acabar `CLASSIFIED` o `DISCARDED`.
- Test de candidato `DISCARDED` existente: si vuelve a aparecer igual, no llama a `topic_fetcher` ni a IA.
- Test de candidato `CLASSIFIED`/favorito existente: discovery no reclasifica por listing; el seguimiento queda en favorites check.
- Test de primer run tras bootstrap: usa `bootstrap_completed_at` como referencia inicial o, si se decide otra politica, verifica explicitamente la semantica aprobada.
- Actualizar tests CLI para cualquier campo nuevo de `RunResult`.
- Ejecutar toda la suite sin red.

## Criterios De Aceptacion

- La suite completa pasa con `pytest`.
- Si `ruff` esta disponible, `ruff check .` pasa; si no esta disponible, documentar la limitacion en la verificacion ejecutada.
- No hay llamadas de red en tests.
- La implementacion no introduce migraciones ni nuevas dependencias runtime.
- Los checkpoints solo avanzan cuando la fase correspondiente ha finalizado de forma semanticamente correcta.
- `run` conserva una pasada finita, sin scheduler ni bucles persistentes.
- La tarea deja una nota breve de verificacion ejecutada en esta sub-SPEC antes de pasar a `REVIEW`.

## Verificacion Esperada

```bash
pytest tests/test_discovery_bootstrap.py tests/test_cli.py tests/test_favorites_service.py
pytest
ruff check .
```

Si `ruff` no esta instalado en el entorno, ejecutar:

```bash
python -m ruff check .
```

y documentar si tampoco esta disponible.

## Verificacion Ejecutada

- `pytest tests/test_discovery_bootstrap.py tests/test_cli.py tests/test_favorites_service.py` -> 39 passed.
- `pytest` -> 148 passed.
- `ruff check .` -> no disponible en PATH global.
- `python -m ruff check .` -> `No module named ruff` con el Python global.
- `.venv/bin/ruff check .` -> All checks passed.

## Commit Sugerido

```text
fix: harden hito 04 run contracts
```

## Rama Y PR

- Rama: `TASK-023_hito_04_sanity_remediation`
- PR: https://github.com/alvarofergil/forum_scraper/pull/20
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
