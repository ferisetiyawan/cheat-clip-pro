# Setting Up Google Stitch MCP (Reference)

This is background for explaining setup to the user, or for the user to follow themselves — this skill does not perform installation, since it runs inside the agent session that would use the already-configured server.

## What it is

Stitch (stitch.withgoogle.com) is Google Labs' AI UI design tool (Gemini-powered): text prompt in, UI screens + exportable HTML/CSS/Figma out. Its MCP integration exposes that generation capability as tools an MCP-compatible coding agent can call directly, instead of a human pasting prompts into the Stitch web UI.

**This only works in MCP-capable agent environments** — Claude Code, Cursor, Gemini CLI, VS Code, Codex, OpenCode — not inside claude.ai's web or mobile chat, which has no Stitch entry in its connector directory.

## Two common ways to set it up

### Option A — community CLI (`@_davideast/stitch-mcp`)
```bash
npx @_davideast/stitch-mcp init
```
This runs a guided wizard: installs/checks `gcloud`, handles OAuth or an API key, and writes the MCP client config for you. Once done, add this to the coding agent's MCP config (the wizard usually does this automatically):
```json
{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["@_davideast/stitch-mcp", "proxy"]
    }
  }
}
```
Simplest auth path: set an API key from Stitch's own settings page instead of going through OAuth:
```bash
export STITCH_API_KEY="your-api-key"
```
Note: this is an independent, experimental, community-built tool — not officially affiliated with or supported by Google.

### Option B — official Gemini CLI extension (`gemini-cli-extensions/stitch`)
```bash
gemini extensions install https://github.com/gemini-cli-extensions/stitch --auto-update
```
Supports the same two auth methods (API key, or Application Default Credentials via `gcloud`).

## Prerequisites either way
- A Google Cloud project with billing enabled and the Stitch API turned on.
- Either an API key generated from Stitch's settings page, or `gcloud auth application-default login` plus `gcloud beta services mcp enable stitch.googleapis.com`.

## Known limits
- Free tier generation caps (commonly cited around 350 generations/month) apply regardless of which client calls the tools.
- This is an experimental/evolving integration — tool names and schemas can change between versions; always check the live tool list rather than assuming a fixed API surface.

## Troubleshooting pointers
- "Permission denied" → check IAM role (Owner/Editor), billing enabled, Stitch API enabled on the project.
- Auth URL not appearing in terminal → look for a `https://accounts.google.com` URL with a short timeout window; in WSL/SSH/Docker contexts, copy it into a browser manually.
- Tools not showing up in the agent → fully restart the MCP client (a reload is often not enough; some clients cache the tool list).
