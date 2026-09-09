---
name: forum-task-agent
description: "Checklist unico para ejecutar tareas del Forum Scraper con bajo consumo de contexto: coordinacion, arquitectura, desarrollo, QA y release bajo demanda."
metadata:
  short-description: Forum Scraper task checklist
---

# Forum Scraper Task Agent

Usar esta skill para cualquier tarea del proyecto. Los antiguos roles se aplican como fases internas breves, no como subagentes ni handoffs escritos.

## Contexto Minimo

1. `SPECs/AGENT_START.md`.
2. Fila activa en `SPECs/forum_scraper_tasks.md`.
3. Sub-SPEC activa en `SPECs/task_specs/`.
4. Codigo, tests y docs afectados por `Archivos Permitidos O Esperados`.
5. Fragmentos de `SPECs/forum_scraper.md` solo si falta una regla global concreta.

## Checklist Interno

- PM: confirmar objetivo, estado, dependencias, alcance y guardrails.
- Arquitectura: comprobar limites entre `sources`, `discovery`, `classification`, `favorites`, `events`, `notifications`, `storage` y `app`.
- Desarrollo: implementar el cambio minimo mantenible, con tipos claros y sin hardcodear configuracion de usuario.
- QA: cubrir requisitos con tests deterministicos, sin red y con fakes para HTTP, OpenAI, SMTP, reloj y filesystem cuando aplique.
- Release: solo si se va a cerrar PR; revisar diff, verificacion, commit, push, PR y estado documental.

## Invariantes

- Sin frontend, API web, scheduler interno, colas externas, Redis, PostgreSQL ni mecanismos de evasion en v1.
- SQLite es la unica fuente de estado operativo.
- La watchlist vive en configuracion, no en codigo Python.
- El acceso a armas.es debe ser secuencial, minimo y respetuoso.
- No persistir secrets, cookies, HTML bruto ni texto completo de posts.
- OpenAI y SMTP deben ir detras de adaptadores/fakes en tests.
- El proyecto debe seguir siendo portable PC -> Raspberry mediante `config/`, `data/`, `backups/` y `.env`.

## Flujo Por Defecto

1. Leer contexto minimo.
2. Inspeccionar archivos afectados con `rg` y lecturas por rango.
3. Escribir o ajustar tests focalizados cuando cambie comportamiento.
4. Implementar.
5. Ejecutar tests focalizados y la verificacion esperada si el entorno lo permite.
6. Actualizar solo los artifacts necesarios.
7. Informar resultado, evidencia y riesgos.

## Release Bajo Demanda

No hacer commit, push, PR ni merge salvo peticion explicita. Cuando se pida release:

- crear o usar rama de tarea desde `main` actualizado;
- confirmar que el diff contiene solo archivos de la tarea;
- ejecutar verificacion requerida;
- hacer un commit con el mensaje sugerido o uno equivalente;
- abrir PR a `main`;
- marcar `REVIEW` al abrir PR y `DONE` solo tras merge.
