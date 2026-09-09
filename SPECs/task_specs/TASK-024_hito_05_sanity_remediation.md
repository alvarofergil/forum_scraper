# TASK-024 - Correctivo Tecnico Post HITO-05

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Endurecer los contratos operativos entregados en HITO-05 antes de preparar Docker/Raspberry y el cierre v1. La tarea debe corregir desviaciones detectadas en el sanity check post HITO-05: backups por defecto sobrescribibles, `run` sin entrega de emails configurados, y eventos no notificables que permanecen indefinidamente como pendientes operativos.

## Contexto Minimo Para Agentes

Leer siempre:

- `SPECs/AGENT_START.md`.
- La fila de `TASK-024` en `SPECs/forum_scraper_tasks.md`.
- Esta sub-SPEC completa.
- `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.

Leer tambien:

- `SPECs/task_specs/TASK-015_email_notifications.md`.
- `SPECs/task_specs/TASK-017_operational_cli.md`.
- `SPECs/task_specs/TASK-023_hito_04_sanity_remediation.md`.
- Fragmentos de `SPECs/forum_scraper.md`:
  - `#12-run-incremental`.
  - `#19-eventos`.
  - `#20-notificaciones`.
  - `#25-cli`.
  - `#26-logs`.
  - `#28-tests-obligatorios`.
  - `#30-definition-of-done-v1`.
- Codigo afectado:
  - `src/app/cli.py`.
  - `src/notifications/email.py`.
  - `src/storage/operational.py`.
  - tests relacionados bajo `tests/`.

## Observaciones Del Sanity Check

1. `python -m app backup` usa por defecto `backups/monitor.db`, mientras la SPEC maestra exige `monitor-YYYYMMDD-HHMMSS.db`. Esto puede sobrescribir backups previos y reduce la garantia de portabilidad/recuperacion de v1.
2. `python -m app run` genera eventos durante discovery/favorites check, pero no intenta entregar emails aunque `notifications.email_enabled=true`. La unica entrega SMTP disponible queda en `retry-notifications`, de modo que una operacion diaria basada solo en `run` detecta eventos pero no notifica.
3. Los eventos cuyo tipo no esta en `notifications.notify_event_types` se cuentan como `skipped`, pero permanecen con `notification_status=PENDING`. Esto hace que `status` y cada retry futuro sigan mostrando trabajo pendiente que por configuracion nunca debe enviarse.
4. La ayuda/README de CLI no documenta la semantica exacta de backup timestamped ni la relacion esperada entre `run`, envio automatico y `retry-notifications`.

## Alcance Incluido

- Cambiar el destino por defecto de `backup` para crear `backups/monitor-YYYYMMDD-HHMMSS.db` cuando el usuario no indique ruta explicita.
- Mantener la posibilidad de pasar una ruta explicita a `backup`; en ese caso debe respetarse exactamente esa ruta y seguir usando la API nativa `sqlite3.Connection.backup`.
- Integrar entrega de emails pendientes al final de `python -m app run` cuando:
  - `notifications.email_enabled=true`;
  - existan variables SMTP requeridas en entorno;
  - haya eventos pendientes/fallidos accionables segun la politica definida abajo.
- Definir una salida CLI clara para `run` que incluya resumen de notificaciones si se intenta el envio, sin ocultar discovery/favorites.
- Mantener `retry-notifications` como comando manual para reintentar `PENDING` y `FAILED`.
- Resolver la semantica de eventos no configurados:
  - opcion preferida sin migracion: no tratarlos como pendientes accionables en `status`; `EmailNotificationService` puede seguir contandolos como `skipped`, pero `read_status()` debe separar `events_pending` accionables de eventos pendientes no notificables solo si dispone de configuracion;
  - si se decide persistir un estado nuevo como `SKIPPED`, la tarea debe incluir migracion Alembic, constraints, tests de upgrade y actualizacion de enums; esta opcion requiere justificar el cambio en esta sub-SPEC antes de implementarlo.
- Actualizar README o ayuda integrada para documentar:
  - que `run` hace una pasada completa y, si email esta activo, intenta entregar notificaciones;
  - que `retry-notifications` es para recuperacion manual;
  - que `backup` sin argumento crea un archivo timestamped.
- Anadir tests unitarios sin red ni SMTP real.

## Alcance Excluido

- No implementar scheduler, daemon, cron, systemd ni Docker; pertenecen a HITO-06.
- No cambiar parsers HTML, politica de scraping, fixtures reales ni acceso a armas.es.
- No cambiar el modelo OpenAI, prompts, umbrales ni semantica de clasificacion.
- No introducir servicios externos adicionales, colas, workers, Redis, PostgreSQL ni API HTTP.
- No almacenar credenciales SMTP en YAML, SQLite, logs, tests o fixtures.
- No enviar emails HTML ni adjuntos.
- No borrar eventos historicos, favoritos, candidatos ni app_state existentes.
- No cambiar tipos de eventos salvo que se elija explicitamente la opcion con estado `SKIPPED` y se cubra con migracion.

## Guardrails Especificos

- Tests no deben realizar llamadas SMTP reales; usar `smtp_factory` fake o monkeypatch.
- Tests no deben realizar llamadas de red; conservar el bloqueo global de red.
- Si faltan variables SMTP durante `run` con `email_enabled=true`, el comando no debe marcar eventos como enviados ni perderlos. Debe fallar de forma explicita o registrar/resumir fallo recuperable; elegir una semantica y cubrirla con tests.
- `run` no debe devolver codigo `0` fingiendo notificaciones enviadas cuando no pudo cargar entorno SMTP. Si se decide mantener codigo `0` por discovery exitoso, la salida debe incluir `notifications_failed` o equivalente.
- No avanzar ni modificar checkpoints de discovery/favorites por el resultado de notificaciones.
- El backup timestamped debe usar hora UTC o local de forma consistente y testeable. Preferencia: UTC en formato compacto `YYYYMMDD-HHMMSS`.
- No sobrescribir un backup existente por defecto. Si una colision de timestamp ocurre, crear sufijo determinista (`-1`, `-2`, etc.) o usar precision suficiente; cubrir con test.
- No incluir payload completo, secretos ni texto completo de posts en salidas `status`, `run`, `retry-notifications` o `inspect`.
- Si se necesita tocar otro archivo fuera de los permitidos, actualizar primero esta sub-SPEC y el documento maestro explicando el motivo.

## Dependencias

- `TASK-015`.
- `TASK-017`.
- `TASK-023`.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `src/app/cli.py`
- `src/notifications/email.py`
- `src/storage/operational.py`
- `src/app/models.py` solo si se introduce un estado persistido nuevo para notificaciones.
- `src/storage/orm.py` solo si se introduce un estado persistido nuevo para notificaciones.
- `alembic/versions/` solo si se introduce un estado persistido nuevo para notificaciones.
- `tests/test_cli.py`
- `tests/test_operational_cli.py`
- `tests/test_email_notifications.py`
- `README.md`
- `SPECs/task_specs/TASK-024_hito_05_sanity_remediation.md`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

1. `python -m app backup` sin argumento debe crear un backup nuevo bajo `backups/` con nombre `monitor-YYYYMMDD-HHMMSS.db`.
2. `python -m app backup <ruta>` debe crear backup en `<ruta>` y no aplicar renombrado automatico salvo para crear directorios padres.
3. El backup debe seguir usando la API `sqlite3.Connection.backup`; no copiar el archivo SQLite directamente.
4. `python -m app run` debe ejecutar discovery y favorites check igual que TASK-023.
5. Si `notifications.email_enabled=false`, `run` no debe cargar secrets SMTP ni intentar SMTP.
6. Si `notifications.email_enabled=true`, `run` debe intentar enviar/reintentar eventos accionables al final de la pasada usando `EmailNotificationService`.
7. Si el envio falla por SMTP, los eventos deben quedar `FAILED` o `PENDING` reintentables conforme a TASK-015, y la salida de `run` debe mostrar `notifications_sent`, `notifications_failed` y `notifications_skipped` o nombres equivalentes.
8. `retry-notifications` debe conservar su comportamiento y seguir procesando `PENDING` y `FAILED`.
9. Los eventos no incluidos en `notifications.notify_event_types` no deben mantener indefinidamente ruido operativo en `status` como pendientes accionables. La solucion debe ser explicita, testeada y compatible con auditoria.
10. `status` debe seguir sin requerir `config/config.yaml` salvo que se decida mostrar contadores configurados; si requiere config, debe conservar una ruta ergonomica para inspeccionar una DB sin secrets.
11. Las salidas CLI no deben imprimir secrets, payloads completos ni texto completo de posts.

## Requisitos De Tests

Implementar tests antes o junto al cambio. Minimo:

- Test de `backup` sin argumento: con reloj inyectado o monkeypatch, crea `backups/monitor-YYYYMMDD-HHMMSS.db` y no `backups/monitor.db`.
- Test de dos backups por defecto en el mismo segundo: no sobrescribe el primero.
- Test de `backup <ruta>`: respeta ruta explicita y crea una copia SQLite consistente.
- Test de `run` con `notifications.email_enabled=false`: no llama a `load_email_environment` ni a SMTP.
- Test de `run` con email activo y SMTP fake exitoso: emite resumen de notificaciones y marca eventos enviados.
- Test de `run` con fallo SMTP: deja eventos reintentables y salida diagnostica el fallo.
- Test de `retry-notifications` sigue procesando `PENDING` y `FAILED`.
- Test de evento no incluido en `notify_event_types`: no se envia y no queda contado como pendiente accionable en `status`, o queda en estado persistido `SKIPPED` si se eligio esa opcion.
- Test de seguridad de salidas: `run`, `retry-notifications`, `status` e `inspect` no imprimen `SMTP_PASSWORD`, valores de password fake, HTML completo ni texto completo de posts.
- Ejecutar toda la suite sin red.

## Criterios De Aceptacion

- La suite completa pasa con `.venv/bin/pytest`.
- `.venv/bin/ruff check .` pasa.
- No hay llamadas de red ni SMTP real en tests.
- Backup por defecto no sobrescribe archivos existentes.
- `run` conserva una unica pasada finita y termina sin scheduler.
- Emails configurados se intentan entregar durante `run` o queda documentado y testeado un motivo explicito para no hacerlo; no debe quedar una ambiguedad operativa.
- Eventos no notificables no aparecen como deuda operacional pendiente accionable para siempre.
- README o ayuda CLI documenta el comportamiento operativo final.
- No se introducen secrets, HTML bruto ni texto completo de posts en persistencia, logs o salidas.
- La tarea deja una nota breve de verificacion ejecutada en esta sub-SPEC antes de pasar a `REVIEW`.

## Verificacion Esperada

```bash
.venv/bin/pytest tests/test_cli.py tests/test_operational_cli.py tests/test_email_notifications.py
.venv/bin/pytest
.venv/bin/ruff check .
git diff --check
```

## Verificacion Ejecutada

Ejecutada en rama `TASK-024_hito_05_sanity_remediation`:

```bash
.venv/bin/pytest tests/test_cli.py tests/test_operational_cli.py tests/test_email_notifications.py
# 20 passed

.venv/bin/pytest
# 166 passed

.venv/bin/ruff check .
# All checks passed!

git diff --check
# sin salida
```

## Commit Sugerido

```text
fix: harden hito 05 operational contracts
```

## Rama Y PR

- Rama: `TASK-024_hito_05_sanity_remediation`
- PR: https://github.com/alvarofergil/forum_scraper/pull/23
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
