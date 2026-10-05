#!/usr/bin/env python3
"""Search YouTube with yt-dlp and return video metadata.

Extracts title, views, author (channel), duration and URL for every video that
matches a search query, optionally limited to a recent upload window and
ranked by relevance, recency, views or "trending" (views per day).

Examples:
    yt_research.py "inteligencia artificial" -n 25
    yt_research.py "claude code" -n 25 --period month --sort trending -o videos.json
    yt_research.py "notebooklm" --format urls
"""

from __future__ import annotations

import argparse
import base64
import calendar
import json
import sys
import time
import urllib.parse
from typing import Any

try:
    import yt_dlp
except ImportError:  # pragma: no cover - exercised only without the dependency
    sys.exit(
        "yt-dlp no está instalado. Ejecuta: scripts/setup.sh "
        "(o: pip install -r requirements.txt)"
    )

# YouTube encodes search filters in the `sp` URL parameter as a base64 protobuf:
#   field 1  -> sort order
#   field 2  -> filter message { field 1: upload date, field 2: result type }
# These values match the ones the YouTube web UI emits.
SORT_CODES = {"relevance": 0, "rating": 1, "date": 2, "views": 3}
PERIOD_CODES = {"any": 0, "hour": 1, "today": 2, "week": 3, "month": 4, "year": 5}
TYPE_VIDEO = 1

# Sort orders we ask YouTube for; "trending" is computed locally from views/day.
SERVER_SORT = {"relevance": "relevance", "date": "date", "views": "views", "trending": "views"}


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def build_search_params(sort: str, period: str) -> str:
    """Return the base64 `sp` value for a sort order and upload-date window."""
    filters = b""
    if PERIOD_CODES[period]:
        filters += b"\x08" + _varint(PERIOD_CODES[period])
    filters += b"\x10" + _varint(TYPE_VIDEO)

    msg = b""
    if SORT_CODES[sort]:
        msg += b"\x08" + _varint(SORT_CODES[sort])
    msg += b"\x12" + _varint(len(filters)) + filters
    return base64.b64encode(msg).decode("ascii")


def build_search_url(query: str, sort: str, period: str) -> str:
    params = urllib.parse.urlencode(
        {"search_query": query, "sp": build_search_params(SERVER_SORT[sort], period)}
    )
    return f"https://www.youtube.com/results?{params}"


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def format_count(n: int | None) -> str:
    if n is None:
        return "?"
    for limit, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if n >= limit:
            return f"{n / limit:.1f}{suffix}"
    return str(n)


def normalize(entry: dict[str, Any], now: float) -> dict[str, Any] | None:
    """Map a yt-dlp entry to the fields this skill reports. Skips non-videos."""
    video_id = entry.get("id")
    if not video_id or entry.get("ie_key") not in (None, "Youtube"):
        return None
    if entry.get("live_status") in ("is_live", "is_upcoming"):
        return None

    timestamp = entry.get("timestamp")
    upload_date = entry.get("upload_date")
    if not timestamp and upload_date:
        timestamp = calendar.timegm(time.strptime(upload_date, "%Y%m%d"))
    if timestamp and not upload_date:
        upload_date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    elif upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

    views = entry.get("view_count")
    views_per_day = None
    if views is not None and timestamp:
        age_days = max((now - timestamp) / 86400, 1.0)
        views_per_day = round(views / age_days)

    return {
        "title": entry.get("title"),
        "views": views,
        "author": entry.get("channel") or entry.get("uploader"),
        "duration_seconds": int(entry["duration"]) if entry.get("duration") else None,
        "duration": format_duration(entry.get("duration")),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "id": video_id,
        "channel_url": entry.get("channel_url") or entry.get("uploader_url"),
        "upload_date": upload_date,
        "views_per_day": views_per_day,
    }


def rank(videos: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    """Re-rank locally so the order holds even if YouTube ignores `sp` sorting."""
    if sort == "views":
        return sorted(videos, key=lambda v: v["views"] or 0, reverse=True)
    if sort == "trending":
        return sorted(
            videos, key=lambda v: (v["views_per_day"] or 0, v["views"] or 0), reverse=True
        )
    if sort == "date":
        return sorted(videos, key=lambda v: v["upload_date"] or "", reverse=True)
    return videos


def search(
    query: str,
    count: int,
    sort: str = "relevance",
    period: str = "any",
    min_duration: int = 0,
    pool: int | None = None,
    full: bool = False,
) -> list[dict[str, Any]]:
    """Return up to `count` videos for `query`, ranked by `sort`."""
    # Fetch a larger candidate pool so local re-ranking and filters still fill `count`.
    pool = pool or (count if sort == "relevance" and not min_duration else max(count * 2, 50))
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": pool,
        # Approximate upload dates from "3 days ago" labels; needed for date/trending.
        "extractor_args": {"youtubetab": {"approximate_date": [""]}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(build_search_url(query, sort, period), download=False)

    now = time.time()
    videos = [v for e in (result or {}).get("entries") or [] if e and (v := normalize(e, now))]
    if min_duration:
        videos = [v for v in videos if (v["duration_seconds"] or 0) >= min_duration]
    videos = rank(videos, sort)[:count]

    if full:
        videos = [_enrich(v) for v in videos]
    return videos


def _enrich(video: dict[str, Any]) -> dict[str, Any]:
    """Fetch the full video page for exact upload date, likes and description."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video["url"], download=False)
    except yt_dlp.utils.DownloadError as exc:
        video["error"] = str(exc)
        return video
    enriched = normalize({**info, "ie_key": "Youtube"}, time.time()) or {}
    video.update({k: v for k, v in enriched.items() if v is not None})
    video["likes"] = info.get("like_count")
    video["description"] = (info.get("description") or "")[:500]
    return video


def render_table(videos: list[dict[str, Any]]) -> str:
    lines = [
        "| # | Título | Autor | Vistas | Duración | Fecha | URL |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, v in enumerate(videos, 1):
        title = (v["title"] or "").replace("|", "\\|")
        author = (v["author"] or "").replace("|", "\\|")
        lines.append(
            f"| {i} | {title} | {author} | {format_count(v['views'])} | "
            f"{v['duration']} | {v['upload_date'] or '?'} | {v['url']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Busca videos en YouTube y extrae metadatos.")
    parser.add_argument("query", help="Consulta de búsqueda (tema)")
    parser.add_argument("-n", "--count", type=int, default=25, help="Número de videos (25)")
    parser.add_argument(
        "--sort",
        choices=["relevance", "date", "views", "trending"],
        default="relevance",
        help="Orden: relevancia, fecha, vistas o trending (vistas por día)",
    )
    parser.add_argument(
        "--period",
        choices=list(PERIOD_CODES),
        default="any",
        help="Ventana de publicación: any, hour, today, week, month, year",
    )
    parser.add_argument(
        "--min-duration", type=int, default=0, help="Descarta videos más cortos (segundos)"
    )
    parser.add_argument("--pool", type=int, help="Candidatos a pedir antes de re-ordenar")
    parser.add_argument(
        "--full", action="store_true", help="Metadatos completos por video (más lento)"
    )
    parser.add_argument(
        "--format", choices=["json", "table", "urls"], default="json", help="Formato de salida"
    )
    parser.add_argument("-o", "--output", help="Guarda el JSON en este archivo")
    args = parser.parse_args(argv)

    if not args.query.strip():
        parser.error("la consulta no puede estar vacía")

    try:
        videos = search(
            args.query,
            args.count,
            sort=args.sort,
            period=args.period,
            min_duration=args.min_duration,
            pool=args.pool,
            full=args.full,
        )
    except yt_dlp.utils.DownloadError as exc:
        print(f"Error de yt-dlp: {exc}", file=sys.stderr)
        return 1

    payload = {
        "query": args.query,
        "sort": args.sort,
        "period": args.period,
        "count": len(videos),
        "videos": videos,
    }
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"Guardados {len(videos)} videos en {args.output}", file=sys.stderr)

    if args.format == "table":
        print(render_table(videos))
    elif args.format == "urls":
        print("\n".join(v["url"] for v in videos))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not videos:
        print("No se encontraron videos para esa búsqueda.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
