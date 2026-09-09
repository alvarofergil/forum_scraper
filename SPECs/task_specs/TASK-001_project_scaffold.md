# TASK-001 - Scaffold Python, Tooling Y Layout Limpio

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Crear la estructura base desplegable en la raiz del repo y preparar herramientas de desarrollo/test.

## Alcance Incluido

- Inicializar Git si no existe.
- Crear `pyproject.toml`.
- Crear layout `src/`, `tests/`, `docs/`, `config/`, `data/`, `backups/`.
- Configurar pytest y ruff.
- Crear paquetes Python vacios segun la arquitectura maestra.
- Mantener codigo de aplicacion en la raiz del repo.

## Alcance Excluido

- Scraping real.
- Base de datos.
- Docker funcional.
- Logica de negocio.

## Guardrails Especificos

- No implementar scraping, persistencia, matching, clasificacion, notificaciones ni CLI funcional fuera de un smoke import.
- No crear ni commitear `.venv`, caches, bases de datos, HTML, secrets ni artefactos generados.
- No modificar la arquitectura, el orden de tareas ni otras sub-SPECs salvo notas minimas de estado/verificacion de esta tarea.
- Si Git ya existe en la raiz del repo, no reinicializarlo ni ejecutar comandos destructivos.
- Cualquier dependencia nueva debe quedar declarada en `pyproject.toml`; no depender de paquetes instalados solo manualmente en el entorno local.

## Dependencias

- Ninguna.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `pyproject.toml`
- `src/`
- `tests/`
- `docs/`
- `config/`
- `data/.gitkeep`
- `backups/.gitkeep`
- `.gitignore`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- `pytest` debe descubrir tests.
- Los imports base deben funcionar desde `src`.
- No debe haber codigo de aplicacion fuera de la raiz del repo.
- `PyYAML` debe quedar declarado como dependencia runtime del proyecto.

## Requisitos De Tests

- Crear un smoke test minimo que importe el paquete principal.
- Ejecutar tests antes del commit.

## Criterios De Aceptacion

- `pytest` pasa.
- `ruff check` pasa si queda configurado.
- Git existe y el commit de la tarea queda creado.

## Verificacion Esperada

```bash
pytest
ruff check .
```

## Verificacion Ejecutada

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Resultado: ambos comandos pasan.

## Commit Sugerido

```text
chore: scaffold python project
```

## Rama Y PR

- Rama sugerida: `TASK-001_project_scaffold`
- PR: desde la rama de tarea hacia `main`
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
