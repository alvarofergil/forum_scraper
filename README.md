# Forum Scraper Monitor

Monitor personal y de bajo impacto para seguir anuncios publicos de compraventa en foros
phpBB, empezando por el subforo de compraventa de armas.es.

El objetivo de la version v1 es detectar temas que coincidan con una watchlist definida por
configuracion, confirmar si son ofertas relevantes, guardarlos como favoritos, seguir sus
cambios aunque desaparezcan de las primeras paginas del foro y notificar eventos importantes
por email.

## Estado Actual

Proyecto en fase inicial, con el nucleo tecnico de HITO-01 completado y endurecido.

Ya existe:

- layout `src/`;
- paquete principal `app`;
- paquetes previstos para fuentes, discovery, clasificacion, favoritos, eventos,
  notificaciones y almacenamiento;
- carga y validacion de configuracion YAML;
- modelos de dominio base;
- SQLite con SQLAlchemy, Alembic y PRAGMAs requeridos;
- URLs canonicas y cliente HTTP secuencial para `armas_es`;
- persistencia UTC, eventos/candidatos idempotentes y tests sin red;
- pytest y Ruff configurados;
- cobertura unitaria de la base tecnica.

Los parsers HTML, discovery, favoritos de negocio, clasificacion, notificaciones y Docker se
implementaran por tareas incrementales siguiendo las SPECs del proyecto.

## Principios

- Sin interfaz web en v1.
- SQLite es la unica fuente de estado operativo.
- Toda la watchlist vive en `config/config.yaml`; no se hardcodean marcas ni modelos en Python.
- El acceso a armas.es debe ser secuencial, minimo y respetuoso.
- No se implementan mecanismos de evasion: sin CAPTCHA bypass, proxy rotation, fingerprint
  evasion, automatizacion de cuentas ni bypass de rate limits.
- Los favoritos se monitorizan por URL canonica, independientemente del discovery.
- Los tests unitarios deben pasar sin red.
- No se guardan secrets, cookies, HTML bruto ni texto completo de posts en SQLite.
- El proyecto debe poder moverse de un PC a una Raspberry Pi copiando `config/`, `data/`,
  `backups/` y `.env`.

## Arquitectura Prevista

```text
forum_scraper/
|-- pyproject.toml
|-- README.md
|-- config/
|-- data/
|-- backups/
|-- docs/
|-- src/
|   |-- app/
|   |-- sources/
|   |   `-- armas_es/
|   |-- discovery/
|   |-- classification/
|   |-- favorites/
|   |-- events/
|   |-- notifications/
|   `-- storage/
`-- tests/
```

Responsabilidades principales:

- `sources/armas_es`: URLs, cliente HTTP y parsers especificos de armas.es.
- `discovery`: recorrido de listings, matcher barato y candidatos.
- `classification`: interfaz de clasificacion y adaptadores reemplazables.
- `favorites`: seguimiento de favoritos, hashing e historicos.
- `events`: eventos idempotentes y estado de notificacion.
- `notifications`: envio de email y reintentos.
- `storage`: SQLite, SQLAlchemy, Alembic y repositorios.
- `app`: CLI y cableado de aplicacion.

## Comandos Operativos Para v1

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

`python -m app run` ejecuta una unica pasada finita de discovery y comprobacion de
favoritos. Si `notifications.email_enabled=true`, al final de la pasada intenta enviar o
reintentar las notificaciones pendientes y fallidas con las variables SMTP del entorno.
Si el email esta desactivado, no carga secretos SMTP ni abre conexiones SMTP.

`python -m app retry-notifications` queda como comando de recuperacion manual para
reenviar eventos `PENDING` o `FAILED`.

`python -m app status` puede ejecutarse sin YAML para inspeccionar una base de datos. Si
se pasa `--config`, los contadores `events_pending` y `events_failed` reflejan solo
eventos accionables para `notifications.notify_event_types`; los excluidos aparecen en
`events_pending_non_notifiable` y `events_failed_non_notifiable`.

`python -m app backup` sin ruta crea una copia consistente con nombre
`backups/monitor-YYYYMMDD-HHMMSS.db` y evita sobrescribir colisiones en el mismo segundo
anadiendo un sufijo. `python -m app backup <RUTA>` respeta la ruta explicita.

## Desarrollo Local

Requisitos actuales:

- Python 3.12 o superior.
- Entorno virtual en `.venv`.

Instalacion para desarrollo:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Verificacion:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Configuracion

La configuracion real no se commitea.

Archivos previstos:

- `config/config.example.yaml`: ejemplo versionado.
- `config/config.yaml`: configuracion local del usuario, ignorada por Git.
- `.env`: secrets locales, ignorado por Git.
- `.env.example`: ejemplo versionado cuando se implemente Docker/notificaciones.

Las credenciales SMTP y cualquier API key deben venir de variables de entorno, nunca de YAML,
SQLite, tests o fixtures.

## Flujo De Trabajo

El proyecto se desarrolla tarea a tarea.

Para cada tarea:

1. leer `SPECs/AGENT_START.md`;
2. leer la fila de la tarea en `SPECs/forum_scraper_tasks.md`;
3. leer la sub-SPEC activa y `SPECs/skills/forum-task-agent/SKILL.md`;
4. implementar con tests focalizados;
5. ejecutar la verificacion requerida.

El flujo de rama, commit, push y PR se ejecuta cuando se pida release o cuando la tarea lo exija expresamente.

Una tarea queda en `REVIEW` cuando el PR existe y en `DONE` cuando el PR se mergea en `main`.

## Documentacion Del Proyecto

Las SPECs viven dentro del repo, en `SPECs/`, y actuan como contrato operativo para agentes IA:

- `SPECs/forum_scraper.md`: SPEC maestra.
- `SPECs/forum_scraper_tasks.md`: documento maestro de tareas.
- `SPECs/task_specs/`: sub-SPECs por tarea.
- `SPECs/skills/forum-task-agent/SKILL.md`: checklist unico de trabajo.

`AGENT_START.md` es la autoridad de arranque: lectura progresiva, un unico agente por defecto y SPEC maestra solo por fragmentos salvo necesidad global.
