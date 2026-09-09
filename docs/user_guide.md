# Guia De Usuario

Esta guia explica como instalar, configurar, desplegar y ejecutar Forum Scraper Monitor desde
cero. Esta pensada para una persona que no conoce el proyecto y quiere dejarlo funcionando en
un PC, servidor domestico o Raspberry Pi.

## 1. Que Hace La Aplicacion

Forum Scraper Monitor vigila anuncios publicos de un foro phpBB. En la version actual trabaja
con el subforo de compraventa de `armas.es`.

El flujo normal es:

1. Lee una watchlist definida por ti en `config/config.yaml`.
2. Recorre paginas publicas del foro de forma secuencial y con pausas configurables.
3. Detecta temas cuyo titulo o resumen coinciden con algun articulo vigilado.
4. Si la IA esta activada, abre el tema y pide una clasificacion para confirmar que es una
   oferta relevante.
5. Guarda las coincidencias confirmadas como favoritos.
6. Revisa favoritos existentes en ejecuciones posteriores.
7. Genera eventos cuando encuentra favoritos nuevos, cambios de precio, cambios de estado,
   reactivaciones o errores operativos.
8. Si el email esta activado, envia o reintenta notificaciones por SMTP.

La aplicacion no se queda ejecutando en segundo plano. Cada llamada a `run` hace una pasada
finita y termina. Para vigilancia continua debes programar ese comando con cron, systemd timer
u otro planificador.

## 2. Requisitos

### Opcion A: Docker

Requisitos:

- Docker instalado.
- Docker Compose disponible mediante `docker compose`.
- Acceso de red desde la maquina donde se ejecuta el contenedor.

Esta es la opcion recomendada para despliegues estables y para Raspberry Pi.

### Opcion B: Python Local

Requisitos:

- Python 3.12 o superior.
- `pip`.
- Un entorno virtual Python.
- Acceso de red desde la maquina donde se ejecuta el comando.

Esta opcion es comoda para desarrollo, pruebas manuales o ejecucion directa en un PC.

### Servicios Opcionales

- OpenAI API: necesaria solo si configuras `ai.enabled=true`.
- SMTP: necesario solo si configuras `notifications.email_enabled=true`.

## 3. Estructura Operativa

Los archivos importantes para operar la aplicacion son:

| Ruta | Proposito |
|---|---|
| `config/config.example.yaml` | Plantilla versionada de configuracion. |
| `config/config.yaml` | Configuracion real del usuario. No se versiona. |
| `.env.example` | Plantilla versionada de variables de entorno. |
| `.env` | Secretos y credenciales reales. No se versiona. |
| `data/monitor.db` | Base SQLite operativa. Se crea automaticamente. |
| `backups/` | Directorio de copias SQLite generadas por `backup`. |
| `docker-compose.yml` | Despliegue local con volumenes portables. |

Para mover la instalacion a otra maquina, conserva `config/`, `data/`, `backups/` y `.env`.

## 4. Instalacion Con Docker

Desde la raiz del repositorio:

```bash
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

Edita `config/config.yaml` y `.env` antes de ejecutar el monitor. Despues construye la imagen:

```bash
docker compose build
```

Comprueba que el comando responde:

```bash
docker compose run --rm forum-scraper status
```

La primera ejecucion puede crear `data/monitor.db` y aplicar migraciones automaticamente.

## 5. Instalacion Con Python Local

Desde la raiz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

Edita `config/config.yaml` y `.env`.

Comprueba la CLI:

```bash
.venv/bin/python -m app --help
```

En los ejemplos siguientes, si usas Python local puedes sustituir `python -m app` por
`.venv/bin/python -m app`.

## 6. Configuracion Principal

La aplicacion lee por defecto `config/config.yaml`. Tambien puedes indicar otra ruta con
`--config` en los comandos que necesitan configuracion:

```bash
python -m app --config config/otra-config.yaml run
```

Una configuracion minima parte de `config/config.example.yaml`:

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
  user_agent: "PersonalForumMonitor/1.0"

ai:
  enabled: false
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

### source

Define la fuente del foro:

- `type`: debe ser `armas_es`.
- `base_url`: URL base, normalmente `https://www.armas.es`.
- `forum_id`: identificador phpBB del subforo. Para el subforo actual de compraventa es `96`.

### bootstrap

Controla el descubrimiento inicial:

- `pages`: numero de paginas que se recorreran durante `bootstrap`.

El bootstrap se ejecuta una vez para poblar el estado inicial. Si necesitas repetirlo, usa
`bootstrap --force`.

### discovery

Controla cada pasada incremental:

- `overlap_minutes`: margen hacia atras respecto al ultimo checkpoint de discovery. Ayuda a no
  perder temas cuando hay pequenos desfases entre ejecuciones.
- `max_pages_per_run`: limite de paginas por pasada incremental.

### favorites

Controla el seguimiento de favoritos:

- `check_every_run`: si es `true`, cada `run` revisa favoritos activos despues del discovery.
- `unavailable_confirmation_runs`: numero de confirmaciones requeridas antes de tratar un favorito
  como no disponible cuando el tema desaparece o no puede localizarse.

### scraping

Controla el comportamiento HTTP:

- `request_delay_seconds`: pausa entre peticiones. Debe mantenerse conservadora.
- `timeout_seconds`: timeout por peticion.
- `max_retries`: reintentos ante errores recuperables.
- `user_agent`: identificador enviado al foro.

La aplicacion esta pensada para uso personal, secuencial y de bajo impacto. No utiliza login,
proxies, evasion de CAPTCHA ni concurrencia.

### ai

Controla la clasificacion con OpenAI:

- `enabled`: activa o desactiva la IA.
- `model`: modelo OpenAI que se usara cuando `enabled=true`.
- `match_confidence_threshold`: confianza minima para crear un favorito automaticamente.

El valor por defecto es `ai.enabled=false`. Asi puedes arrancar sin coste ni secretos. En ese
modo se crean candidatos pendientes, pero no favoritos nuevos confirmados por IA.

Para uso completo con clasificacion:

```yaml
ai:
  enabled: true
  model: "gpt-4.1-mini"
  match_confidence_threshold: 0.85
```

Ademas, define `OPENAI_API_KEY` en `.env`. Debes configurar un `ai.model` no nulo; la API key
por si sola no basta si el modelo sigue en `null`.

### notifications

Controla el email:

- `email_enabled`: si es `true`, `run` y `retry-notifications` cargan credenciales SMTP desde
  `.env` e intentan enviar eventos accionables.
- `notify_event_types`: lista de tipos de evento que generan email.

Eventos disponibles:

- `NEW_FAVORITE`
- `PRICE_CHANGED`
- `STATUS_CHANGED`
- `BECAME_UNAVAILABLE`
- `FAVORITE_REACTIVATED`
- `ERROR`

Los eventos no incluidos en `notify_event_types` pueden quedar registrados pero se saltan durante
el envio de email.

### watchlist

Define los articulos que quieres vigilar:

```yaml
watchlist:
  - id: rifle_001
    brand: "Marca"
    model: "Modelo"
    aliases:
      - "Alias frecuente"
      - "Nombre alternativo"
```

Recomendaciones:

- Usa `id` estable y unico. No lo cambies despues de crear favoritos, salvo que sepas como afecta
  al historial.
- Pon marca y modelo como los escribirian los vendedores.
- Usa `aliases` para abreviaturas, errores frecuentes o denominaciones alternativas.

## 7. Variables De Entorno

Copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

Variables SMTP, requeridas solo con `notifications.email_enabled=true`:

```dotenv
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFICATION_EMAIL=
```

Variable OpenAI, requerida solo con `ai.enabled=true`:

```dotenv
OPENAI_API_KEY=
```

Los secretos deben estar en `.env` o en el entorno del proceso. No los pongas en
`config/config.yaml`.

## 8. Primer Arranque

### 8.1 Revisar Configuracion

Antes de tocar la red, valida mentalmente:

- `source.base_url` apunta a la fuente esperada.
- `source.forum_id` es el foro correcto.
- `watchlist` no esta vacia.
- Si el email esta activado, `.env` tiene las variables SMTP.
- Si la IA esta activada, `.env` tiene `OPENAI_API_KEY` y `config/config.yaml` tiene `ai.model`.

### 8.2 Ver Estado Inicial

Con Python local:

```bash
python -m app status
```

Con Docker:

```bash
docker compose run --rm forum-scraper status
```

Este comando crea o migra la base si hace falta y muestra contadores. Puede ejecutarse sin YAML,
aunque con `--config` muestra tambien la fuente y filtra contadores de notificaciones segun
`notify_event_types`:

```bash
python -m app --config config/config.yaml status
```

### 8.3 Ejecutar Bootstrap

Con Python local:

```bash
python -m app bootstrap
```

Con Docker:

```bash
docker compose run --rm forum-scraper bootstrap
```

El bootstrap recorre `bootstrap.pages` paginas y crea estado inicial. Si ya se ejecuto antes,
devuelve un aviso. Para repetirlo de forma explicita:

```bash
python -m app bootstrap --force
docker compose run --rm forum-scraper bootstrap --force
```

## 9. Ejecucion Habitual

Ejecuta una pasada:

```bash
python -m app run
```

o con Docker:

```bash
docker compose run --rm forum-scraper run
```

Una pasada hace:

1. Discovery incremental desde las primeras paginas del foro.
2. Clasificacion de candidatos si la IA esta activada.
3. Revision de favoritos activos si `favorites.check_every_run=true`.
4. Envio o reintento de emails si `notifications.email_enabled=true`.
5. Actualizacion de checkpoints operativos si las fases terminan correctamente.

El comando imprime un resumen con contadores como paginas vistas, candidatos clasificados,
pendientes restantes, favoritos revisados y notificaciones enviadas o fallidas.

## 10. Programar Ejecuciones Periodicas

La aplicacion no incorpora un scheduler interno. Programa `run` desde el sistema operativo.

### Ejemplo Con Cron

Editar el crontab:

```bash
crontab -e
```

Ejemplo para ejecutar cada 30 minutos con Docker:

```cron
*/30 * * * * cd /ruta/al/forum_scraper && docker compose run --rm forum-scraper run >> logs/forum-scraper.log 2>&1
```

Crea el directorio de logs si decides usar ese ejemplo:

```bash
mkdir -p logs
```

### Ejemplo Con Systemd Timer

Servicio `forum-scraper.service`:

```ini
[Unit]
Description=Forum Scraper Monitor run

[Service]
Type=oneshot
WorkingDirectory=/ruta/al/forum_scraper
ExecStart=/usr/bin/docker compose run --rm forum-scraper run
```

Timer `forum-scraper.timer`:

```ini
[Unit]
Description=Run Forum Scraper Monitor every 30 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
```

Activalo:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now forum-scraper.timer
```

## 11. Comandos Operativos

### bootstrap

```bash
python -m app bootstrap
python -m app bootstrap --force
```

Ejecuta el descubrimiento inicial acotado por `bootstrap.pages`.

### run

```bash
python -m app run
```

Ejecuta una pasada incremental completa y termina.

### status

```bash
python -m app status
python -m app --config config/config.yaml status
```

Muestra:

- temas y favoritos almacenados;
- favoritos activos e inactivos;
- candidatos pendientes;
- eventos pendientes, fallidos y enviados;
- eventos no notificables segun configuracion;
- ultimos
checkpoints conocidos de discovery, favoritos y notificaciones;
- fuente activa cuando se usa `--config`.

### favorites

```bash
python -m app favorites
```

Lista favoritos monitorizados con id interno, topic externo, watch item, estado, precio y URL.

### inspect

```bash
python -m app inspect <TOPIC_ID>
```

Inspecciona un tema por id externo del foro o por id numerico interno. Muestra metadatos seguros,
favorito asociado si existe y eventos registrados.

### favorite deactivate / reactivate

```bash
python -m app favorite deactivate <TOPIC_ID>
python -m app favorite reactivate <TOPIC_ID>
```

Permite pausar o reactivar manualmente el seguimiento de un favorito. La operacion es reversible
y genera un evento de auditoria.

### retry-notifications

```bash
python -m app retry-notifications
```

Reintenta eventos con notificacion `PENDING` o `FAILED` que esten incluidos en
`notifications.notify_event_types`.

### backup

```bash
python -m app backup
python -m app backup backups/copia-manual.db
```

Crea una copia consistente de SQLite. Sin ruta explicita genera un archivo con timestamp en
`backups/`.

### debug-listing

```bash
python -m app debug-listing
```

Descarga y parsea la primera pagina del listado configurado, e imprime los temas detectados. Es
util para comprobar conectividad y forma actual del listado.

## 12. Uso Con Base De Datos Alternativa

Por defecto se usa `data/monitor.db`. Puedes indicar otra ruta con `--database`:

```bash
python -m app --database data/pruebas.db status
python -m app --database data/pruebas.db run
```

La opcion es global y se coloca antes del subcomando.

## 13. Notificaciones Por Email

Cuando `notifications.email_enabled=true`, `run` intenta enviar al final de la pasada los eventos
pendientes o fallidos que coincidan con `notify_event_types`.

Configuracion minima:

```yaml
notifications:
  email_enabled: true
  notify_event_types:
    - NEW_FAVORITE
    - PRICE_CHANGED
    - STATUS_CHANGED
    - BECAME_UNAVAILABLE
```

`.env`:

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=usuario@example.com
SMTP_PASSWORD=...
NOTIFICATION_EMAIL=destino@example.com
```

El envio usa STARTTLS, login SMTP y mensajes de texto plano.

Si faltan variables SMTP, el comando informa un error de configuracion. Para desactivar email:

```yaml
notifications:
  email_enabled: false
```

## 14. Clasificacion Con OpenAI

La IA se usa para confirmar si un candidato barato es realmente una oferta relevante del articulo
vigilado. Sin IA, el sistema puede dejar candidatos pendientes, pero no crea nuevos favoritos
confirmados automaticamente.

Pasos:

1. Define `OPENAI_API_KEY` en `.env`.
2. Cambia `ai.enabled` a `true`.
3. Configura `ai.model` con un modelo valido.
4. Ajusta `match_confidence_threshold` si quieres ser mas estricto o mas permisivo.

Ejemplo:

```yaml
ai:
  enabled: true
  model: "gpt-4.1-mini"
  match_confidence_threshold: 0.85
```

Si `ai.enabled=true` y `ai.model` es `null`, la aplicacion rechaza la configuracion.
`OPENAI_API_KEY` sin modelo no basta.

## 15. Backups Y Migracion

Crear backup:

```bash
python -m app backup
docker compose run --rm forum-scraper backup
```

Los backups se guardan en `backups/monitor-YYYYMMDD-HHMMSS.db` cuando no indicas ruta.

Para migrar a otra maquina:

1. Deten programaciones activas para evitar escrituras durante la copia.
2. Ejecuta `backup`.
3. Copia `config/`, `data/`, `backups/` y `.env` a la maquina destino.
4. En destino, ejecuta `docker compose build`.
5. Comprueba `docker compose run --rm forum-scraper status`.
6. Lanza `docker compose run --rm forum-scraper run`.
7. Reactiva el cron o systemd timer en destino.

No copies `.venv`, `.pytest_cache`, `.ruff_cache` ni caches de Docker.

## 16. Despliegue En Raspberry Pi

Recomendacion:

1. Instala Docker en la Raspberry Pi.
2. Clona o copia el repositorio.
3. Copia tu `config/config.yaml` y `.env`.
4. Copia `data/monitor.db` si vienes de otra maquina.
5. Ejecuta:

```bash
docker compose build
docker compose run --rm forum-scraper status
docker compose run --rm forum-scraper run
```

La imagen parte de `python:3.12-slim` y se construye para la arquitectura local de la maquina.

## 17. Mantenimiento

Rutina recomendada:

- Revisa `status` periodicamente.
- Ejecuta `backup` antes de actualizar codigo o mover la instalacion.
- Mira `events_failed` si no llegan emails.
- Usa `retry-notifications` despues de corregir credenciales SMTP o problemas de red.
- Ajusta `watchlist` cuando veas alias o denominaciones que se te escapan.
- Mantiene `request_delay_seconds` en valores conservadores.

## 18. Resolucion De Problemas

### `configuration file not found`

No existe `config/config.yaml` o has pasado mal `--config`.

Solucion:

```bash
cp config/config.example.yaml config/config.yaml
```

### `watchlist must be a non-empty list`

La watchlist esta vacia o no tiene formato de lista.

Solucion: define al menos un elemento con `id`, `brand`, `model` y opcionalmente `aliases`.

### `ai.model must be configured when ai.enabled=true`

Has activado IA sin modelo.

Solucion: configura un modelo en `ai.model` o cambia `ai.enabled` a `false`.

### Faltan Variables SMTP

Si el email esta activado, `run` necesita `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD` y `NOTIFICATION_EMAIL`.

Solucion: rellena `.env` o cambia `notifications.email_enabled` a `false`.

### Hay Candidatos Pendientes Pero No Favoritos Nuevos

Comprueba si `ai.enabled=false`. En ese modo el sistema detecta candidatos, pero no confirma
favoritos nuevos automaticamente.

Solucion: activa IA con `ai.enabled=true`, `ai.model` y `OPENAI_API_KEY`, o revisa la base con los
comandos operativos disponibles.

### No Llegan Emails

Pasos:

1. Ejecuta `python -m app --config config/config.yaml status`.
2. Comprueba `events_failed` y `events_pending`.
3. Verifica credenciales SMTP en `.env`.
4. Ejecuta `python -m app retry-notifications`.

### El Foro Cambia Y `debug-listing` No Devuelve Temas

Puede haber cambiado la estructura HTML de la fuente o existir un problema temporal de red.

Pasos:

1. Ejecuta `python -m app debug-listing`.
2. Revisa conectividad de la maquina.
3. Evita aumentar agresivamente frecuencia o concurrencia.
4. Actualiza el parser si el HTML publico ha cambiado.

## 19. Seguridad Y Privacidad

- No pongas secretos en `config/config.yaml`.
- No subas `.env`, `data/monitor.db` ni backups a repositorios publicos.
- La aplicacion no guarda cookies ni credenciales del foro.
- La base guarda metadatos, hashes, favoritos, historicos y eventos; no necesita conservar HTML
  bruto ni texto completo de posts para operar.
- Usa un `user_agent` identificable y pausas razonables.

## 20. Referencia Rapida

Local:

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

Docker:

```bash
docker compose run --rm forum-scraper bootstrap
docker compose run --rm forum-scraper run
docker compose run --rm forum-scraper status
docker compose run --rm forum-scraper retry-notifications
docker compose run --rm forum-scraper backup
```

