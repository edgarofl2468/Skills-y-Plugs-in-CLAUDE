# Skills y Plugs-in para Claude Code

Pipeline de investigación automatizada **YouTube → NotebookLM** con dos habilidades de
proyecto para Claude Code:

| Habilidad | Qué hace | Basada en |
|---|---|---|
| `yt-research` | Busca videos por tema y extrae título, vistas, autor, duración, URL, fecha y vistas por día; ordena por relevancia, fecha, vistas o tendencia | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| `notebooklm` | Crea cuadernos, sube URLs de YouTube como fuentes, pide análisis con citas y genera infografías, presentaciones, tarjetas de estudio, cuestionarios, informes, audio y video | [notebooklm-py](https://github.com/teng-lin/notebooklm-py) (API no oficial de Teng Lin) |

## Instalación

Requiere Python 3.10+.

### Mac / Linux

```bash
git clone -b claude/sweet-meitner-alq9ba https://github.com/edgarofl2468/Skills-y-Plugs-in-CLAUDE
cd Skills-y-Plugs-in-CLAUDE
scripts/setup.sh            # crea .venv e instala yt-dlp y notebooklm-py[browser]
```

### Windows (PowerShell)

Escribe una línea a la vez y pulsa Enter después de cada una:

```powershell
cd $HOME\Documents
git clone -b claude/sweet-meitner-alq9ba https://github.com/edgarofl2468/Skills-y-Plugs-in-CLAUDE
cd Skills-y-Plugs-in-CLAUDE
python -m venv .venv
.venv\Scripts\python -m pip install -U -r requirements.txt
```

Si `python` no se reconoce, instala Python con `winget install Python.Python.3.12`,
cierra PowerShell, ábrelo de nuevo y repite desde `cd $HOME\Documents\Skills-y-Plugs-in-CLAUDE`.

## Autenticación con Google (una sola vez)

Abre **una terminal aparte** (el login abre un navegador) en la carpeta del repositorio:

```bash
source .venv/bin/activate        # Mac / Linux
notebooklm login                 # la primera vez descarga Chromium (~170 MB)
notebooklm auth check --test --json   # debe decir "status": "ok"
```

En Windows (PowerShell), sin activar nada:

```powershell
.venv\Scripts\notebooklm login
.venv\Scripts\notebooklm auth check --test --json
```

La sesión se guarda en `~/.notebooklm/` (fuera del repositorio). Son credenciales de tu
cuenta: no las compartas ni las subas.

## Uso

Abre Claude Code en la carpeta del repositorio y escribe, por ejemplo:

> Usa la habilidad yt-research para encontrar los 25 videos más recientes y tendencia
> sobre **inteligencia artificial en educación**. Una vez que tengamos esos videos,
> envíalos a NotebookLM usando la habilidad notebooklm. Dame su análisis de los
> hallazgos principales, luego pide a NotebookLM que cree una infografía en estilo
> manuscrito / pizarrón que represente ese análisis.

Si no indicas el tema, Claude te lo preguntará antes de empezar. Los resultados
(`videos.json`, `notebook.json`, `analisis.md`, la infografía) quedan en
`research/<tema>/`.

También puedes usar los scripts directamente:

```bash
.venv/bin/python .claude/skills/yt-research/scripts/yt_research.py "tema" \
  -n 25 --period month --sort trending --format table -o research/tema/videos.json

.venv/bin/python .claude/skills/notebooklm/scripts/nlm_ingest.py \
  --videos research/tema/videos.json --title "Investigación: tema"
```

## Sesiones en la nube (claude.ai/code)

Las dependencias se instalan solas al iniciar la sesión (hook `SessionStart` en
`.claude/settings.json`). Para que el pipeline funcione allí:

- La política de red del entorno debe permitir `www.youtube.com`, `youtube.com`,
  `notebooklm.google.com`, `accounts.google.com` y `*.googleapis.com`.
- No hay navegador para `notebooklm login`. Lo más sencillo es usar el pipeline en tu
  Claude Code local. Para servidores sin pantalla, notebooklm-py documenta la
  autenticación con *master token* (`notebooklm login --master-token`); ver
  [docs/installation.md](https://github.com/teng-lin/notebooklm-py/blob/main/docs/installation.md).

## Estructura

```
.claude/
  settings.json                         permisos de los comandos del pipeline + hook de instalación
  skills/yt-research/SKILL.md           instrucciones de la habilidad
  skills/yt-research/scripts/yt_research.py
  skills/notebooklm/SKILL.md            flujo: sesión → cuaderno → análisis → entregables
  skills/notebooklm/reference.md        referencia oficial de notebooklm-py 0.8.4 (MIT)
  skills/notebooklm/scripts/nlm_ingest.py
CLAUDE.md                               pipeline completo y regla de "pregunta el tema"
requirements.txt
scripts/setup.sh
```

> notebooklm-py usa APIs no documentadas de Google: pueden cambiar sin aviso y la
> generación de contenido tiene límites de uso.
