# SPEC Maestra - Forum Scraper Monitor v1

Estado: `APPROVED_FOR_PLANNING`  
Documento maestro de tareas: [forum_scraper_tasks.md](forum_scraper_tasks.md)  
Directorio desplegable de la aplicacion: [`../`](../)

## 0. Protocolo De Arranque Para Agentes

En una conversacion nueva, el agente debe empezar leyendo [AGENT_START.md](AGENT_START.md).

Despues debe aplicar lectura progresiva antes de actuar:

1. identificar la tarea activa o la tarea solicitada por el usuario;
2. consultar el documento maestro de tareas [forum_scraper_tasks.md](forum_scraper_tasks.md) como indice operativo, leyendo solo la fila de la tarea activa, dependencias directas y notas aplicables;
3. leer completa la sub-SPEC correspondiente bajo `SPECs/task_specs/`;
4. leer [forum-task-agent](skills/forum-task-agent/SKILL.md) como checklist unico;
5. leer fragmentos concretos de esta SPEC maestra cuando la tarea, sub-SPEC, skill o duda actual lo requiera;
6. leer esta SPEC completa solo cuando haya impacto global, contradiccion entre artefactos, duda de alcance v1, arquitectura, acceso externo, privacidad, seguridad, coste, legalidad o comportamiento funcional transversal;
7. si falta informacion para decidir requisitos, alcance, arquitectura, acceso externo, privacidad, seguridad, coste o comportamiento funcional, preguntar al usuario antes de inventar o implementar;
8. no modificar codigo, tareas ni estados sin haber leido el contexto minimo aplicable.

Este protocolo es obligatorio para cualquier agente IA que trabaje en el proyecto. La lectura completa de documentos deja de ser el comportamiento por defecto; el comportamiento por defecto es cargar el contexto minimo verificable.

## 1. Proposito

Construir una aplicacion autonoma en Python que monitorice el foro publico de compraventa:

```text
https://www.armas.es/foros/viewforum.php?f=96
```

La aplicacion detectara temas relacionados con elementos configurados por el usuario en una watchlist, los convertira en favoritos cuando proceda, seguira su evolucion aunque desaparezcan de las primeras paginas del foro y notificara eventos relevantes por email.

La version v1 no incluye interfaz web.

## 2. Principios Rectores

1. La raiz del repo contiene todo el codigo, configuracion de runtime, tests y artefactos necesarios para desplegar la aplicacion.
2. `SPECs/` vive dentro del repo y contiene la direccion del proyecto para agentes IA: esta SPEC, el documento maestro de tareas y las SPECs por tarea.
3. No debe haber marcas, modelos ni categorias de interes hardcodeadas en Python.
4. Todo criterio de interes procede de `config/config.yaml`.
5. SQLite es la fuente unica de estado operativo.
6. No se descarga ni analiza en profundidad un topic que claramente no sea candidato.
7. Los favoritos se monitorizan directamente por URL canonica, de forma independiente del discovery.
8. No se implementan mecanismos de evasion: sin CAPTCHA bypass, proxy rotation, fingerprint evasion, account automation ni rate-limit bypass.
9. La carga contra armas.es debe ser extremadamente baja, secuencial y respetuosa.
10. La aplicacion debe poder moverse de un PC a una Raspberry Pi copiando solamente `config/`, `data/`, `backups/` si existen y `.env`.

## 3. Modelo De Desarrollo Para Agentes IA

Este proyecto sera desarrollado por agentes IA. Por tanto, la documentacion debe ser tratada como contrato operativo.

### 3.1 Checklist Unico Del Proyecto

El proyecto usa un unico agente por defecto. Las funciones de PM, Arquitectura, Desarrollo, QA y Release son fases internas de [forum-task-agent](skills/forum-task-agent/SKILL.md), no subagentes ni handoffs escritos.

Antes de comenzar una tarea, el agente debe leer:

1. [AGENT_START.md](AGENT_START.md);
2. la fila de la tarea activa en el documento maestro de tareas;
3. la sub-SPEC de la tarea;
4. [forum-task-agent](skills/forum-task-agent/SKILL.md);
5. los fragmentos de esta SPEC maestra necesarios para resolver la tarea o duda actual.

Solo se usan varios agentes si el usuario lo pide de forma explicita o si hace falta una revision independiente real. Si aparece una duda que afecta requisitos, arquitectura, privacidad, coste, acceso externo, legalidad, seguridad o alcance, se pregunta al usuario antes de implementar o redactar decisiones nuevas.

### 3.2 Spec Driven Development

Cada tarea implementable debe tener su propia SPEC en Markdown bajo:

```text
SPECs/task_specs/
```

Cada sub-SPEC debe incluir:

- objetivo;
- contexto minimo para agentes;
- alcance incluido;
- alcance excluido;
- guardrails especificos de la tarea;
- dependencias;
- archivos permitidos o esperados;
- requisitos funcionales;
- requisitos de tests;
- criterios de aceptacion;
- mensaje de commit sugerido, rama sugerida y PR esperado cuando se vaya a hacer release.

Los guardrails son obligatorios y deben redactarse con el mismo nivel de cuidado que los requisitos positivos. Cada sub-SPEC debe dejar claro:

- que debe hacer el agente;
- que no debe hacer bajo ningun concepto dentro de esa tarea;
- que decisiones requieren preguntar antes de avanzar;
- que archivos, servicios, datos externos, credenciales, red, commits o cambios de estado quedan fuera de limites;
- que comportamientos podrian parecer utiles pero pertenecen a otra tarea o a otra version.

Si una tarea no puede definir guardrails concretos, debe considerarse insuficientemente definida y quedar en `BLOCKED` o pendiente de revision antes de implementarse.

El documento maestro [forum_scraper_tasks.md](forum_scraper_tasks.md) enlaza todas las sub-SPECs y es la fuente de verdad del estado de trabajo.

### 3.3 GitHub Flow Obligatorio Por Tarea

Cada tarea con cambios en el repositorio debe poder entregarse con una rama y PR propios. El flujo de release se ejecuta cuando el usuario lo pide o cuando la tarea activa lo exige expresamente.

Antes de empezar a implementar:

1. comprobar estado del repo y cambios ajenos;
2. cambiar a `main`;
3. ejecutar:

```bash
git pull --ff-only origin main
```

4. crear una rama local desde `main` con nombre descriptivo:

```text
TASK-XXX_slug_descriptivo
```

Ejemplo:

```text
TASK-002_config_and_domain_models
```

Al terminar una tarea:

1. todos los tests y checks requeridos deben pasar;
2. anotar la verificacion ejecutada;
3. hacer commit, push, PR y `REVIEW` solo cuando se pida release;
4. describir en el PR objetivo, cambios incluidos, guardrails respetados, verificacion ejecutada y limitaciones conocidas.

`DONE` queda reservado para tareas cuyo PR ya ha sido mergeado en `main`.

No se debe usar `develop` como rama normal de integracion de tareas. Cada tarea viaja en su propia rama.

### 3.4 TDD Obligatorio

Cada tarea se implementa con metodologia TDD:

1. leer [AGENT_START.md](AGENT_START.md);
2. localizar la tarea en el documento maestro;
3. leer la sub-SPEC de la tarea;
4. leer [forum-task-agent](skills/forum-task-agent/SKILL.md);
5. leer fragmentos de esta SPEC solo cuando falte una regla global concreta;
6. reclamar la tarea en el documento maestro;
7. escribir o actualizar tests que fallen por la funcionalidad pendiente;
8. implementar el cambio minimo suficiente;
9. ejecutar tests focalizados durante el ciclo y todos los tests unitarios antes de entregar;
10. corregir hasta que pasen;
11. actualizar estado y notas de la tarea;
12. hacer commit, push y PR solo cuando se pida release.

No se debe hacer commit si falla algun test unitario.

### 3.5 Commits

Cuando empiece la implementacion se inicializara Git dentro del repositorio si todavia no existe.

Reglas:

- un commit por tarea terminada;
- no mezclar tareas no relacionadas;
- no commitear secrets;
- no commitear HTML sin sanitizar;
- no commitear cambios de estado falsos;
- el commit debe ocurrir despues de tests verdes;
- no hacer push directo a `main`;
- el PR de cada tarea debe apuntar a `main`.

## 4. Fuente Monitorizada

Fuente inicial:

```yaml
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
```

Todos los detalles especificos de armas.es deben quedar encapsulados en:

```text
src/sources/armas_es/
```

El resto de la aplicacion no debe conocer HTML, selectores CSS ni convenciones de URL de armas.es.

## 5. Reglas Verificadas De armas.es

El foro esta basado en phpBB.

El listado tiene bloques diferenciados:

```text
Anuncios
Temas
```

Discovery procesa exclusivamente el bloque `Temas` y excluye `Anuncios` por estructura DOM, no por texto del titulo.

La paginacion usa `start`:

```text
Pagina 1: viewforum.php?f=96
Pagina 2: viewforum.php?f=96&start=18
Pagina 3: viewforum.php?f=96&start=36
```

El parser debe preferir:

1. enlace `Siguiente`;
2. parametros de paginacion presentes en el HTML;
3. fallback configurable/testeable de 18 temas por pagina.

Las URLs deben eliminar parametros efimeros como `sid`.

## 6. Identidad Y URLs Canonicas

El identificador primario externo de un topic es el parametro phpBB:

```text
t
```

La URL canonica almacenada sera:

```text
https://www.armas.es/foros/viewtopic.php?f=96&t=<TOPIC_ID>
```

Nunca usar como identidad:

- URL completa recibida;
- `sid`;
- `start`;
- `p`;
- anchor;
- posicion en la pagina;
- titulo;
- hash del HTML.

## 7. Informacion De Listing

Para cada topic ordinario de `viewforum`, intentar extraer:

- `external_topic_id`;
- `canonical_url`;
- `title`;
- `snippet`;
- `author`;
- `created_at`;
- `last_activity_at`;
- `last_post_author`;
- `reply_count`;
- `view_count`;

Para cada pagina de listing, intentar extraer:

- `next_page_url`.

`next_page_url` debe permanecer dentro del host, path `/foros/viewforum.php` y
foro configurados, sin parametros efimeros o especificos de fila como `sid`,
`p` o anchors.

Debe distinguirse `created_at` de `last_activity_at`, porque el foro se ordena por actividad reciente.

El parser debe obtener autor y fecha desde estructura HTML siempre que sea posible. El texto visible solo sera fallback.

## 8. Informacion De Topic

Cuando un candidato o favorito requiera analisis, se descargara:

```text
https://www.armas.es/foros/viewtopic.php?f=96&t=<TOPIC_ID>
```

El parser debe extraer:

- `topic_title`;
- `external_topic_id`;
- `original_author`;
- `total_posts`;
- `current_page`;
- `total_pages`;
- posts visibles.

Para cada post visible:

- `external_post_id`, si existe;
- `author`;
- `posted_at`;
- `text`;
- `sequence_number`.

Los topics pueden tener varias paginas. No asumir que todo el topic esta en una unica pagina.

## 9. Watchlist

La watchlist vive en YAML:

```yaml
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
    aliases:
      - "MarcaA ModeloX"
      - "Modelo-X"
```

En v1 el matching inicial es sencillo:

- buscar marca y modelo;
- incluir aliases como señales adicionales;
- favorecer recall sobre precision;
- enviar candidatos dudosos a clasificacion cuando la IA este activa.

No debe ser necesario modificar Python para agregar elementos.

## 10. Normalizacion

Antes de comparar:

- Unicode normalize;
- lowercase;
- trim;
- collapse spaces;
- normalize guiones;
- normalize puntuacion.

Mantener texto raw para clasificacion y texto normalizado para matching/hashing.

## 11. Bootstrap

Comando:

```bash
python -m app bootstrap
```

Config:

```yaml
bootstrap:
  pages: 10
```

El bootstrap recorre las primeras 10 paginas del bloque `Temas`.

Flujo:

```text
10 paginas de listing
-> topic rows ordinarios
-> matcher determinista barato
-> solo candidatos
-> GET viewtopic
-> clasificacion
-> favorito o descartado
```

No abrir automaticamente todos los topics.

Guardar `bootstrap_completed_at` en `app_state`.

Si ya existe bootstrap, `bootstrap` debe rechazar la ejecucion salvo:

```bash
python -m app bootstrap --force
```

`--force` no borra favoritos ni historicos existentes.

## 12. Run Incremental

Comando:

```bash
python -m app run
```

Cada llamada ejecuta una pasada completa y termina.

Fases obligatorias:

```text
RUN
|-- DISCOVERY
|-- FAVORITES CHECK
```

No debe existir scheduler obligatorio dentro de la logica de negocio.

El host, cron, systemd timer o Docker ejecutaran periodicamente el comando.

## 13. Discovery Incremental

Guardar:

```text
last_successful_discovery_at
```

Config:

```yaml
discovery:
  overlap_minutes: 30
  max_pages_per_run: 50
```

Cutoff:

```text
last_successful_discovery_at - overlap_minutes
```

El discovery navega paginas ordenadas por actividad hasta encontrar topics con:

```text
last_activity_at < cutoff
```

Si alcanza `max_pages_per_run` sin llegar al cutoff:

- registrar `WARNING`;
- no avanzar `last_successful_discovery_at` como si el discovery hubiese sido completo.

Los topics no candidatos pueden guardar metadatos minimos:

- `external_topic_id`;
- `last_activity_at`;
- `last_seen_at`.

No deben entrar en favorite monitoring.

## 14. Favorites

Un favorito es un topic confirmado como relevante para un watch item.

Campos conceptuales:

- `topic_id`;
- `watch_item_id`;
- `favorited_at`;
- `is_active`;
- `current_status`;
- `current_price`;
- `currency`;
- `last_checked_at`;
- `last_content_hash`;
- `last_classified_at`.

Estados de disponibilidad:

- `AVAILABLE`;
- `RESERVED`;
- `SOLD`;
- `WITHDRAWN`;
- `UNKNOWN`.

Reglas:

- `AVAILABLE` se sigue monitorizando;
- `RESERVED` puede seguir monitorizandose;
- `SOLD` y `WITHDRAWN` pasan a `is_active = false`;
- no borrar fisicamente favoritos.

CLI manual:

```bash
python -m app favorite deactivate <TOPIC_ID>
python -m app favorite reactivate <TOPIC_ID>
```

## 15. Favorites Check

Para todos los favoritos activos:

1. `GET canonical_topic_url`;
2. extraer contenido actual;
3. calcular `content_hash`;
4. si el hash no cambia, no llamar a IA y no crear evento;
5. si cambia, clasificar el cambio.

Topic eliminado o inaccesible:

- distinguir `HTTP_TRANSIENT_ERROR`, `TOPIC_NOT_FOUND`, `TOPIC_UNAVAILABLE`;
- no marcar inactivo por un unico fallo;
- confirmar con `favorites.unavailable_confirmation_runs`.

## 16. Hashing Y Almacenamiento De Posts

Para minimizar almacenamiento, v1 persiste hashes y metadatos de posts, no el texto completo de los posts.

El hash de contenido se calcula a partir de contenido limpio y estable:

```text
topic_id
+ post_id
+ author
+ posted_at
+ normalized_post_text
```

No usar HTML completo para hashes.

## 17. Clasificacion

El scraper no depende directamente de OpenAI. Usa una interfaz:

```python
class ListingClassifier(Protocol):
    def classify_new_candidate(self, watch_item, topic) -> ClassificationResult: ...
    def classify_favorite_update(self, previous_state, topic) -> ClassificationResult: ...
```

Tests deben poder usar `FakeClassifier`.

Si `ai.enabled: false`, los candidatos deben quedar pendientes de clasificacion y no convertirse automaticamente en favoritos.

El modelo concreto no se fija en esta SPEC. Debe ser configurable.

Resultado estructurado con Pydantic:

```json
{
  "matches_watch_item": true,
  "listing_type": "offer",
  "availability": "available",
  "price": 123.45,
  "currency": "EUR",
  "confidence": 0.93,
  "evidence": []
}
```

Tipos conceptuales de listing:

- `OFFER`;
- `WANTED`;
- `INFORMATION`;
- `DISCUSSION`;
- `OTHER`.

Un topic que mencione un watch item no se convierte automaticamente en favorito. Debe ser un `OFFER` relevante y superar umbrales configurados.

No enviar HTML completo a OpenAI. Enviar solo datos estructurados limpios:

- watch item;
- titulo;
- autor original;
- posts relevantes;
- estado previo cuando aplique.

## 18. Precio E Historicos

Guardar estado actual:

- `current_price`;
- `currency`;
- `price_updated_at`.

El precio puede aparecer o cambiar en:

- titulo;
- primer post editado;
- respuesta posterior del autor.

Historico:

- `price_history`;
- `status_history`.

Si la clasificacion devuelve `price = null`, no borrar automaticamente el precio anterior.

## 19. Eventos

Eventos v1:

- `NEW_FAVORITE`;
- `PRICE_CHANGED`;
- `STATUS_CHANGED`;
- `BECAME_UNAVAILABLE`;
- `FAVORITE_REACTIVATED`;
- `ERROR`.

Cada evento tiene:

- `topic_id`;
- `event_type`;
- `payload_json`;
- `created_at`;
- `notification_status`;
- `notified_at`;
- `deduplication_key`.

`deduplication_key` debe ser unico y evitar emails duplicados.

Ejemplo conceptual:

```text
topic_id + event_type + content_hash
```

## 20. Notificaciones

Canal v1: email de texto plano via SMTP Gmail.

Variables de entorno:

```text
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
NOTIFICATION_EMAIL
```

Nunca almacenar credenciales en SQLite ni YAML.

La configuracion debe permitir indicar que eventos se notifican:

```yaml
notifications:
  email_enabled: true
  notify_event_types:
    - NEW_FAVORITE
    - PRICE_CHANGED
    - STATUS_CHANGED
    - BECAME_UNAVAILABLE
```

Si Gmail falla, el evento queda pendiente para retry.

## 21. SQLite Y Alembic

Ruta por defecto:

```text
/app/data/monitor.db
```

En desarrollo local bajo la raiz del repo:

```text
data/monitor.db
```

Requisitos:

- SQLAlchemy;
- Alembic;
- `PRAGMA journal_mode=WAL`;
- `PRAGMA foreign_keys=ON`;
- migraciones versionadas;
- sin PostgreSQL, Redis ni colas externas en v1.

Esquema conceptual:

- `topics`;
- `candidate_matches`;
- `favorites`;
- `price_history`;
- `status_history`;
- `topic_posts`;
- `events`;
- `app_state`.

`topics.external_topic_id` debe ser `UNIQUE NOT NULL`.

`candidate_matches` guarda candidatos por topic y watch item cuando aun no son favoritos, incluyendo candidatos pendientes de clasificacion si `ai.enabled=false` o si la clasificacion falla de forma recuperable.

## 22. Configuracion

Ejemplo base:

```yaml
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96

bootstrap:
  pages: 10

discovery:
  overlap_minutes: 30
  max_pages_per_run: 50

favorites:
  check_every_run: true
  unavailable_confirmation_runs: 2

scraping:
  request_delay_seconds: 2
  timeout_seconds: 20
  max_retries: 3

ai:
  enabled: true
  model: null
  match_confidence_threshold: 0.85

notifications:
  email_enabled: true
  notify_event_types:
    - NEW_FAVORITE
    - PRICE_CHANGED
    - STATUS_CHANGED
    - BECAME_UNAVAILABLE

debug:
  save_failed_html: false

watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
    aliases: []
```

La carga YAML debe implementarse con `PyYAML`, declarado como dependencia runtime del proyecto.

## 23. Cliente HTTP

Crear `ArmasEsClient` con responsabilidades:

- GET;
- timeouts;
- retries;
- User-Agent configurable;
- rate limiting;
- encoding;
- clasificacion de errores HTTP.

No mezclar networking con parsing.

User-Agent ejemplo:

```text
PersonalForumMonitor/1.0
```

Requests contra armas.es:

- secuenciales;
- con delay configurable;
- sin concurrencia en v1;
- solo las minimas necesarias para cumplir el flujo.

## 24. Docker Y Portabilidad

Estructura objetivo en la raiz del repo:

```text
forum_scraper/
|-- Dockerfile
|-- docker-compose.yml
|-- pyproject.toml
|-- README.md
|-- .env.example
|-- alembic.ini
|-- config/
|   `-- config.example.yaml
|-- data/
|   `-- .gitkeep
|-- backups/
|   `-- .gitkeep
|-- src/
|-- tests/
`-- docs/
```

Persistencia Docker:

```yaml
volumes:
  - ./data:/app/data
  - ./backups:/app/backups
  - ./config:/app/config:ro
```

Debe funcionar en:

- `linux/amd64`;
- `linux/arm64`.

## 25. CLI

Comandos v1:

```bash
python -m app bootstrap
python -m app bootstrap --force
python -m app run
python -m app status
python -m app favorites
python -m app inspect <TOPIC_ID>
python -m app retry-notifications
python -m app backup
python -m app favorite deactivate <TOPIC_ID>
python -m app favorite reactivate <TOPIC_ID>
python -m app debug-listing
```

`status` debe mostrar resumen legible de fuente, bootstrap, discovery, favoritos, notificaciones pendientes y metricas de la ultima ejecucion.

`backup` debe usar la API de backup de SQLite y crear:

```text
/app/backups/monitor-YYYYMMDD-HHMMSS.db
```

## 26. Logs

Logs estructurados legibles.

Ejemplos:

```text
INFO source=armas_es action=listing_fetch page=1
INFO source=armas_es topics=18 announcements_skipped=4
INFO topic=1234 candidate=false
INFO topic=5678 candidate=true watch_item=item_001
INFO topic=5678 action=topic_fetch
INFO topic=5678 favorite_created=true
INFO topic=5678 content_changed=false
INFO topic=9999 price_changed=true
INFO run_completed=true
```

No registrar passwords, API keys, cookies sensibles ni HTML completo salvo diagnostico explicitamente habilitado.

## 27. Fixtures Y Tests

Tests deben pasar sin conexion a armas.es.

Fixtures sanitizadas:

```text
tests/fixtures/armas_es/
|-- listing_page_1.html
|-- listing_page_2.html
|-- topic_legal_notice.html
|-- topic_multipage_page_1.html
`-- topic_multipage_page_2.html
```

Antes de fijar selectores definitivos, un agente autorizado debe descargar unas pocas paginas reales de forma controlada y respetuosa:

- `robots.txt`;
- listing pagina 1;
- listing pagina 2;
- un topic de una pagina;
- un topic con varias paginas, si se puede identificar sin exceso de navegacion.

Los fixtures deben sanitizarse antes de commitearse.

Documentar selectores elegidos en:

```text
docs/armas_es_parser.md
```

## 28. Tests Obligatorios

Parser listing:

- detecta exactamente bloque `Temas`;
- excluye `Anuncios`;
- extrae `t`;
- elimina `sid`;
- extrae titulo;
- extrae snippet;
- extrae creador;
- extrae fecha original;
- extrae ultima actividad;
- extrae replies;
- extrae views;
- detecta enlace `Siguiente`.

Parser topic:

- obtiene posts visibles;
- distingue autor original;
- extrae fecha individual;
- detecta paginacion interna.

Comportamiento:

- bootstrap recorre 10 paginas configuradas;
- bootstrap ignora anuncios;
- bootstrap abre solo candidatos;
- dos runs sin cambios no crean nuevos eventos;
- topic no relevante con nueva actividad no entra en favoritos;
- favorite unchanged no llama a IA;
- favorite changed llama a clasificacion;
- eventos no se duplican;
- fallos de email dejan eventos pendientes;
- PC apagado y reanudado recupera desde checkpoint con overlap.

## 29. Condiciones De Acceso

Antes de activar ejecuciones periodicas:

1. comprobar `robots.txt`;
2. revisar condiciones aplicables del sitio si estan disponibles;
3. documentar resultado en `docs/access_policy.md`.

Si el scraping publico deja de ser viable, la aplicacion debe fallar explicitamente y registrar el motivo.

## 30. Definition Of Done v1

v1 esta terminada cuando:

1. `docker compose build` funciona desde la raiz del repo;
2. los tests pasan sin conexion a armas.es;
3. fixtures reales sanitizadas cubren parsers;
4. bootstrap analiza las paginas configuradas;
5. `Anuncios` no entra en discovery;
6. topics ordinarios se identifican por `t`;
7. `sid` no forma parte de identidad;
8. topics no candidatos no se descargan individualmente;
9. candidatos pueden convertirse en favoritos;
10. favoritos se monitorizan directamente;
11. favoritos sin cambios no llaman a IA;
12. cambios generan historicos;
13. eventos no se duplican;
14. notificaciones son configurables por tipo de evento;
15. fallos de Gmail dejan eventos pendientes;
16. apagado y reanudacion recuperan actividad desde checkpoint;
17. SQLite sobrevive a recrear contenedores;
18. existe backup consistente;
19. copiar `config/`, `data/`, `backups/` y `.env` permite continuar en otra maquina;
20. Docker es compatible con amd64 y arm64;
21. README explica PC -> Raspberry;
22. no hay secrets en Git;
23. no existen mecanismos de evasion.

## 31. Prioridades

Cuando exista conflicto:

```text
correctitud
> no perder eventos
> idempotencia
> simplicidad
> minimizar requests
> minimizar llamadas IA
> optimizacion
```

No sobredisenar. SQLite, Docker y procesos secuenciales bastan para v1.
