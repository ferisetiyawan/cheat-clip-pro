#!/bin/sh
# ==============================================================================
# Cheat Clip PRO backend entrypoint
# Seeds bundled fonts into the persisted volume, ensures runtime dirs exist,
# then boots the single-worker Uvicorn server (single worker is required: SSE
# progress streams and render/download job state live in process memory).
# ==============================================================================
set -e

FONTS_DIR="/app/backend/fonts"
DEFAULT_FONTS_DIR="/opt/default-fonts"

mkdir -p \
    /app/backend/temp_clips/uploads \
    /app/backend/temp \
    /app/backend/exports \
    "$FONTS_DIR"

# Copy any bundled fonts that are missing from the (possibly pre-existing) volume.
if [ -d "$DEFAULT_FONTS_DIR" ]; then
    cp -Rn "$DEFAULT_FONTS_DIR"/. "$FONTS_DIR"/ 2>/dev/null || true
fi

echo "[entrypoint] ffmpeg:  $(command -v ffmpeg || echo 'MISSING')"
echo "[entrypoint] yt-dlp:  $(command -v yt-dlp || echo 'via python -m yt_dlp')"
echo "[entrypoint] starting uvicorn on ${HOST:-0.0.0.0}:${PORT:-8000}"

exec uvicorn backend.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --timeout-keep-alive 75 \
    --proxy-headers \
    --forwarded-allow-ips '*'
