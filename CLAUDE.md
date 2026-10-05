# Pipeline de investigación: YouTube → NotebookLM

Este repositorio contiene dos habilidades de proyecto en `.claude/skills/`:

- `yt-research`: busca videos de YouTube con yt-dlp y extrae título, vistas, autor,
  duración y URL.
- `notebooklm`: crea cuadernos de NotebookLM, sube URLs como fuentes, pide análisis y
  genera entregables (infografías, presentaciones, tarjetas de estudio…) con
  notebooklm-py.

Dependencias en `.venv` (se crean con `scripts/setup.sh`). Ejecuta todo desde la raíz del
repositorio.

## Regla: sin tema no hay investigación

Si el usuario pide una investigación sin indicar el tema (por ejemplo, deja literal
`[TU TEMA]` o no menciona ninguno), **pregúntale qué tema quiere investigar y espera su
respuesta** antes de ejecutar cualquier paso.

## Pipeline completo

Cuando el usuario pida "usa yt-research para encontrar N videos sobre X, envíalos a
NotebookLM, dame el análisis y crea una infografía…":

1. `slug` = tema en minúsculas con guiones; `mkdir -p research/<slug>`.
2. **yt-research**: busca los videos (para "recientes y en tendencia":
   `--period month --sort trending`), guarda `research/<slug>/videos.json` y muestra la
   tabla.
3. **notebooklm**: comprueba la sesión (`auth check --test --json`); si no hay sesión,
   detente y pide al usuario que ejecute `notebooklm login` en otra terminal.
4. **notebooklm**: `nlm_ingest.py` crea el cuaderno "Investigación: <tema>" con los
   videos; informa cuántas fuentes quedaron listas.
5. **notebooklm**: pide el análisis de hallazgos principales con `ask`, muéstralo y
   guárdalo en `research/<slug>/analisis.md`.
6. **notebooklm**: genera el entregable pedido usando el análisis como descripción
   (infografía manuscrita / pizarrón → `--style sketch-note`), espera y descárgalo en
   `research/<slug>/`.
7. Resume: videos encontrados, fuentes listas/fallidas, análisis, rutas de los archivos y
   enlace al cuaderno.

Mantén al usuario informado entre pasos con una línea breve; la generación puede tardar
varios minutos.
