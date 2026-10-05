---
name: yt-research
description: Busca videos de YouTube sobre un tema con yt-dlp y extrae sus metadatos (título, vistas, autor, duración, URL, fecha aproximada y vistas por día). Úsala cuando el usuario pida investigar, encontrar o listar videos de YouTube sobre un tema, incluidos "los más recientes", "en tendencia" o "los más vistos", o cuando haga falta una lista de URLs de YouTube para enviar a NotebookLM.
---

# yt-research: investigación de YouTube con yt-dlp

## Antes de empezar: el tema es obligatorio

Si el usuario pide una investigación sin decir el tema (por ejemplo, deja literal
`[TU TEMA]`, `[tema]`, `<tema>` o simplemente no lo menciona), **no ejecutes nada**:
pregúntale qué tema quiere investigar y espera su respuesta antes de continuar.

## Ejecutar la búsqueda

El script vive junto a este archivo. Usa el Python del entorno virtual del proyecto
(`.venv/bin/python`); si no existe, ejecuta primero `scripts/setup.sh` desde la raíz del
repositorio.

```bash
.venv/bin/python .claude/skills/yt-research/scripts/yt_research.py "TEMA" \
  -n 25 --period month --sort trending \
  -o research/<slug-del-tema>/videos.json --format table
```

- `-o` guarda el JSON completo (lo necesita la habilidad `notebooklm`); `--format table`
  imprime una tabla Markdown para mostrar al usuario. Crea la carpeta antes
  (`mkdir -p research/<slug>`).
- Sale con código 1 si no hay resultados o si yt-dlp falla; informa el error tal cual.

### Cómo traducir la petición del usuario a opciones

| El usuario dice | Opciones |
|---|---|
| "más recientes y en tendencia" | `--period month --sort trending` (si dice "esta semana": `--period week`) |
| "más recientes" / "lo último" | `--period week --sort date` |
| "más vistos" / "populares" | `--sort views` (añade `--period` si menciona un rango de tiempo) |
| sin preferencia | `--sort relevance` |
| "videos largos", "sin shorts" | `--min-duration 240` (segundos) |
| necesita fechas exactas, likes o descripción | añade `--full` (una petición por video, más lento) |

`trending` ordena por vistas por día desde la publicación. Las fechas de la búsqueda son
aproximadas (vienen de etiquetas como "hace 3 días"); `--full` las vuelve exactas.

## Salida

Cada video del JSON (`.videos[]`) tiene:

| Campo | Contenido |
|---|---|
| `title` | Título |
| `views` | Vistas (entero) |
| `author` | Canal |
| `duration` / `duration_seconds` | Duración `m:ss` / en segundos |
| `url` | `https://www.youtube.com/watch?v=<id>` |
| `upload_date` | Fecha `YYYY-MM-DD` (aproximada sin `--full`) |
| `views_per_day` | Métrica de tendencia |
| `channel_url`, `id` | Extras |

Muestra al usuario la tabla (título, autor, vistas, duración, URL) y di cuántos videos
se encontraron. Si hay menos de los pedidos, dilo; no inventes videos.

## Para encadenar con NotebookLM

Pasa el archivo `videos.json` a la habilidad `notebooklm`
(`.claude/skills/notebooklm/scripts/nlm_ingest.py --videos research/<slug>/videos.json`).
Para solo las URLs: `--format urls`.
