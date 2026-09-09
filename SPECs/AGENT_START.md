# Arranque Compacto Para Agentes - Forum Scraper

Este archivo es la unica autoridad de arranque. Su objetivo es ahorrar contexto sin perder trazabilidad, guardrails ni calidad.

## Regla Principal

Usar un unico agente por defecto. No simular handoffs entre PM, Arquitecto, Developer, QA y Release Manager. Esos roles son checklist interno, no conversaciones separadas, salvo que el usuario pida agentes reales o una revision independiente.

Leer solo el contexto minimo que permite actuar con seguridad. No leer documentos completos si basta una fila, una seccion, una sub-SPEC o una busqueda dirigida con `rg`.

## Arranque Minimo

1. Identificar la tarea, hito o decision concreta.
2. Leer la fila activa en `SPECs/forum_scraper_tasks.md`.
3. Leer completa solo la sub-SPEC activa en `SPECs/task_specs/`.
4. Leer `SPECs/skills/forum-task-agent/SKILL.md` como checklist unico.
5. Leer codigo, tests y docs directamente afectados.
6. Leer fragmentos de `SPECs/forum_scraper.md` solo si la sub-SPEC no cubre un requisito global necesario.

## Cuándo Leer Mas

Leer `SPECs/forum_scraper.md` completa solo si:

- la tarea modifica alcance v1, arquitectura global o limites entre componentes;
- hay duda sobre legalidad, privacidad, coste, seguridad, retencion de datos o acceso externo;
- se modifica la fuente monitorizada, politica de scraping, persistencia transversal o portabilidad;
- la sub-SPEC activa contradice otro artefacto;
- el usuario pide una revision global del proyecto.

Leer sub-SPECs de dependencias solo cuando su contrato sea necesario para implementar o verificar la tarea activa. Para comprobar estados, basta la tabla maestra.

## Trabajo Sobre Codigo

- Respetar `Archivos Permitidos O Esperados`.
- Si hace falta tocar algo fuera del alcance, preguntar o actualizar la sub-SPEC antes.
- Implementar con tests focalizados primero y verificacion requerida al final.
- Mantener tests sin red salvo tarea que permita acceso externo controlado.
- No ejecutar flujo de release, commit, push o PR salvo peticion explicita del usuario o de la tarea activa.

## Git Y Estados

- El repo Git vive en la raiz del paquete `forum_scraper/`; `SPECs/` esta versionado dentro de ese repo.
- No hacer push directo a `main`.
- Usar rama propia para tareas con cambios de repo cuando se vaya a preparar PR.
- Usar `REVIEW` solo para PR abierto con tests verdes.
- No marcar `DONE` hasta que el PR este mergeado en `main`.
- No mezclar cambios de tareas distintas.

## Criterios De Parada

Parar y preguntar si aparece una decision no cubierta que afecte:

- alcance funcional;
- arquitectura;
- privacidad o datos persistidos;
- coste o uso de OpenAI/SMTP;
- legalidad o politica de acceso a armas.es;
- seguridad, secretos o credenciales;
- cambios fuera de la sub-SPEC activa.

## Salida Esperada

Responder breve y accionable: resultado, archivos cambiados, verificacion ejecutada y riesgos reales si existen.
