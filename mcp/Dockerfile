# Cheat Clip PRO — MCP server (streamable HTTP transport)
# The heavy media work (FFmpeg/Whisper/yt-dlp) runs on the Cheat Clip PRO backend,
# so this image is small and only needs network access to the backend.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    CCP_MCP_TRANSPORT=streamable-http \
    CCP_MCP_HOST=0.0.0.0 \
    CCP_MCP_PORT=8765 \
    CCP_OUTPUT_DIR=/data

COPY pyproject.toml README.md ./
COPY cheat_clip_mcp ./cheat_clip_mcp
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

RUN mkdir -p /data
EXPOSE 8765

CMD ["cheat-clip-mcp"]
