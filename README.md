# Forum Scraper Monitor

Forum Scraper Monitor es una aplicacion de linea de comandos para vigilar anuncios publicos
en foros phpBB con trafico bajo y secuencial. La version actual esta preparada para el
subforo de compraventa de `armas.es` y permite descubrir temas que coinciden con una
watchlist configurada por el usuario, clasificarlos opcionalmente con IA, guardar favoritos,
seguir cambios en esos favoritos y notificar eventos por email.

La aplicacion no incluye interfaz web. Se ejecuta como comandos finitos que pueden lanzarse
manualmente, desde Docker Compose o desde un programador externo como cron o systemd timers.

## Funcionalidad Principal

- Descubrimiento de temas publicos en el foro configurado.
- Coincidencia inicial contra una watchlist de marcas, modelos y alias.
- Clasificacion opcional con OpenAI para confirmar ofertas relevantes.
- Persistencia de favoritos, candidatos, eventos, historicos de precio y estado.
- Seguimiento de favoritos aunque desaparezcan de las primeras paginas del foro.
- Notificaciones SMTP para eventos configurables.
- Comandos operativos para estado, inspeccion, reintentos, backups y gestion de favoritos.
- Despliegue portable con SQLite, Docker y directorios de estado externos al contenedor.

## Componentes

- **CLI**: punto de entrada operativo mediante `python -m app`.
- **Fuente `armas_es`**: cliente HTTP secuencial, construccion de URLs canonicas y parsers de
  listados y temas publicos.
- **Discovery**: recorre listados, aplica la watchlist y crea candidatos pendientes o favoritos
  confirmados.
- **Clasificacion**: adaptador opcional de OpenAI para validar si un tema es una oferta del
  articulo vigilado.
- **Favoritos**: monitoriza temas ya seleccionados, detecta cambios de precio, estado y
  disponibilidad, y mantiene historicos.
- **Eventos**: registra eventos deduplicados y estados de notificacion.
- **Notificaciones**: envia emails por SMTP y permite reintentar entregas fallidas.
- **Almacenamiento**: SQLite con migraciones automaticas al abrir la base de datos.

## Dependencias

### Ejecucion Local

- Python 3.12 o superior.
- Paquetes Python instalados desde `pyproject.toml`: SQLAlchemy, Alembic, PyYAML, Pydantic y
  OpenAI.
- Una base SQLite local en `data/monitor.db`.
- Opcional: cuenta/API key de OpenAI si se activa la clasificacion con IA.
- Opcional: servidor SMTP si se activan las notificaciones por email.

### Docker

- Docker y Docker Compose.
- Los mismos archivos de configuracion y secretos que en ejecucion local.

## Configuracion

La configuracion vive en archivos locales que no se versionan:

- `config/config.yaml`: configuracion principal.
- `.env`: secretos y credenciales.
- `data/`: base SQLite operativa.
- `backups/`: copias generadas por la aplicacion.

El repositorio incluye plantillas seguras:

```bash
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

Edita `config/config.yaml` para definir la fuente, los limites de scraping, la watchlist,
la IA y las notificaciones. Edita `.env` solo con los secretos necesarios.

El ejemplo deja `ai.enabled=false` para que el primer arranque no requiera coste ni secretos
OpenAI. Con IA desactivada, el monitor puede detectar candidatos por coincidencia inicial,
pero no confirma nuevos favoritos automaticamente. Para activar la clasificacion completa,
configura `ai.enabled=true`, un `ai.model` no nulo y `OPENAI_API_KEY` en `.env`. La
API key por si sola no basta si `ai.model` sigue en `null`.

Si `notifications.email_enabled=true`, define en `.env`:

```dotenv
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFICATION_EMAIL=
```

Para ejecutar sin email, cambia `notifications.email_enabled` a `false`.

## Instalacion Local

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

Despues de editar la configuracion, inicializa la base de datos y ejecuta el bootstrap:

```bash
.venv/bin/python -m app bootstrap
```

## Ejecucion

Comandos locales:

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

`python -m app run` ejecuta una unica pasada finita: discovery incremental, revision de
favoritos y, si procede, envio o reintento de notificaciones.

`python -m app status` muestra contadores operativos, fuente activa, favoritos activos,
backlog pendiente y los ultimos
checkpoints conocidos de discovery, favoritos y notificaciones.

## Docker

Construir la imagen:

```bash
docker compose build
```

Ejecutar comandos operativos:

```bash
docker compose run --rm forum-scraper bootstrap
docker compose run --rm forum-scraper run
docker compose run --rm forum-scraper status
docker compose run --rm forum-scraper retry-notifications
docker compose run --rm forum-scraper backup
```

Docker Compose monta:

- `config/` como solo lectura dentro del contenedor.
- `data/` con escritura para conservar SQLite.
- `backups/` con escritura para conservar copias.
- `.env` como archivo opcional de variables de entorno.

## Despliegue Portable

El despliegue recomendado para una maquina dedicada, incluida Raspberry Pi, es Docker Compose:

1. Copia el repositorio en la maquina destino.
2. Crea `config/config.yaml` y `.env` desde las plantillas.
3. Ejecuta `docker compose build`.
4. Inicializa con `docker compose run --rm forum-scraper bootstrap`.
5. Programa ejecuciones periodicas de `docker compose run --rm forum-scraper run`.
6. Revisa el estado con `docker compose run --rm forum-scraper status`.

Para migrar entre maquinas, copia `config/`, `data/`, `backups/` y `.env`. No hace falta
copiar `.venv`, caches ni artefactos de build.

## Documentacion

La guia completa de instalacion, configuracion, despliegue y uso esta en
[`docs/user_guide.md`](docs/user_guide.md).

Las notas tecnicas adicionales sobre politica de acceso y parsers estan en `docs/`.
