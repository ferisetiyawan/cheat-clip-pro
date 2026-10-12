"""
Cheat Clip PRO — Model Context Protocol server.

Exposes tools so an agent (e.g. Hermes Multi Agent) can:
  1. paste a YouTube URL and get ranked clip recommendations,
  2. visually preview the recommended clips (frame images),
  3. render the chosen clips and download the files.

The Gemini API key is NOT required from the caller — the backend reads it from
its own environment. YouTube cookies are likewise read from the server ENV.

Run (stdio, for most agent hosts):
    pip install -e ./mcp
    CCP_BASE_URL=https://your-cheatclip-host cheat-clip-mcp

Run (streamable HTTP, for networked agents):
    CCP_MCP_TRANSPORT=streamable-http CCP_MCP_HOST=0.0.0.0 CCP_MCP_PORT=8765 cheat-clip-mcp
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import TextContent

from .client import CheatClipClient, CheatClipError, summary_of_clips

mcp = FastMCP("cheat-clip-pro")

_client: Optional[CheatClipClient] = None
# In-process cache of the most recent analysis per video_id, so tools can refer
# to clips by index (0, 1, 2, ...) without the agent re-sending full clip data.
_analyses: Dict[str, Dict[str, Any]] = {}

# Ready-made render settings. "clean_1080p" is the default: 9:16 1080x1920 output
# with clean, readable captions. Any keys passed in `settings` override these.
RENDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "clean_1080p": {
        "aspect_ratio": "9:16",
        "background_style": "black",
        "enable_face_tracking": True,
        "subtitles_enabled": True,
        "caption_style": "clean_minimal",
        "caption_font": "Inter",
        "title_font": "Inter",
        "font_size": "medium",
        "title_font_size": "medium",
        "text_case": "capitalize",
        "title_text_case": "capitalize",
        "subtitle_position_mode": "bottom",
        "title_position": "auto",
        "title_duration": "entire",
        "hardware_accel": "auto",
        "render_mode": "separate",
    },
    "viral": {
        "aspect_ratio": "9:16",
        "background_style": "black",
        "enable_face_tracking": True,
        "subtitles_enabled": True,
        "caption_style": "viral_pop",
        "caption_font": "Outfit",
        "title_font": "Outfit",
        "font_size": "big",
        "text_case": "uppercase",
        "subtitle_position_mode": "center",
        "title_position": "auto",
        "title_duration": "entire",
        "hardware_accel": "auto",
        "render_mode": "separate",
    },
    "none": {},
}


def _c() -> CheatClipClient:
    global _client
    if _client is None:
        _client = CheatClipClient()
    return _client


def _get_analysis(video_id: str) -> Dict[str, Any]:
    cached = _analyses.get(video_id)
    if not cached:
        raise CheatClipError(
            f"No cached analysis for video_id '{video_id}'. Call analyze_video(url) first."
        )
    return cached


def _select_clips(
    analysis: Dict[str, Any], clip_indices: Optional[List[int]]
) -> List[Dict[str, Any]]:
    clips = summary_of_clips(analysis)
    if not clip_indices:
        return clips
    selected = []
    for idx in clip_indices:
        if 0 <= idx < len(clips):
            selected.append(clips[idx])
        else:
            raise CheatClipError(
                f"clip index {idx} is out of range (0..{len(clips) - 1})."
            )
    return selected


# ── Tools ─────────────────────────────────────────────────────────────────


@mcp.tool()
def get_platform_status() -> Dict[str, Any]:
    """
    Check the Cheat Clip PRO server: reachability, whether a Gemini API key and
    YouTube cookies are configured via ENV, and which video encoders are available.
    Use this first to confirm the platform is ready for automation.
    """
    health = _c().health()
    try:
        hw = _c().hardware_accel()
    except CheatClipError:
        hw = {}
    return {
        "base_url": _c().base_url,
        "status": health.get("status"),
        "gemini_env_configured": health.get("gemini_env_configured"),
        "cookies_env_configured": health.get("cookies_env_configured"),
        "proxy_configured": health.get("proxy_configured"),
        "supadata_keys_count": health.get("supadata_keys_count"),
        "recommended_encoder": hw.get("recommended"),
    }


@mcp.tool()
def analyze_video(
    url: str,
    duration: str = "auto",
    target_clip_count: Union[int, str] = "auto",
    custom_prompt: Optional[str] = None,
    model: Optional[str] = None,
    range_start: Optional[float] = None,
    range_end: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Analyze a YouTube video URL and return ranked viral clip candidates.

    Args:
        url: The YouTube video URL (paste the link directly).
        duration: Target clip length: "15s", "30s", "60s", or "auto" (dynamic, 15-90s).
        target_clip_count: Number of clips to find, or "auto" for all high-value moments.
        custom_prompt: Optional focus, e.g. "find clips about pricing / mindset".
        model: Optional Gemini model id (defaults to the server's choice).
        range_start / range_end: Optional analysis window in seconds.

    Returns a summary plus an indexed list of clips. Reference clips later by
    their `index` in preview_clips / render_clips.
    """
    result = _c().analyze(
        url=url,
        duration=duration,
        target_clip_count=target_clip_count,
        custom_prompt=custom_prompt,
        model=model,
        range_start=range_start,
        range_end=range_end,
    )
    video_id = result.get("video_id", "")
    _analyses[video_id] = result
    clips = summary_of_clips(result)
    return {
        "video_id": video_id,
        "title": result.get("title"),
        "channel": result.get("channel"),
        "duration": result.get("duration"),
        "summary": result.get("summary"),
        "source_type": result.get("source_type"),
        "clip_count": len(clips),
        "clips": clips,
        "preview_hint": "Call preview_clips(video_id, clip_indices) to view frames.",
    }


@mcp.tool()
def preview_clips(
    video_id: str,
    clip_indices: Optional[List[int]] = None,
    marks: Optional[List[str]] = None,
    video_url: Optional[str] = None,
) -> list:
    """
    Return preview frame images for recommended clips so a human/agent can SEE
    them before rendering. Use this after analyze_video.

    Args:
        video_id: The video_id returned by analyze_video.
        clip_indices: Which clips to preview (defaults to all). e.g. [0, 2].
        marks: Which moments to capture per clip: a subset of ["start", "hook", "end"].
               Defaults to ["hook"] (the moment the AI thinks is the hook).
        video_url: Optional source URL to help frame extraction.

    Returns text labels followed by the corresponding JPEG frame images.
    """
    analysis = _get_analysis(video_id)
    source_url = video_url or analysis.get("video_url")
    marks = [m.lower() for m in (marks or ["hook"])]
    selected = _select_clips(analysis, clip_indices)

    content: list = []
    for clip in selected:
        content.append(
            TextContent(
                type="text",
                text=(
                    f"Clip #{clip['index']} — \"{clip['title']}\" "
                    f"({clip['duration']}s, virality {clip['virality_score']}) "
                    f"[{clip['start_time']:.1f}s-{clip['end_time']:.1f}s, hook {clip['hook_time']:.1f}s]"
                ),
            )
        )
        for mark in marks:
            ts = {
                "start": clip["start_time"],
                "hook": clip["hook_time"],
                "end": clip["end_time"],
            }.get(mark)
            if ts is None:
                continue
            frame = _c().clip_frame(video_id, ts, source_url)
            if frame:
                content.append(TextContent(type="text", text=f"  {mark} @ {ts:.1f}s:"))
                content.append(Image(data=frame, format="jpeg"))
            else:
                content.append(
                    TextContent(type="text", text=f"  {mark} @ {ts:.1f}s: frame unavailable")
                )
    return content


@mcp.tool()
def render_clips(
    video_id: str,
    clip_indices: Optional[List[int]] = None,
    preset: str = "clean_1080p",
    settings: Optional[Dict[str, Any]] = None,
    wait: bool = True,
    max_wait_seconds: float = 1800.0,
    auto_download: bool = True,
) -> Dict[str, Any]:
    """
    Render one or more recommended clips into finished vertical MP4s.

    Args:
        video_id: The video_id from analyze_video.
        clip_indices: Which clips to render (defaults to all). e.g. [0, 3].
        preset: Ready-made style. One of "clean_1080p" (default — 9:16, clean captions),
                "viral" (bold karaoke captions), or "none" (server defaults).
        settings: Optional overrides merged on top of the preset, e.g.
            {"caption_style": "beast_punch", "enable_face_tracking": false, "hardware_accel": "cpu"}.
        wait: Wait for rendering to finish before returning (default true).
        max_wait_seconds: Safety timeout for waiting.
        auto_download: When finished, download the batch ZIP locally and return its path.

    Returns batch status; when completed and auto_download is true, also returns
    the local ZIP path and per-clip download URLs.
    """
    analysis = _get_analysis(video_id)
    clips = _select_clips(analysis, clip_indices)

    # Merge: preset base, then explicit overrides.
    effective_settings: Dict[str, Any] = dict(RENDER_PRESETS.get(preset, {}))
    if settings:
        effective_settings.update(settings)

    render_clips_payload = [
        {
            "title": clip["title"],
            "custom_title": clip.get("title_suggestion") or clip["title"],
            "title_suggestion": clip.get("title_suggestion"),
            "start_time": clip["start_time"],
            "end_time": clip["end_time"],
            "hook_time": clip["hook_time"],
            "transcript": clip.get("transcript"),
            "virality_score": clip.get("virality_score"),
            "key_quotes": clip.get("key_quotes"),
        }
        for clip in clips
    ]

    payload = {
        "video_url": analysis.get("video_url") or "",
        "video_id": video_id,
        "clips": render_clips_payload,
        "settings": effective_settings,
        "transcript": analysis.get("transcript"),
    }
    started = _c().render_batch(payload)
    batch_id = started["batch_id"]

    out: Dict[str, Any] = {
        "batch_id": batch_id,
        "total_clips": started.get("total_clips"),
        "preset": preset,
        "status": "running",
    }
    if not wait:
        out["hint"] = f"Poll get_render_status('{batch_id}') until completed."
        return out

    batch = _c().wait_render(batch_id, max_wait=max_wait_seconds)
    out["status"] = batch.get("overall_status")
    out["clips"] = [
        {
            "clip_index": c.get("clip_index"),
            "title": c.get("title"),
            "status": c.get("status"),
            "download_url": _c().absolute(c["download_url"]) if c.get("download_url") else None,
            "error": c.get("error") or c.get("error_message"),
        }
        for c in (batch.get("clips") or [])
    ]

    if batch.get("overall_status") == "completed" and auto_download:
        try:
            zip_path = _c().download_batch_zip(batch_id)
            out["zip_path"] = str(zip_path)
        except CheatClipError as exc:
            out["download_error"] = str(exc)
    return out


@mcp.tool()
def get_render_status(batch_id: str) -> Dict[str, Any]:
    """Return the current status/progress of a previously started render batch."""
    batch = _c().get_batch(batch_id)
    return {
        "batch_id": batch_id,
        "overall_status": batch.get("overall_status"),
        "total_clips": batch.get("total_clips"),
        "current_clip_index": batch.get("current_clip_index"),
        "clips": [
            {
                "clip_index": c.get("clip_index"),
                "title": c.get("title"),
                "status": c.get("status"),
                "progress_percent": c.get("progress_percent"),
            }
            for c in (batch.get("clips") or [])
        ],
        "zip_url": _c().absolute(batch["zip_url"]) if batch.get("zip_url") else None,
    }


@mcp.tool()
def download_batch(batch_id: str, dest_dir: Optional[str] = None) -> Dict[str, Any]:
    """Download a finished render batch as a ZIP file to the local machine."""
    path = _c().download_batch_zip(batch_id, Path(dest_dir) if dest_dir else None)
    return {"batch_id": batch_id, "zip_path": str(path), "size_bytes": path.stat().st_size}


# ── Resources & prompt ────────────────────────────────────────────────────


@mcp.resource("cheatclip://guide")
def usage_guide() -> str:
    """Recommended workflow and tips for automating Cheat Clip PRO."""
    return (
        "CHEAT CLIP PRO — automated clipping workflow\n"
        "1. get_platform_status() — confirm the server is reachable and ready.\n"
        "2. analyze_video(url) — paste a YouTube URL; returns ranked clip candidates.\n"
        "3. Rank/select clips by virality_score and the user's goal.\n"
        "4. preview_clips(video_id, [indices]) — SHOW the frames to the user to decide.\n"
        "5. render_clips(video_id, [indices], settings) — render the chosen clips.\n"
        "6. download / zip is returned automatically; upload the best MP4s.\n\n"
        "Notes:\n"
        "- No Gemini key is needed: the server reads GEMINI_API_KEY from its ENV.\n"
        "- YouTube cookies, if needed to avoid IP bans, are also read from the server ENV.\n"
        "- Clip indices are tied to the most recent analyze_video result per video_id.\n"
    )


@mcp.prompt()
def pick_best_clips(url: str, goal: str = "maximize watch-through and shares") -> str:
    """Prompt template that guides the agent through analyze → preview → pick → render."""
    return (
        f"You are a short-form video editor. Goal: {goal}.\n\n"
        f"Step 1: Call analyze_video(url=\"{url}\") and review the returned clips.\n"
        "Step 2: Rank the clips by virality_score and how well they fit the goal. "
        "Explain your top 3 choices in one sentence each.\n"
        "Step 3: Call preview_clips(video_id, clip_indices=[...]) for the top 3 so the "
        "human can see the hook frames.\n"
        "Step 4: After the human confirms, call render_clips(video_id, clip_indices=[...]) "
        "and report the download paths.\n"
    )


def main() -> None:
    transport = os.environ.get("CCP_MCP_TRANSPORT", "stdio").strip().lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        # FastMCP reads host/port from its settings; expose via env for convenience.
        mcp.settings.host = os.environ.get("CCP_MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.environ.get("CCP_MCP_PORT", "8765"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
