# TASK-018 - Docker, Raspberry Readiness Y README

Estado: `REVIEW`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Hacer la aplicacion portable con Docker y documentar despliegue PC -> Raspberry.

## Contexto Minimo Para Agentes

- Leer `SPECs/AGENT_START.md`, esta sub-SPEC y la fila de `TASK-018` en `SPECs/forum_scraper_tasks.md`.
- Leer sub-SPECs de dependencias solo si hace falta aclarar contratos de CLI operativa, configuracion o datos persistidos.
- Leer fragmentos de `SPECs/forum_scraper.md` solo para reglas globales de portabilidad, despliegue, secrets, GitHub Flow o TDD que no esten claras aqui.
- Usar la checklist unica `SPECs/skills/forum-task-agent/SKILL.md`; no simular handoffs entre roles.

## Alcance Incluido

- `Dockerfile` multiarch-friendly.
- `docker-compose.yml`.
- `.env.example`.
- Volumenes `data`, `backups`, `config`.
- README operativo.
- Documentacion de migracion.

## Alcance Excluido

- Publicar imagen remota.
- Scheduler systemd real instalado en host.

## Guardrails Especificos

- No publicar imagenes en registries remotos ni requerir cuentas externas.
- No instalar servicios en el host ni modificar systemd/cron de la maquina del usuario.
- No incluir secrets en `Dockerfile`, `docker-compose.yml`, README ni `.env.example`.
- No cambiar la logica de negocio para adaptarla a Docker; solo empaquetado, configuracion y documentacion.
- No usar volumenes que rompan la portabilidad PC -> Raspberry definida por `config/`, `data/`, `backups/` y `.env`.
- No asumir arquitectura unica; mantener compatibilidad con `linux/amd64` y `linux/arm64`.

## Dependencias

- TASK-017.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `docs/`
- `tests/test_deployment_artifacts.py`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- `docker compose build` funciona desde la raiz del repo.
- Persistencia en volumenes locales.
- Compatible con `linux/amd64` y `linux/arm64`.

## Requisitos De Tests

- Tests unitarios siguen pasando.
- Build Docker validado si el entorno lo permite.

## Criterios De Aceptacion

- README explica configuracion, ejecucion, backup y migracion PC -> Raspberry.

## Verificacion Esperada

```bash
pytest
docker compose build
```

## Commit Sugerido

```text
feat: add portable docker deployment
```

## Rama Y PR

- Rama sugerida: `TASK-018_docker_raspberry`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
