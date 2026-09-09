# TASK-025 - Correctivo Post HITO-06: Recuperacion De Pendientes Y Arranque Operativo

Estado: `DONE`
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Subsanar las desviaciones detectadas en el sanity check posterior a HITO-06 sin ampliar el alcance v1: evitar que candidatos pendientes queden olvidados tras fallos o tras `ai.enabled=false`, hacer resiliente el check de favoritos ante errores recuperables de clasificacion, y alinear configuracion/documentacion/estado de tareas con un arranque operativo claro.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`.
- Leer la fila `TASK-025` en `SPECs/forum_scraper_tasks.md`.
- Leer esta sub-SPEC completa.
- Leer `SPECs/skills/forum-task-agent/SKILL.md`.
- Leer, como minimo, estos fragmentos de la SPEC maestra:
  - seccion 13, `Discovery Incremental`;
  - seccion 15, `Favorites Check`;
  - seccion 17, `Clasificacion`;
  - seccion 19, `Eventos`;
  - seccion 20, `Notificaciones`;
  - seccion 22, `Configuracion`;
  - seccion 30, `Definition Of Done v1`.
- Leer codigo y tests afectados directamente:
  - `src/discovery/service.py`;
  - `src/favorites/service.py`;
  - `src/storage/repositories.py`;
  - `src/storage/operational.py`;
  - `src/app/cli.py`;
  - `src/app/config.py`;
  - `src/classification/base.py`;
  - `src/classification/fake.py`;
  - `config/config.example.yaml`;
  - `.env.example`;
  - `README.md`;
  - `tests/test_discovery_bootstrap.py`;
  - `tests/test_favorites_service.py`;
  - `tests/test_operational_cli.py`;
  - `tests/test_final_acceptance.py`;
  - `tests/test_config.py`.

## Observaciones Que Motivan La Tarea

1. Criticidad alta: `candidate_matches` conserva candidatos `PENDING`, pero no existe una fase explicita que procese el backlog pendiente independientemente del listing actual. Si `ai.enabled=false` durante bootstrap/run, o si falla la clasificacion de un candidato, el topic solo se reintenta si vuelve a aparecer en las paginas procesadas y dentro del cutoff. Un candidato puede envejecer fuera del discovery incremental y quedar pendiente indefinidamente, desviandose de la finalidad de recuperacion e idempotencia.
2. Criticidad media-alta: `FavoriteService.check_favorite()` no captura errores de clasificacion en favoritos modificados. Un fallo puntual del clasificador aborta la sesion de `favorites check`, puede impedir el procesamiento de favoritos posteriores y no deja un evento `ERROR` deduplicado ni una senal operativa clara.
3. Criticidad media: `config/config.example.yaml` trae `ai.enabled: true` con `ai.model: null`. `load_config()` acepta ese YAML, pero el cableado real de `OpenAIClassifier.from_config()` falla en runtime si se ejecuta `bootstrap`, `run` o `debug-listing` con esa configuracion sin editar el modelo. El README menciona `OPENAI_API_KEY`, pero no obliga explicitamente a fijar `ai.model` o desactivar IA.
4. Criticidad baja/documental: tras los commits de HITO-06, `TASK-018` y `TASK-019` siguen en `REVIEW` en `SPECs/forum_scraper_tasks.md` y en sus sub-SPECs. Si sus PRs ya han sido mergeados en `main`, deben pasar a `DONE`; si no, el README no deberia afirmar cierre v1 como estado final.
5. Criticidad baja: la cobertura final de DoD valida artefactos y documentacion, pero no cubre explicitamente los caminos de recuperacion de candidatos pendientes fuera del listing ni los fallos del clasificador durante favoritos.

## Alcance Incluido

- Anadir procesamiento explicito de candidatos `PENDING` antes o despues del discovery incremental, pero siempre dentro de `python -m app run`.
- Hacer que candidatos pendientes se reintenten aunque no aparezcan en la pagina actual del listing.
- Mantener candidatos en `PENDING` cuando no se puedan clasificar por error recuperable, ausencia de clasificador o `ai.enabled=false`.
- Marcar candidatos como `CLASSIFIED` o `DISCARDED` solo tras una clasificacion valida.
- Emitir eventos `ERROR` deduplicados y sanitizados para fallos recuperables relevantes de clasificacion/fetch cuando aporten observabilidad sin crear ruido infinito.
- Hacer resiliente `favorites check` ante errores de clasificacion: no abortar toda la pasada por un favorito, no modificar estado de disponibilidad/precio/hash como si el cambio hubiese sido clasificado y permitir reintento posterior.
- Ajustar CLI/resumen operativo si se anaden contadores de pendientes procesados/fallidos o checks incompletos.
- Alinear `config/config.example.yaml`, `.env.example` y README para que el primer uso deje claro uno de estos caminos:
  - IA desactivada por defecto en ejemplo; o
  - IA activada solo si el usuario configura `ai.model` y `OPENAI_API_KEY`.
- Actualizar tests unitarios y de aceptacion final para cubrir los nuevos contratos.
- Actualizar `SPECs/forum_scraper_tasks.md` y, si procede por evidencia real de merge, estados de `TASK-018`/`TASK-019`.

## Alcance Excluido

- No introducir scheduler interno, API web, frontend, colas externas, Redis, PostgreSQL ni servicios nuevos.
- No cambiar la fuente monitorizada ni ampliar scraping a otras secciones.
- No hacer requests reales a armas.es para implementar esta tarea.
- No cambiar el contrato de URLs canonicas ni la identidad primaria por `t`.
- No persistir texto completo de posts, HTML bruto, cookies, cabeceras sensibles, prompts completos ni respuestas completas del modelo.
- No convertir automaticamente candidatos pendientes en favoritos si `ai.enabled=false`.
- No inventar un sistema complejo de jobs; SQLite y consultas simples bastan para v1.
- No hacer commit, push, PR ni merge salvo peticion explicita de release.

## Guardrails Especificos

- Todo acceso externo debe seguir usando fakes en tests. OpenAI, SMTP, HTTP y reloj deben ser inyectables o sustituibles.
- Los errores guardados en `events.error_message` deben estar truncados y sanitizados; no deben incluir API keys, passwords, cookies, HTML bruto ni texto completo de posts.
- El procesamiento de pendientes debe tener limite configurable o constante razonable por pasada para evitar bucles largos. Si se anade configuracion, debe estar documentada y validada.
- Un candidato `PENDING` no debe bloquear el avance de otros candidatos pendientes ni de otros favoritos.
- No avanzar un checkpoint de una fase que haya quedado incompleta por fallo sistemico de clasificador/fetch si ese avance puede ocultar trabajo pendiente.
- No borrar candidatos, favoritos, historicos ni eventos existentes durante la subsanacion.
- Mantener idempotencia: repetir dos veces el mismo run sin cambios no debe duplicar favoritos, historicos ni eventos.
- No degradar la minimizacion de requests: solo descargar topics de candidatos pendientes o favoritos activos que realmente requieren analisis.

## Dependencias

- TASK-018.
- TASK-019.
- TASK-024.

## Archivos Permitidos O Esperados

- `src/discovery/service.py`
- `src/favorites/service.py`
- `src/storage/repositories.py`
- `src/storage/operational.py`
- `src/app/cli.py`
- `src/app/config.py`
- `src/classification/base.py`
- `src/classification/fake.py`
- `config/config.example.yaml`
- `.env.example`
- `README.md`
- `tests/test_discovery_bootstrap.py`
- `tests/test_favorites_service.py`
- `tests/test_operational_cli.py`
- `tests/test_final_acceptance.py`
- `tests/test_config.py`
- `SPECs/forum_scraper_tasks.md`
- `SPECs/task_specs/TASK-018_docker_raspberry.md`
- `SPECs/task_specs/TASK-019_final_acceptance.md`
- `SPECs/task_specs/TASK-025_hito_06_sanity_remediation.md`

## Requisitos Funcionales

1. `run` debe procesar candidatos `PENDING` almacenados aunque el topic no aparezca en los listings del run actual.
2. El procesamiento de pendientes debe usar `topics.external_topic_id`, `topics.canonical_url` y `candidate_matches.watch_item_id`; no debe reconstruir identidad desde URLs completas no canonicas.
3. Si el `watch_item_id` de un candidato pendiente ya no existe en la watchlist, el candidato debe permanecer `PENDING` y debe quedar trazabilidad operativa sin crear favoritos falsos.
4. Si `ai.enabled=false`, el backlog pendiente no debe abrir topics ni llamar al clasificador.
5. Si `ai.enabled=true` pero no hay clasificador disponible/configurable, el backlog debe permanecer pendiente y la pasada debe reportar incompletitud sin perder estado.
6. Si un candidato pendiente se clasifica como oferta relevante y supera umbral, debe crear o reutilizar favorito idempotentemente y marcar el candidato como `CLASSIFIED`.
7. Si un candidato pendiente se clasifica como no relevante, no oferta o bajo umbral, debe marcarse como `DISCARDED`.
8. Si falla fetch o clasificacion de un candidato pendiente, el candidato debe seguir `PENDING`, no debe crear favorito y debe poder reintentarse en el siguiente run.
9. Los fallos recuperables de clasificacion/fetch deben poder emitir `ERROR` con deduplication key estable por topic/watch/scope/tipo de error, evitando spam por cada run identico.
10. Si un favorito cambiado falla al clasificarse, `check_favorite` no debe propagar la excepcion fuera de la comprobacion del favorito.
11. Ante fallo de clasificacion de favorito, no debe actualizarse `last_content_hash`, `last_classified_at`, precio, disponibilidad ni historicos como si hubiese clasificacion valida.
12. Ante fallo de clasificacion de favorito, debe actualizarse solo lo estrictamente operativo que no oculte el reintento; si se actualiza `last_checked_at`, el cambio debe estar justificado por test.
13. Ante fallo de clasificacion de favorito, debe emitirse un `ERROR` deduplicado y sanitizado, y la comprobacion de los demas favoritos debe continuar.
14. El resultado de `run_once()` y la salida de CLI deben reflejar si hubo pendientes procesados/fallidos o si `favorites check` quedo incompleto por errores recuperables.
15. La configuracion de ejemplo debe ser coherente con el primer uso documentado. Preferencia recomendada: `ai.enabled: false` en `config/config.example.yaml` para que el ejemplo sea ejecutable sin coste ni secretos OpenAI; documentar como activar IA indicando `ai.enabled: true`, `ai.model` y `OPENAI_API_KEY`.
16. El README debe explicar de forma explicita que `OPENAI_API_KEY` por si sola no basta si `ai.model` queda `null`.
17. Si los PRs/commits de HITO-06 ya estan integrados en `main`, cambiar estados documentales de `TASK-018` y `TASK-019` a `DONE`. Si no estan integrados, documentar que siguen en `REVIEW` y no presentar v1 como cerrada definitivamente.

## Requisitos De Tests

- Test unitario: candidato `PENDING` creado con `ai.enabled=false` se procesa en un run posterior con IA activada aunque el listing actual venga vacio o ya este por debajo del cutoff.
- Test unitario: candidato `PENDING` positivo crea un favorito una sola vez y marca `CLASSIFIED`.
- Test unitario: candidato `PENDING` negativo marca `DISCARDED` y no crea favorito.
- Test unitario: fallo de fetch/clasificacion en candidato pendiente deja estado `PENDING`, no avanza a `CLASSIFIED`/`DISCARDED`, no crea favorito y permite reintento posterior.
- Test unitario: dos runs con el mismo fallo de candidato pendiente no duplican eventos `ERROR`.
- Test unitario: fallo de `classify_favorite_update()` en un favorito cambiado no propaga excepcion, no cambia hash/precio/status/historicos y emite un `ERROR` deduplicado.
- Test unitario: si hay dos favoritos activos y falla la clasificacion del primero, el segundo se comprueba igualmente.
- Test CLI: `run` imprime contadores/estado de pendientes y refleja incompletitud cuando corresponde.
- Test config/final acceptance: `config/config.example.yaml` y README quedan alineados con el modo IA elegido.
- Suite completa sin red:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
docker compose build
```

## Criterios De Aceptacion

- Ningun candidato `PENDING` recuperable queda dependiente de reaparecer en el listing para volver a intentarse.
- Un fallo temporal de OpenAI o del fetch de topic no pierde un candidato ni aborta la monitorizacion de todos los favoritos.
- La salida operativa permite distinguir run completo, run con backlog pendiente, y run con errores recuperables.
- No se duplican eventos ante runs repetidos con el mismo estado.
- La configuracion de ejemplo no conduce a un fallo runtime sorprendente tras copiarla siguiendo el README.
- La documentacion de estados HITO-06 no contradice la realidad del repo/PR.
- `pytest`, `ruff` y `docker compose build` pasan desde la raiz del repo.

## Verificacion Esperada

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
docker compose build
```

## Commit Sugerido

```text
fix: harden pending recovery after hito 06
```

## Rama Y PR

- Rama sugerida: `TASK-025_hito_06_sanity_remediation`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
