# TASK-002 - Configuracion Y Modelos De Dominio

Estado: `DONE`  
SPEC maestra: [../forum_scraper.md](../forum_scraper.md)  
Documento maestro: [../forum_scraper_tasks.md](../forum_scraper_tasks.md)

## Objetivo

Implementar carga validada de configuracion YAML/env y modelos de dominio compartidos.

## Alcance Incluido

- `config/config.example.yaml`.
- `src/app/config.py`.
- `src/app/models.py`.
- Enums de eventos, disponibilidad y tipos de listing.
- Enum/estado de candidato pendiente, clasificado y descartado.
- Config de notificaciones por tipo de evento.
- Fechas internas en UTC.

## Alcance Excluido

- SQLAlchemy.
- Cliente HTTP.
- OpenAI real.

## Guardrails Especificos

- No crear tablas, migraciones, repositorios ni dependencias hacia SQLAlchemy.
- No realizar llamadas de red ni inicializar clientes externos.
- No hardcodear marcas, modelos, categorias de interes ni valores reales de la watchlist fuera de ejemplos neutros.
- No guardar, imprimir ni incluir secrets en YAML, tests, logs o fixtures; solo nombres de variables de entorno.
- No definir comportamiento de negocio avanzado que pertenezca a discovery, favoritos, eventos o notificaciones.

## Dependencias

- TASK-001.

## Checklist Operativa

- Usar [forum-task-agent](../skills/forum-task-agent/SKILL.md) como checklist unico.
- No simular handoffs entre roles salvo peticion explicita.

## Archivos Permitidos O Esperados

- `config/config.example.yaml`
- `src/app/config.py`
- `src/app/models.py`
- `tests/`
- `SPECs/forum_scraper_tasks.md`

## Requisitos Funcionales

- Validar watchlist con `id`, `brand`, `model`, `aliases`.
- Permitir `ai.model = null`.
- Leer secrets solo desde entorno cuando aplique.
- Rechazar configuracion invalida con errores claros.
- Usar `PyYAML` para cargar `config/config.yaml`.

## Requisitos De Tests

- Config valida carga correctamente.
- Config invalida falla.
- `notify_event_types` filtra enums conocidos.
- `ai.enabled=false` es representable.

## Criterios De Aceptacion

- Los modelos son reutilizables por tareas posteriores.
- No hay secrets en ejemplos.

## Verificacion Esperada

```bash
pytest
```

## Verificacion Ejecutada

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Resultado: ambos comandos pasan.

## Commit Sugerido

```text
feat: add config and domain models
```

## Rama Y PR

- Rama sugerida: `TASK-002_config_and_domain_models`
- PR: https://github.com/alvarofergil/forum_scraper/pull/3
- Estado al abrir PR: `REVIEW`
- Estado tras merge a `main`: `DONE`
