# Cheat Clip PRO — MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets an
agent (e.g. **Hermes Multi Agent**, Claude Desktop, Cursor, or any MCP host)
drive Cheat Clip PRO end-to-end:

1. **Paste a YouTube URL** → get ranked clip recommendations.
2. **See the clips** → the agent receives preview frame images.
3. **Decide the best clip** → render and download the finished MP4s.

> **No Gemini API key required.** The backend reads `GEMINI_API_KEY` from its own
> environment. The MCP server never asks the user for a key. (YouTube cookies are
> likewise read from the server ENV.)

---

## Tools

| Tool | Description |
| --- | --- |
| `get_platform_status` | Reachability, whether Gemini key + YouTube cookies are ENV-configured, available encoders. |
| `analyze_video(url, duration, target_clip_count, custom_prompt, model, range_start, range_end)` | Analyze a YouTube URL, return ranked clip candidates (title, timestamps, virality, quotes, captions). |
| `preview_clips(video_id, clip_indices, marks, video_url)` | Return **JPEG frame images** (start/hook/end) so the agent/user can visually judge each clip. |
| `render_clips(video_id, clip_indices, preset, settings, wait, max_wait_seconds, auto_download)` | Render selected clips to vertical MP4s; downloads a ZIP when done. Default preset `clean_1080p`. |
| `get_render_status(batch_id)` | Progress of a render batch. |
| `download_batch(batch_id, dest_dir)` | Download a finished batch ZIP. |

**Render presets:** `clean_1080p` (default — 9:16 1080×1920, `clean_minimal` captions, Inter font,
sentence case), `viral` (bold `viral_pop` karaoke captions), or `none` (raw server defaults). Any key
in `settings` overrides the preset.

Also provided: a `cheatclip://guide` resource and a `pick_best_clips` prompt.

---

## Install

```bash
# from the repo root
pip install -e ./mcp
# or run without installing:
uvx --from ./mcp cheat-clip-mcp
```

## Configure (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `CCP_BASE_URL` | `http://localhost:8000` | Base URL of the Cheat Clip PRO backend. |
| `MCP_API_KEY` | — | API key matching the server's `MCP_API_KEY`. Sent as Bearer + `X-API-Key`. **Recommended.** |
| `CCP_SESSION_TOKEN` | — | Pre-issued bearer token (alternative to `MCP_API_KEY`). |
| `CCP_USERNAME` / `CCP_PASSWORD` | — | Fallback dashboard login, only if password login is enabled on the server. |
| `CCP_VERIFY_TLS` | `true` | Set `false` for self-signed certificates. |
| `CCP_TIMEOUT` | `120` | Per-request timeout (seconds) for non-streaming calls. |
| `CCP_OUTPUT_DIR` | `./cheat-clip-output` | Where rendered ZIPs/MP4s are saved. |
| `CCP_GEMINI_API_KEY` | — | Optional override key. Leave unset to use the server ENV key. |

Transport:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CCP_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http`. |
| `CCP_MCP_HOST` / `CCP_MCP_PORT` | `0.0.0.0` / `8765` | Bind address for HTTP transport. |

---

## Hermes Multi Agent / generic MCP host config

```json
{
  "mcpServers": {
    "cheat-clip-pro": {
      "command": "cheat-clip-mcp",
      "env": {
        "CCP_BASE_URL": "https://cheatclip.example.com",
        "MCP_API_KEY": "your-mcp-api-key",
        "CCP_OUTPUT_DIR": "/Users/you/cheat-clip-output"
      }
    }
  }
}
```

**opencode** (`opencode.json`) — a project config is included in this repo:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "cheat-clip-pro": {
      "type": "local",
      "command": ["uv", "run", "--directory", "mcp", "cheat-clip-mcp"],
      "environment": {
        "CCP_BASE_URL": "{env:CHEAT_CLIP_BASE_URL}",
        "MCP_API_KEY": "{env:MCP_API_KEY}",
        "CCP_OUTPUT_DIR": "./cheat-clip-output"
      }
    }
  }
}
```

Set `CHEAT_CLIP_BASE_URL` and `MCP_API_KEY` in your shell before starting opencode. For a
Coolify-hosted MCP, use the remote form instead:

```json
{ "mcp": { "cheat-clip-pro": {
  "type": "remote", "url": "https://mcp.your-domain.com/mcp"
}}}
```

If your host prefers `uvx` without a global install:

```json
{
  "mcpServers": {
    "cheat-clip-pro": {
      "command": "uvx",
      "args": ["--from", "/absolute/path/to/cheat-clip-pro/mcp", "cheat-clip-mcp"],
      "env": { "CCP_BASE_URL": "https://cheatclip.example.com" }
    }
  }
}
```

For a networked / containerized agent, run the HTTP transport instead:

```bash
CCP_MCP_TRANSPORT=streamable-http CCP_MCP_HOST=0.0.0.0 CCP_MCP_PORT=8765 \
  CCP_BASE_URL=https://cheatclip.example.com cheat-clip-mcp
# endpoint: http://<host>:8765/mcp
```

---

## Recommended agent flow

```
get_platform_status()
      │
analyze_video("https://youtube.com/watch?v=...")
      │   → clips[] with index, title, start/end, virality_score, quotes
      │
rank clips (by virality_score / the user's goal)
      │
preview_clips(video_id, clip_indices=[0,2,5])
      │   → frame images the human can look at
      │
render_clips(video_id, clip_indices=[0,2], settings={"aspect_ratio":"9:16"})
      │   → MP4s + ZIP path
      │
upload the chosen files
```

Clip indices refer to the most recent `analyze_video` result for that
`video_id`, so the agent can pass just `[0, 2]` instead of full clip objects.

---

## Docker

```bash
docker build -t cheat-clip-mcp ./mcp
docker run --rm -p 8765:8765 \
  -e CCP_BASE_URL=https://cheatclip.example.com \
  -e MCP_API_KEY=your-mcp-api-key \
  -e CCP_MCP_TRANSPORT=streamable-http \
  -v "$PWD/output:/data" -e CCP_OUTPUT_DIR=/data \
  cheat-clip-mcp
# endpoint: http://localhost:8765/mcp
```

> The MCP server only needs network access to the Cheat Clip PRO backend; all
> FFmpeg/Whisper work happens on the backend, so this container stays tiny and
> does not need media tooling.

## Deploy via Coolify

The MCP is already a service in the repo's `docker-compose.yml` (`mcp`), so a
Coolify **Docker Compose** deployment builds and runs it automatically next to
the backend.

1. In Coolify set the shared environment variable `MCP_API_KEY` (a long random
   string). It is passed to **both** the backend and the MCP service, so the
   agent can authenticate without a password.
2. To reach the MCP from a remote agent, open **Domains → Add domain** and add a
   second domain bound to **Service = `mcp`**, **Internal port = `8765`**
   (e.g. `https://mcp.your-domain.com:8765`).
3. Point your agent at `https://mcp.your-domain.com/mcp`.

**Protect the endpoint.** The MCP HTTP transport itself does not require the API
key (the MCP authenticates *to the backend* with it), so anyone who can reach the
URL can drive it. Either keep it on a private network, or put Coolify's built-in
Basic Auth in front of the `mcp` domain. The `MCP_API_KEY` still protects the
backend: without it, all API calls the MCP makes will be rejected with 401.

Local compose (same network as the backend):

```bash
MCP_API_KEY=your-key docker compose up -d backend mcp
# internal: http://mcp:8765/mcp  (from the agent container)
```
