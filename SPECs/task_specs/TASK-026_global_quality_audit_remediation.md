# TASK-026 - Correctivo Global Post Auditoria De Calidad v1

Estado: `REVIEW`
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Subsanar las desviaciones detectadas en la auditoria adversarial global posterior al cierre de v1, sin ampliar el alcance funcional del producto: endurecer la integracion real con OpenAI Structured Outputs, hacer que las fases de `run` sean resilientes e independientes ante fallos recuperables, alinear favoritos con los contratos de monitorizacion de la SPEC, respetar configuracion custom de fuente, cerrar huecos de sanitizacion de errores y cubrir los edge-cases con tests deterministas sin red.

La tarea queda completada cuando:

- el schema enviado al API de OpenAI con `strict: true` sea compatible con el subconjunto soportado por Structured Outputs;
- `python -m app run` no pierda trabajo ni oculte errores recuperables cuando fallen listing, topic fetch, clasificacion, favoritos o notificaciones;
- favoritos activos se comprueben en lo que sea posible aunque la IA este desactivada o no disponible;
- la configuracion de fuente se use de forma consistente en listing y topic;
- ningun error persistido en `events.error_message` pueda contener secrets triviales, cabeceras sensibles, HTML bruto ni textos largos de terceros;
- la suite local cubra los casos nuevos y siga pasando completa.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila `TASK-026` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer fragmentos concretos de `SPECs/forum_scraper.md`:

- seccion 13, `Discovery Incremental`;
- seccion 15, `Favorites Check`;
- seccion 17, `Clasificacion`;
- seccion 19, `Eventos`;
- seccion 20, `Notificaciones`;
- seccion 22, `Configuracion`;
- seccion 30, `Definition Of Done v1`.

Leer sub-SPECs relacionadas solo si el contrato local no queda claro por esta tarea:

- `SPECs/task_specs/TASK-012_openai_classifier.md`;
- `SPECs/task_specs/TASK-013_favorites_hashing_history.md`;
- `SPECs/task_specs/TASK-014_events_idempotency.md`;
- `SPECs/task_specs/TASK-015_email_notifications.md`;
- `SPECs/task_specs/TASK-016_incremental_recovery.md`;
- `SPECs/task_specs/TASK-025_hito_06_sanity_remediation.md`.

Leer codigo y tests afectados directamente:

- `src/classification/base.py`;
- `src/classification/openai_classifier.py`;
- `src/discovery/service.py`;
- `src/favorites/service.py`;
- `src/events/service.py`;
- `src/notifications/email.py`;
- `src/sources/armas_es/topic_fetcher.py`;
- `src/sources/armas_es/topic_parser.py`;
- `src/app/config.py`;
- `src/app/cli.py`;
- `src/storage/orm.py`;
- `src/storage/repositories.py`;
- `src/storage/operational.py`;
- `tests/test_openai_classifier.py`;
- `tests/test_discovery_bootstrap.py`;
- `tests/test_favorites_service.py`;
- `tests/test_email_notifications.py`;
- `tests/test_config.py`;
- `tests/test_operational_cli.py`;
- `tests/test_final_acceptance.py`;
- fixtures bajo `tests/fixtures/armas_es/` solo si son necesarias para reproducir parsing.

Referencia externa permitida:

- Documentacion oficial de OpenAI Structured Outputs: <https://platform.openai.com/docs/guides/structured-outputs>
- Documentacion oficial de OpenAI Responses API: <https://platform.openai.com/docs/api-reference/responses/create>

No usar blogs, mirrors ni ejemplos no oficiales como fuente normativa para el schema.

## Observaciones Que Motivan La Tarea

1. Criticidad alta: `OpenAIClassifier` envia `ClassificationResult.model_json_schema()` directamente con `strict: true`. El schema generado por Pydantic contiene defaults/opcionalidad que no encajan de forma robusta con Structured Outputs estrictos: `price`, `currency` y `evidence` no aparecen como requeridos y no se fuerza `additionalProperties: false` en los objetos relevantes. Riesgo: el primer uso real del API puede fallar por schema invalido antes de clasificar.
2. Criticidad alta: `DiscoveryService._run_favorites_check()` retorna incompleto si `classifier is None`. Sin embargo, comprobar favoritos no es solo clasificar: debe hacer fetch de favoritos activos, calcular hash, detectar retirada/no disponible, distinguir errores y evitar IA si el contenido no cambia. Riesgo: al desactivar IA temporalmente se deja de monitorizar disponibilidad.
3. Criticidad alta: `FavoriteService.check_favorite()` captura `TopicFetchRecoverableError`, actualiza `last_checked_at` y devuelve `False` sin evento `ERROR` ni marca de error. Riesgo: errores transitorios quedan ocultos y el checkpoint de favoritos puede avanzar como si la pasada hubiese sido sana.
4. Criticidad alta: `_run_incremental_discovery()` no aisla excepciones de listing fetch/parser. Una excepcion en discovery puede abortar `run_once()` antes de backlog pendiente, favoritos y notificaciones. Riesgo: una caida puntual de listing bloquea monitorizacion de favoritos ya existentes.
5. Criticidad media: `ArmasEsTopicFetcher` respeta `base_url` y `forum_id` para construir URLs, pero llama al parser de topic sin pasar esa configuracion. Riesgo: fuentes custom o entornos de fixtures con otro foro/base parsean mal o generan canonicas erroneas.
6. Criticidad media: favoritos se deduplican por `topic_id` unico. `candidate_matches` permite `topic + watch_item`, pero `favorites` colapsa todos los matches del mismo topic en un unico favorito asociado al primer watch item. Riesgo: se pierde contexto cuando un anuncio encaja en varias busquedas.
7. Criticidad media: `load_config()` acepta `ai.enabled=true` con `ai.model=None`, pero el cableado real del clasificador falla despues en runtime. Riesgo: configuracion validada que acaba en traceback operativo.
8. Criticidad media: un candidato descubierto y fallido puede ser reprocesado en el mismo `run` por la fase de pendientes. Riesgo: doble fetch/topic y posible doble consumo externo ante una misma caida.
9. Criticidad media-baja: `_page_reached_cutoff((), cutoff)` devuelve `False`; una pagina de listing vacia con checkpoint puede provocar escaneo hasta `max_pages_per_run` en cada ejecucion sin avanzar checkpoint. Riesgo: desperdicio repetido y ruido operativo.
10. Criticidad media-baja: `notifications.email._safe_error_message()` solo trunca, no redacta secrets. Riesgo: excepciones SMTP con password/token/cookie/API key pueden persistirse en SQLite.
11. Criticidad baja: `status` no muestra de forma suficientemente clara fuente activa y metricas de ultima ejecucion segun la promesa de la SPEC. Riesgo: menor observabilidad operativa.

## Alcance Incluido

- Cambiar el schema de OpenAI para que sea compatible con Structured Outputs estrictos.
- Anadir tests unitarios de compatibilidad del schema sin llamar a OpenAI.
- Mantener la interfaz publica de `Classifier` y `ClassificationResult` salvo que un ajuste minimo sea imprescindible para generar el schema.
- Hacer que el check de favoritos ejecute la parte no-IA aunque `classifier is None`.
- Hacer que favoritos sin cambios no requieran clasificador.
- Hacer que favoritos no disponibles, retirados, 404 o temporalmente inaccesibles se gestionen igual con IA activada o desactivada.
- Emitir eventos `ERROR` deduplicados y sanitizados para errores recuperables relevantes de fetch/clasificacion.
- Hacer que fallos de listing fetch/parser no aborten el resto de fases de `run_once()`.
- Reflejar en el resultado de `run_once()` y en CLI si discovery o favoritos han quedado incompletos.
- Pasar `base_url` y `forum_id` al parser de topic cuando el fetcher use configuracion custom.
- Decidir e implementar una solucion explicita para topic con varios watch items:
  - opcion preferente: permitir un favorito por par `topic_id + watch_item_id`;
  - opcion alternativa aceptable solo si se documenta en codigo/tests: mantener favorito unico por topic pero preservar trazabilidad de todos los matches y no marcar como clasificado un watch item cuyo contexto se ha perdido.
- Validar la configuracion AI en `load_config()` para evitar `enabled=true` con `model=None`.
- Evitar que candidatos creados durante discovery se reintenten automaticamente en la fase de pendientes del mismo run.
- Cortar de forma razonable cuando una pagina de listing viene vacia y hay checkpoint, o tratarlo como parser/fetch incompleto con evento operativo.
- Unificar sanitizacion de errores entre discovery, favorites y email notification.
- Mejorar `status` solo en la medida necesaria para cumplir la SPEC v1, sin crear dashboards ni nuevos comandos.
- Actualizar README/config docs si cambia el contrato de AI o status.
- Actualizar tests existentes y crear tests nuevos con fakes.

## Alcance Excluido

- No introducir scheduler interno, colas, Redis, PostgreSQL, API web, frontend ni workers.
- No cambiar la fuente principal del proyecto ni anadir soporte multi-sitio.
- No hacer scraping real a armas.es durante tests.
- No hacer llamadas reales a OpenAI ni SMTP en tests.
- No capturar nuevas fixtures reales salvo autorizacion explicita del usuario.
- No persistir HTML bruto, texto completo de posts, prompts completos, respuestas completas del modelo, cookies, cabeceras sensibles ni credenciales.
- No cambiar la identidad canonica de topic basada en `t`.
- No reescribir toda la arquitectura de discovery/favorites; hacer cambios quirurgicos en los contratos afectados.
- No anadir migraciones destructivas ni borrar datos existentes.
- No modificar historicos existentes salvo que una migracion sea imprescindible para resolver favoritos multi-watch-item.
- No abrir PRs adicionales ni mezclar tareas fuera de TASK-026.

## Guardrails Especificos

- Todos los tests nuevos deben ser deterministas, sin red y con fakes/stubs.
- Si se toca persistencia, la migracion debe ser compatible hacia adelante y no destructiva.
- Si se modifica una constraint unica en favoritos, preservar datos existentes:
  - no borrar favoritos;
  - no perder historicos;
  - definir comportamiento para datos legacy con un favorito por topic.
- Los errores persistidos en `events.error_message` deben pasar por una unica funcion de sanitizacion o por funciones equivalentes cubiertas por tests compartidos.
- La sanitizacion debe cubrir, como minimo:
  - nombres de variables/cabeceras: `OPENAI_API_KEY`, `Authorization`, `Cookie`, `password`, `token`, `api_key`, `secret`;
  - variantes de mayusculas/minusculas;
  - patrones `key=value`, `key: value` y bearer/basic tokens;
  - fragmentos HTML obvios, que deben eliminarse o reemplazarse por texto corto.
- Los eventos `ERROR` deben tener deduplication key estable y suficientemente especifica para no mezclar errores de topics/favoritos distintos.
- Un fallo recuperable de una fase no debe impedir fases independientes:
  - fallo de listing no debe impedir pendientes ya existentes, favoritos ni notificaciones;
  - fallo de un favorito no debe impedir revisar los demas;
  - fallo de una notificacion no debe impedir cerrar el resto del run.
- No avanzar checkpoints de forma que oculten trabajo no realizado.
- No duplicar requests a topic dentro del mismo run para el mismo candidato/watch item cuando el primer intento acaba de fallar.
- Mantener idempotencia: ejecutar dos veces con el mismo estado no debe duplicar favoritos, historicos ni eventos.
- Mantener minimizacion de requests: no descargar topics si `ai.enabled=false` y no hay trabajo no-IA necesario; no clasificar favoritos cuyo hash no haya cambiado.
- Si aparece una decision que afecta coste, privacidad, legalidad, migracion de datos existente o contrato de producto, parar y preguntar.

## Dependencias

- TASK-012.
- TASK-013.
- TASK-014.
- TASK-015.
- TASK-016.
- TASK-017.
- TASK-025.

## Archivos Permitidos O Esperados

- `src/classification/base.py`
- `src/classification/openai_classifier.py`
- `src/discovery/service.py`
- `src/favorites/service.py`
- `src/events/service.py`
- `src/notifications/email.py`
- `src/sources/armas_es/topic_fetcher.py`
- `src/sources/armas_es/topic_parser.py`
- `src/app/config.py`
- `src/app/cli.py`
- `src/storage/orm.py`
- `src/storage/repositories.py`
- `src/storage/operational.py`
- `alembic/versions/*.py` solo si se cambia schema de BD
- `README.md`
- `config/config.example.yaml`
- `.env.example`
- `tests/test_openai_classifier.py`
- `tests/test_discovery_bootstrap.py`
- `tests/test_favorites_service.py`
- `tests/test_email_notifications.py`
- `tests/test_config.py`
- `tests/test_operational_cli.py`
- `tests/test_final_acceptance.py`
- `tests/fixtures/armas_es/*` solo si hace falta fixture local sintetica, no captura real
- `SPECs/forum_scraper_tasks.md`
- esta sub-SPEC si durante la implementacion se descubre una decision relevante

Tocar otros archivos requiere actualizar esta seccion y justificarlo en el PR.

## Requisitos Funcionales

### A. OpenAI Structured Outputs

1. `OpenAIClassifier` debe enviar un JSON Schema estable y compatible con Structured Outputs estrictos.
2. El schema debe estar definido de forma explicita o generado por una funcion controlada; no debe depender ciegamente de `ClassificationResult.model_json_schema()` si Pydantic emite construcciones incompatibles.
3. Todos los campos esperados por `ClassificationResult` deben estar presentes como propiedades requeridas en el schema enviado a OpenAI.
4. Campos conceptualmente opcionales deben modelarse como requeridos pero anulables cuando aplique:
   - `price`: number o null;
   - `currency`: string o null;
   - `evidence`: array de strings, posiblemente vacio.
5. Los objetos del schema deben declarar `additionalProperties: false`.
6. El schema no debe permitir campos inesperados del modelo.
7. La validacion local con Pydantic debe mantenerse despues de parsear `response.output_text`.
8. Si OpenAI devuelve JSON invalido o no compatible con `ClassificationResult`, el error debe seguir siendo recuperable, sanitizado y no debe persistir la respuesta completa.
9. Tests deben inspeccionar el schema final y verificar:
   - `strict` se mantiene en `True`;
   - `required` contiene todos los campos del resultado;
   - `additionalProperties` existe y es `False` en objetos;
   - opcionales usan nullability en vez de omitirse;
   - no hay llamada real a red.

### B. Favorites Check Sin Dependencia Total De IA

10. `DiscoveryService._run_favorites_check()` no debe retornar antes de consultar favoritos activos solo porque `classifier is None`.
11. Para cada favorito activo, el sistema debe intentar fetch del topic si existe `topic_fetcher`.
12. Si el topic no ha cambiado respecto a `last_content_hash`, no debe llamarse al clasificador.
13. Si el topic esta retirado/no disponible/not found, debe actualizarse disponibilidad conforme al contrato existente aunque no haya clasificador.
14. Si el topic cambio y no hay clasificador, el favorito debe quedar sin reclasificar, con senal operativa de check incompleto, pero sin perder el hash anterior ni marcar falsamente como actualizado.
15. El resumen de `run_once()` debe distinguir:
   - favoritos comprobados;
   - favoritos sin cambios;
   - favoritos cambiados pero no reclasificados por falta de IA;
   - favoritos con error recuperable.
16. La salida CLI debe mostrar la incompletitud de favoritos de forma concisa.

### C. Errores Recuperables En Favoritos

17. `TopicFetchRecoverableError` durante favoritos debe producir un `ERROR` deduplicado y sanitizado.
18. Ese error debe marcar que la fase de favoritos no fue completamente exitosa.
19. No debe avanzar `last_successful_favorites_check_at` si hubo errores recuperables de fetch o clasificacion en favoritos.
20. El fallo de un favorito no debe abortar la comprobacion de favoritos posteriores.
21. En error recuperable de fetch:
   - no cambiar `last_content_hash`;
   - no cambiar precio;
   - no crear historicos de precio/status;
   - no marcar como retirado;
   - permitir reintento posterior.
22. En error recuperable de clasificacion:
   - no actualizar `last_classified_at`;
   - no actualizar `last_content_hash` como si estuviera procesado;
   - no cambiar precio/status;
   - no crear historicos;
   - emitir evento `ERROR`;
   - continuar con el siguiente favorito.

### D. Aislamiento De Fases En `run_once`

23. `run_once()` debe ejecutar, siempre que existan dependencias minimas:
   - discovery incremental;
   - backlog de candidatos pendientes;
   - check de favoritos;
   - notificaciones pendientes.
24. Un fallo recuperable de listing fetch/parser debe marcar discovery como incompleto, pero no debe impedir backlog, favoritos ni notificaciones.
25. El resultado operativo debe reflejar que discovery fallo o quedo incompleto.
26. Si listing falla antes de obtener paginas validas, no avanzar `last_discovery_at`.
27. Si discovery alcanza `max_pages_per_run` sin cutoff, mantener el comportamiento de warning/no avance de checkpoint ya definido.
28. Si una pagina parseada viene vacia con checkpoint activo, escoger uno de estos comportamientos y cubrirlo con test:
   - tratar pagina vacia como fin/cutoff razonable y detener avance de paginas;
   - o tratar pagina vacia como senal incompleta con evento/error operativo.
29. La opcion elegida debe evitar escanear siempre hasta `max_pages_per_run` en runs repetidos.

### E. Topic Fetcher Con Configuracion Custom

30. `ArmasEsTopicFetcher` debe pasar `base_url` y `forum_id` al parser de topic.
31. La signatura de `TopicParser` debe aceptar esos parametros o el fetcher debe adaptar el parser mediante wrapper.
32. Los tests deben cubrir una configuracion no-default:
   - `base_url="https://example.test"`;
   - `forum_id` distinto de `96`;
   - HTML con enlaces `viewtopic.php?f=<forum_id>&t=<id>`.
33. Listing parser y topic parser deben quedar consistentes respecto a configuracion custom.

### F. Favoritos Y Multiples Watch Items

34. Definir comportamiento esperado cuando un mismo topic coincide con varios watch items.
35. Preferencia de producto para v1: un favorito debe representar el par `topic_id + watch_item_id`, porque el match pertenece a una busqueda concreta.
36. Si se adopta la preferencia:
   - cambiar constraint unica de `favorites.topic_id` a `favorites.topic_id + favorites.watch_item_id`;
   - crear migracion Alembic no destructiva;
   - adaptar `create_from_classification()` para buscar por par;
   - preservar idempotencia por par;
   - mantener historicos ligados al favorito correcto;
   - adaptar notificaciones para que el contexto del watch item sea el correcto.
37. Si se rechaza la preferencia por coste de migracion, debe documentarse explicitamente:
   - favorito unico por topic es decision intencional;
   - candidatos de watch items adicionales no deben marcarse `CLASSIFIED` como si hubiesen generado favorito propio;
   - la UI/CLI/eventos deben dejar trazabilidad de matches secundarios.
38. Tests obligatorios:
   - mismo topic coincide con dos watch items;
   - se crean dos favoritos o se preserva trazabilidad segun decision;
   - reejecutar run no duplica favoritos/eventos.

### G. Configuracion AI

39. `load_config()` debe rechazar `ai.enabled=true` con `model=None` mediante `ConfigError`.
40. El mensaje de error debe ser claro y no mencionar secrets.
41. `ai.enabled=false` con `model=None` debe seguir siendo valido.
42. `config/config.example.yaml` debe continuar siendo ejecutable sin OpenAI por defecto, salvo decision explicita contraria.
43. README debe explicar:
   - para usar OpenAI se necesita `ai.enabled: true`;
   - `ai.model` no puede ser `null`;
   - `OPENAI_API_KEY` debe existir en entorno;
   - tests no hacen llamadas reales a OpenAI.
44. CLI debe capturar `ConfigError` en comandos que construyan servicios y mostrar salida operativa limpia.

### H. Evitar Reintento Doble En El Mismo Run

45. Un candidato creado durante discovery y fallido al clasificar/fetchear no debe ser reintentado por la fase de pendientes del mismo run.
46. Opciones aceptables:
   - pasar a `_process_pending_candidates()` un conjunto de candidate ids creados/intentos en este run para excluirlos;
   - o procesar backlog pendiente antes de discovery y limitarlo a candidatos preexistentes;
   - o registrar `last_attempted_at` y filtrar intentos de la misma ejecucion.
47. La solucion no debe impedir reintento en el siguiente `run`.
48. Test obligatorio: topic fetch/classifier fake falla durante discovery; el contador de llamadas confirma un solo intento en ese run y un nuevo intento en el run siguiente.

### I. Sanitizacion De Errores

49. Crear o reutilizar una funcion comun de sanitizacion para errores persistidos.
50. Aplicarla, como minimo, en:
   - discovery;
   - favorites;
   - notifications/email.
51. La funcion debe:
   - aceptar cualquier `BaseException` o string;
   - convertir a texto corto;
   - eliminar saltos/espaciado excesivo;
   - truncar a longitud razonable existente o documentada;
   - redactar tokens/secrets/cookies/passwords;
   - eliminar HTML bruto o reemplazarlo por marcador corto;
   - no lanzar excepciones.
52. Tests obligatorios:
   - error SMTP con `password=abc`;
   - error SMTP con `Authorization: Bearer secret`;
   - error OpenAI con `OPENAI_API_KEY=sk-...`;
   - error HTTP con fragmento `<html>...`;
   - todos persisten mensaje sanitizado, no secreto.

### J. CLI Status

53. `python -m app status` debe mostrar informacion operativa suficiente para cumplir v1:
   - fuente activa cuando haya config disponible;
   - conteos de favoritos activos;
   - eventos pendientes/notificables/no notificables;
   - ultimo discovery/check favoritos/notification run conocido;
   - senal de backlog pendiente si existe.
54. No crear nuevo comando si `status` puede cubrirlo.
55. Tests de CLI deben verificar texto estable sin acoplarse a formato decorativo fragil.

## Requisitos De Tests

Anadir o ajustar tests focalizados. Como minimo:

1. `test_openai_classifier_uses_strict_supported_schema`
   - fake client captura payload;
   - assert `strict is True`;
   - assert todos los campos requeridos;
   - assert objetos con `additionalProperties: False`;
   - assert opcionales como nullable.
2. `test_openai_classifier_rejects_invalid_output_without_leaking_raw_response`
   - respuesta JSON invalida o fuera de schema;
   - error recuperable;
   - mensaje sin body completo.
3. `test_favorites_check_runs_without_classifier_for_unchanged_topic`
   - favorito activo;
   - topic fetch devuelve mismo hash;
   - classifier `None`;
   - check completo para ese favorito, cero llamadas IA.
4. `test_favorites_check_without_classifier_marks_changed_topic_incomplete`
   - favorito activo;
   - topic fetch devuelve hash distinto;
   - classifier `None`;
   - no cambia hash/precio/status;
   - resultado incompleto.
5. `test_favorite_recoverable_fetch_error_emits_error_and_does_not_advance_success_checkpoint`
   - topic fetch lanza `TopicFetchRecoverableError`;
   - evento `ERROR` deduplicado;
   - `last_successful_favorites_check_at` no avanza.
6. `test_favorite_classification_error_does_not_abort_other_favorites`
   - primer favorito falla clasificacion;
   - segundo se procesa;
   - primer favorito no muta datos de clasificacion;
   - evento `ERROR`.
7. `test_run_listing_failure_still_processes_pending_favorites_and_notifications`
   - listing client lanza;
   - candidato pendiente preexistente se procesa si corresponde;
   - favoritos se comprueban;
   - notificaciones pendientes se intentan;
   - run reporta discovery incompleto.
8. `test_topic_fetcher_passes_custom_base_url_and_forum_id_to_parser`
   - parser fake captura parametros;
   - fetcher usa config custom.
9. `test_same_topic_matching_two_watch_items_preserves_watch_context`
   - cubrir decision implementada en seccion F.
10. `test_ai_enabled_requires_model`
   - YAML con `ai.enabled: true` y `model: null`;
   - `load_config()` lanza `ConfigError`;
   - YAML con `enabled: false` y `model: null` sigue valido.
11. `test_newly_failed_candidate_is_not_retried_twice_in_same_run`
   - fake topic/classifier cuenta llamadas.
12. `test_empty_listing_with_checkpoint_does_not_spin_to_max_pages`
   - listing parser devuelve pagina vacia;
   - assert paginas consultadas minimas o estado incompleto explicito.
13. `test_email_error_message_is_sanitized_before_persisting`
   - SMTP fake lanza mensaje con secret;
   - DB event no contiene secret.
14. `test_status_reports_operational_summary`
   - salida contiene fuente/backlog/eventos/ultimos checks de forma estable.
15. `test_final_acceptance_includes_task_026_contracts`
   - si existe test final de artefactos/documentacion, anadir checks de esta tarea.

La suite completa debe seguir sin red. No marcar la tarea como completada con tests saltados salvo causa externa documentada.

## Criterios De Aceptacion

- OpenAI Structured Outputs no depende de un schema Pydantic incompatible con `strict: true`.
- Tests validan la forma del schema sin llamar a OpenAI.
- Favoritos activos se siguen consultando cuando IA esta desactivada si hay trabajo no-IA que realizar.
- Topic sin cambios no consume IA.
- Topic cambiado sin IA queda pendiente/incompleto sin corromper hash, precio, disponibilidad ni historicos.
- Errores recuperables de fetch/clasificacion de favoritos generan evento `ERROR` deduplicado y no avanzan checkpoint de exito.
- Fallo de listing no impide backlog, favoritos ni notificaciones.
- Topic parser respeta `base_url` y `forum_id` configurados.
- El comportamiento multi-watch-item queda implementado y probado.
- Configuracion AI invalida falla temprano con `ConfigError` claro.
- No hay reintento doble del mismo candidato fallido dentro del mismo run.
- Paginas vacias con checkpoint no provocan bucles hasta `max_pages_per_run` en cada ejecucion.
- Errores SMTP/OpenAI/HTTP persistidos estan sanitizados.
- `status` cubre el resumen operativo minimo prometido por v1.
- `README.md`, `config/config.example.yaml` y `.env.example` no se contradicen.
- `pytest`, `ruff` y, si Docker esta disponible, `docker compose build` pasan desde la raiz del repo.

## Verificacion Esperada

Ejecutar desde la raiz del repo:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
docker compose build
```

Si Docker no esta disponible en el entorno, documentar el motivo exacto en el PR y ejecutar al menos:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Secuencia Recomendada De Implementacion

1. Crear rama desde `main` actualizado: `TASK-026_global_quality_audit_remediation`.
2. Leer esta sub-SPEC completa y abrir los archivos afectados.
3. Escribir primero tests de OpenAI schema y config AI; hacerlos fallar.
4. Implementar schema estricto compatible y validacion de config.
5. Escribir tests de favorites sin IA y errores recuperables; hacerlos fallar.
6. Ajustar `FavoriteService` y `DiscoveryService._run_favorites_check`.
7. Escribir test de aislamiento de fases de `run_once`; hacerlos fallar.
8. Ajustar `_run_incremental_discovery`/`run_once` para reportar incompletitud sin abortar fases independientes.
9. Escribir test de topic fetcher con config custom; corregir parser/fetcher.
10. Resolver multi-watch-item con migracion o decision documentada y tests.
11. Anadir sanitizacion comun y aplicar a email/discovery/favorites.
12. Ajustar CLI `status` y README/config docs.
13. Ejecutar tests focalizados.
14. Ejecutar verificacion completa.
15. Revisar `git diff` para confirmar que no hay cambios fuera de alcance.
16. Commit, push y PR.
17. Dejar `TASK-026` en `REVIEW` mientras el PR este abierto; pasar a `DONE` solo tras merge.

## Commit Sugerido

```text
fix: harden global v1 runtime contracts
```

## Rama Y PR

- Rama sugerida: `TASK-026_global_quality_audit_remediation`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
