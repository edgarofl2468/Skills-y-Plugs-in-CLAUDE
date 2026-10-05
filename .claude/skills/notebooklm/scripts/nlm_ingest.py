#!/usr/bin/env python3
"""Create a NotebookLM notebook and load YouTube (or any) URLs as sources.

Reads the `videos.json` written by the yt-research skill (or URLs passed with
--url), creates a notebook (or reuses one with --notebook), adds every URL,
waits until each source is ready and prints a JSON summary with the IDs the
rest of the pipeline needs.

Examples:
    nlm_ingest.py --videos research/ia/videos.json --title "Investigación: IA"
    nlm_ingest.py --notebook <id> --url https://www.youtube.com/watch?v=abc123
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

try:
    from notebooklm import NotebookLMClient, NotebookLMError
except ImportError:  # pragma: no cover - exercised only without the dependency
    sys.exit(
        "notebooklm-py no está instalado. Ejecuta: scripts/setup.sh "
        "(o: pip install -r requirements.txt)"
    )


def load_urls(videos_path: str | None, urls: list[str]) -> list[dict[str, Any]]:
    """Return [{url, title}] from a yt-research JSON file plus explicit URLs, deduplicated."""
    items: list[dict[str, Any]] = []
    if videos_path:
        data = json.loads(Path(videos_path).read_text(encoding="utf-8"))
        videos = data["videos"] if isinstance(data, dict) else data
        items += [{"url": v["url"], "title": v.get("title")} for v in videos if v.get("url")]
    items += [{"url": u, "title": None} for u in urls]

    seen: set[str] = set()
    unique = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique


async def ingest(
    items: list[dict[str, Any]],
    title: str | None,
    notebook_id: str | None,
    timeout: float,
) -> dict[str, Any]:
    async with NotebookLMClient.from_storage() as client:
        if notebook_id:
            notebook = await client.notebooks.get(notebook_id)
        else:
            notebook = await client.notebooks.create(title)
        print(f"Cuaderno: {notebook.title} ({notebook.id})", file=sys.stderr)

        # Add sequentially: NotebookLM rate-limits bursts of source creation.
        results: list[dict[str, Any]] = []
        for i, item in enumerate(items, 1):
            row = {"url": item["url"], "title": item["title"], "id": None, "status": None}
            try:
                source = await client.sources.add_url(notebook.id, item["url"])
                row["id"] = source.id
                row["title"] = source.title or item["title"]
                print(f"[{i}/{len(items)}] añadida: {item['url']}", file=sys.stderr)
            except NotebookLMError as exc:
                row["status"] = "error"
                row["error"] = f"{type(exc).__name__}: {exc}"
                print(f"[{i}/{len(items)}] FALLÓ: {item['url']} -> {exc}", file=sys.stderr)
            results.append(row)

        pending = [r for r in results if r["id"]]
        print(f"Esperando a que {len(pending)} fuentes estén listas...", file=sys.stderr)
        outcomes = await asyncio.gather(
            *(client.sources.wait_until_ready(notebook.id, r["id"], timeout=timeout) for r in pending),
            return_exceptions=True,
        )
        for row, outcome in zip(pending, outcomes):
            if isinstance(outcome, BaseException):
                row["status"] = "error"
                row["error"] = f"{type(outcome).__name__}: {outcome}"
            else:
                row["status"] = "ready"
                row["title"] = outcome.title or row["title"]

    ready = [r for r in results if r["status"] == "ready"]
    return {
        "notebook_id": notebook.id,
        "notebook_title": notebook.title,
        "notebook_url": f"https://notebooklm.google.com/notebook/{notebook.id}",
        "ready_count": len(ready),
        "failed_count": len(results) - len(ready),
        "ready_source_ids": [r["id"] for r in ready],
        "sources": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Crea un cuaderno de NotebookLM y sube URLs (YouTube) como fuentes."
    )
    parser.add_argument("--videos", help="JSON generado por yt-research (videos.json)")
    parser.add_argument("--url", action="append", default=[], help="URL extra (repetible)")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--title", help="Título del cuaderno nuevo")
    target.add_argument("--notebook", help="ID de un cuaderno existente")
    parser.add_argument(
        "--timeout", type=float, default=600, help="Espera máxima por fuente, en segundos (600)"
    )
    parser.add_argument("-o", "--output", help="Guarda el resumen JSON en este archivo")
    args = parser.parse_args(argv)

    items = load_urls(args.videos, args.url)
    if not items:
        parser.error("no hay URLs: usa --videos y/o --url")

    try:
        summary = asyncio.run(ingest(items, args.title, args.notebook, args.timeout))
    except FileNotFoundError as exc:
        print(f"Sin sesión de NotebookLM: {exc}", file=sys.stderr)
        return 1
    except NotebookLMError as exc:
        print(
            f"Error de NotebookLM: {type(exc).__name__}: {exc}\n"
            "Comprueba la sesión con: notebooklm auth check --test --json",
            file=sys.stderr,
        )
        return 1

    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Resumen guardado en {args.output}", file=sys.stderr)
    print(text)
    return 0 if summary["ready_count"] else 1


if __name__ == "__main__":
    sys.exit(main())
