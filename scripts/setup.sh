#!/usr/bin/env bash
# Crea .venv en la raíz del repositorio e instala las dependencias de las habilidades.
# Uso: scripts/setup.sh        (se puede repetir; actualiza yt-dlp y notebooklm-py)
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  [ -x .venv/bin/python ] || uv venv --quiet .venv
  uv pip install --quiet --python .venv/bin/python -U -r requirements.txt
else
  [ -x .venv/bin/python ] || python3 -m venv .venv
  .venv/bin/pip install --quiet -U -r requirements.txt
fi

echo "Listo:"
echo "  yt-dlp      $(.venv/bin/yt-dlp --version)"
echo "  notebooklm  $(.venv/bin/notebooklm --version)"
