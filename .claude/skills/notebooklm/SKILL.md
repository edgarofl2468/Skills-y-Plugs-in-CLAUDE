---
name: notebooklm
description: Opera NotebookLM (Gemini Notebook) con notebooklm-py: crear cuadernos, subir URLs de YouTube u otras fuentes, pedir análisis con citas y generar entregables (infografías, presentaciones, tarjetas de estudio, cuestionarios, informes, audio, video, mapas mentales) y descargarlos. Úsala cuando el usuario mencione NotebookLM o Gemini Notebook, quiera enviar videos o enlaces a un cuaderno, o pida una infografía, presentación o flashcards a partir de fuentes.
---

# notebooklm: cuadernos, fuentes, análisis y entregables

Herramientas (ejecutar desde la raíz del repositorio):

- CLI: `.venv/bin/notebooklm` (en Windows: `.venv\Scripts\notebooklm`)
- Carga masiva de URLs: `.venv/bin/python .claude/skills/notebooklm/scripts/nlm_ingest.py`
- Referencia completa del paquete (invariantes, errores, Python API): `reference.md`
  en esta carpeta. Ante cualquier duda de opciones, consulta
  `.venv/bin/notebooklm <comando> --help` en vez de adivinar.

Si `.venv` no existe, ejecuta `scripts/setup.sh`.

## 1. Comprobar la sesión (siempre primero)

```bash
.venv/bin/notebooklm auth check --test --json
```

Continúa solo si `.status == "ok"` y `.checks.token_fetch == true`. Si falla, **detente** y
pide al usuario que, en una terminal aparte (el login abre un navegador), ejecute:

```bash
source .venv/bin/activate && notebooklm login   # Mac / Linux
.venv\Scripts\notebooklm login                  # Windows (PowerShell)
```

y que te avise al terminar. No ejecutes `notebooklm login` tú mismo. Nunca muestres,
copies ni subas al repositorio `~/.notebooklm/` (`storage_state.json`,
`master_token.json`): son credenciales de la cuenta de Google.

## 2. Crear un cuaderno y subir videos de YouTube

Desde el JSON de la habilidad `yt-research` (crea el cuaderno, sube todas las URLs y
espera a que cada fuente esté lista):

```bash
.venv/bin/python .claude/skills/notebooklm/scripts/nlm_ingest.py \
  --videos research/<slug>/videos.json \
  --title "Investigación: <tema>" \
  -o research/<slug>/notebook.json
```

- Devuelve `notebook_id`, `notebook_url`, `ready_source_ids` y, por fuente, `status` y
  `error`. Guarda el `notebook_id`: todos los comandos siguientes lo llevan con `-n`.
- Para añadir a un cuaderno existente usa `--notebook <id>` en lugar de `--title`.
  URLs sueltas: `--url <url>` (repetible).
- Algunos videos pueden fallar (sin transcripción, privados, límites de la cuenta).
  Informa cuántos quedaron listos y cuáles fallaron; sigue con los listos. Si
  `ready_count` es 0, detente y muestra los errores.

Operaciones sueltas con el CLI:

| Objetivo | Comando |
|---|---|
| Listar cuadernos | `notebooklm list --json` |
| Crear cuaderno | `notebooklm create "Título" --json` → `.notebook.id` |
| Añadir una fuente | `notebooklm source add <url> -n <nb> --json` → `.source.id` |
| Esperar una fuente | `notebooklm source wait <src> -n <nb> --timeout 600` |
| Ver fuentes | `notebooklm source list -n <nb> --json` |

## 3. Pedir el análisis

```bash
.venv/bin/notebooklm ask "PREGUNTA" -n <nb> --json
```

Usa `.answer` (incluye citas `[1]`, `[2]`… a las fuentes). Para "hallazgos principales",
una buena pregunta (en el idioma del usuario) es:

> Analiza todas las fuentes y resume los hallazgos principales: temas recurrentes,
> afirmaciones o datos clave, puntos de consenso y desacuerdo entre los creadores,
> tendencias emergentes y preguntas abiertas. Organízalo en secciones con viñetas y
> cita las fuentes.

Muestra el análisis al usuario y guárdalo en `research/<slug>/analisis.md`. Para
preguntas largas usa `--prompt-file <archivo>`. No uses `ask --new` sin confirmación
(borra la conversación del cuaderno).

## 4. Generar entregables

Flujo para cualquier tipo: generar → esperar → descargar, siempre con IDs explícitos.

```bash
.venv/bin/notebooklm generate <tipo> [opciones] -n <nb> --json      # -> .task_id
.venv/bin/notebooklm artifact wait <task_id> -n <nb> --timeout 1200
.venv/bin/notebooklm download <tipo> research/<slug>/<archivo> -a <task_id> -n <nb>
```

| Entregable | `<tipo>` | Opciones útiles | Descarga |
|---|---|---|---|
| Infografía | `infographic` | `--style`, `--orientation landscape\|portrait\|square`, `--detail concise\|standard\|detailed`, `--language es` | `.png` |
| Presentación | `slide-deck` | `--format detailed\|presenter`, `--length default\|short`, `--language es` | `.pdf` o `--format pptx` |
| Tarjetas de estudio | `flashcards` | `--quantity fewer\|standard\|more`, `--difficulty easy\|medium\|hard` | `--format json\|markdown\|html` |
| Cuestionario | `quiz` | `--quantity`, `--difficulty` | `--format json\|markdown\|html` |
| Informe | `report` | `--format briefing-doc\|study-guide\|blog-post\|custom`, `--language es` | `.md` |
| Podcast | `audio` | `--format deep-dive\|brief\|critique\|debate`, `--length`, `--language es` | `.mp3` |
| Video | `video` | `--format explainer\|brief`, `--style whiteboard\|classic\|…`, `--language es` | `.mp4` |
| Mapa mental | `mind-map` | `--kind interactive\|note-backed` (no necesita `artifact wait`) | `.json` |
| Tabla de datos | `data-table` | `--language es` | `.csv` |

Estilos de infografía: `auto`, `sketch-note`, `professional`, `bento-grid`, `editorial`,
`instructional`, `bricks`, `clay`, `anime`, `kawaii`, `scientific`.
**"Manuscrito", "a mano", "pizarrón" o "pizarra" → `--style sketch-note`.**

Para que el entregable represente el análisis, pásale la síntesis como descripción
(escríbela en un archivo y usa `--prompt-file`), por ejemplo:

```bash
.venv/bin/notebooklm generate infographic --prompt-file research/<slug>/prompt_infografia.txt \
  --style sketch-note --orientation landscape --detail standard --language es -n <nb> --json
```

donde el archivo dice algo como: "Infografía en estilo manuscrito / pizarrón, dibujada a
mano, que represente estos hallazgos principales: …(resumen del análisis)…".

Notas:

- Usa `--language es` (o el idioma del usuario) cuando el comando lo admita.
- La generación tarda minutos y Google la limita; si hay error de límite, informa el
  `task_id` y no reintentes en bucle. `--retry 2` es aceptable en el primer intento.
- Descarga solo cuando `artifact wait` termine con éxito (código 0 / `completed`).
- Al terminar, da al usuario la ruta del archivo y el enlace al cuaderno
  (`notebook_url`).

## Autorización

Pedir explícitamente un entregable autoriza generarlo, esperar y descargarlo. Pide
confirmación antes de cualquier acción destructiva o de cuenta: borrar cuadernos,
fuentes o artefactos, `ask --new`, `logout`, `language set`, compartir.
