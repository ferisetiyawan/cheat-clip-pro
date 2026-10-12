"""
Thin HTTP client for the Cheat Clip PRO backend API.

The MCP server never needs a Gemini API key from the caller: the backend reads
``GEMINI_API_KEY`` from its own environment. A key is only forwarded if one is
present in this process's environment (``CCP_GEMINI_API_KEY`` / ``GEMINI_API_KEY``),
which lets operators override the server default when they want to.

Configuration is entirely via environment variables:

    CCP_BASE_URL        Base URL of the Cheat Clip PRO backend (default http://localhost:8000)
    MCP_API_KEY         API key for authenticated access (matches the server's MCP_API_KEY)
    CCP_SESSION_TOKEN   Optional pre-issued bearer token (alternative to MCP_API_KEY)
    CCP_USERNAME        Dashboard username (used only if no API key and login is enabled)
    CCP_PASSWORD        Dashboard password
    CCP_VERIFY_TLS      "false" to disable TLS verification (self-signed certs)
    CCP_TIMEOUT         Per-request timeout in seconds for non-streaming calls (default 120)
    CCP_OUTPUT_DIR      Where rendered files/downloads are written (default ./cheat-clip-output)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


class CheatClipError(RuntimeError):
    """Raised for any non-recoverable Cheat Clip PRO API error."""


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip() != "":
            return value
    return default


class CheatClipClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        verify_tls: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (
            base_url
            or _env("CCP_BASE_URL", "CHEAT_CLIP_BASE_URL", default="http://localhost:8000")
        ).rstrip("/")
        self.api_key = api_key or _env("MCP_API_KEY", "CCP_API_KEY")
        self.username = username or _env("CCP_USERNAME", "DASHBOARD_LOGIN_USERNAME")
        self.password = password or _env("CCP_PASSWORD", "DASHBOARD_LOGIN_PASSWORD")
        self.token = token or _env("CCP_SESSION_TOKEN")
        self.verify = (
            verify_tls
            if verify_tls is not None
            else _env("CCP_VERIFY_TLS", default="true").lower() not in ("0", "false", "no")
        )
        try:
            self.timeout = float(timeout or _env("CCP_TIMEOUT", default="120"))
        except ValueError:
            self.timeout = 120.0
        self.output_dir = Path(_env("CCP_OUTPUT_DIR", default="./cheat-clip-output")).expanduser()

        self._client = httpx.Client(
            base_url=self.base_url,
            verify=self.verify,
            follow_redirects=True,
            timeout=self.timeout,
        )
        self._authed = False

    # ── auth ──────────────────────────────────────────────────────────────
    def _headers(self) -> Dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}", "X-API-Key": self.api_key}
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _ensure_auth(self) -> None:
        if self._authed:
            return
        try:
            status = self._client.get("/api/auth/status", headers=self._headers()).json()
        except Exception as exc:  # noqa: BLE001
            raise CheatClipError(
                f"Cannot reach Cheat Clip PRO at {self.base_url}: {exc}"
            ) from exc

        if not status.get("auth_required") or status.get("authenticated"):
            self._authed = True
            return

        if self.api_key:
            raise CheatClipError(
                "MCP_API_KEY was rejected by the server (invalid or not configured there)."
            )
        if self.token:
            raise CheatClipError("The provided CCP_SESSION_TOKEN is invalid or expired.")
        if not status.get("login_available", True):
            raise CheatClipError(
                "This server requires an API key. Set MCP_API_KEY in the MCP server environment."
            )
        if not (self.username and self.password):
            raise CheatClipError(
                "The dashboard requires a login. Set MCP_API_KEY, or CCP_USERNAME and CCP_PASSWORD."
            )

        resp = self._client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise CheatClipError(f"Login failed ({resp.status_code}): {resp.text[:200]}")
        self._authed = True

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self._ensure_auth()
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        resp = self._client.request(method, path, headers=headers, **kwargs)
        if resp.status_code == 401:
            # Session/token may have expired — re-authenticate once.
            self._authed = False
            self._ensure_auth()
            headers = {**self._headers(), **kwargs.get("headers", {})}
            resp = self._client.request(method, path, headers=headers, **kwargs)
        return resp

    # ── read APIs ─────────────────────────────────────────────────────────
    def health(self) -> Dict[str, Any]:
        resp = self._request("GET", "/api/health")
        if resp.status_code != 200:
            raise CheatClipError(f"Health check failed ({resp.status_code}).")
        return resp.json()

    def hardware_accel(self) -> Dict[str, Any]:
        resp = self._request("GET", "/api/hardware-accel")
        if resp.status_code != 200:
            raise CheatClipError(f"hardware-accel failed ({resp.status_code}).")
        return resp.json()

    def clip_frame(
        self, video_id: str, timestamp: float, video_url: Optional[str] = None
    ) -> Optional[bytes]:
        """Returns JPEG bytes for a frame, or None if it cannot be extracted."""
        params: Dict[str, Any] = {"video_id": video_id, "timestamp": float(timestamp)}
        if video_url:
            params["video_url"] = video_url
        resp = self._request("GET", "/api/clip-frame", params=params)
        if resp.status_code == 200 and resp.content:
            return resp.content
        return None

    # ── analyze (SSE) ─────────────────────────────────────────────────────
    def analyze(
        self,
        url: str,
        duration: str = "auto",
        target_clip_count: Any = "auto",
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
        range_start: Optional[float] = None,
        range_end: Optional[float] = None,
        subtitles: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"url": url, "duration": str(duration)}
        if target_clip_count is not None:
            payload["target_clip_count"] = target_clip_count
        if custom_prompt:
            payload["custom_prompt"] = custom_prompt
        if model:
            payload["model"] = model
        if range_start is not None:
            payload["range_start"] = float(range_start)
        if range_end is not None:
            payload["range_end"] = float(range_end)
        if subtitles:
            payload["subtitles"] = subtitles

        # Only forward a key if this process has one; otherwise the backend ENV is used.
        override_key = _env("CCP_GEMINI_API_KEY", "GEMINI_API_KEY")
        if override_key:
            payload["api_key"] = override_key.strip()

        self._ensure_auth()
        result: Optional[Dict[str, Any]] = None
        with self._client.stream(
            "POST",
            "/api/analyze",
            json=payload,
            headers=self._headers(),
            timeout=httpx.Timeout(self.timeout, read=None),
        ) as resp:
            if resp.status_code >= 400 and "json" in resp.headers.get("content-type", ""):
                resp.read()
                raise CheatClipError(f"Analyze failed ({resp.status_code}): {resp.text[:300]}")
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("error"):
                    raise CheatClipError(str(event["error"]))
                if isinstance(event, dict) and event.get("done") and event.get("result"):
                    result = event["result"]

        if not result:
            raise CheatClipError("Analysis completed but returned no result.")
        return result

    # ── render (SSE progress) ─────────────────────────────────────────────
    def render_batch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._request("POST", "/api/render-batch", json=payload)
        if resp.status_code != 200:
            raise CheatClipError(f"render-batch failed ({resp.status_code}): {resp.text[:300]}")
        return resp.json()

    def wait_render(
        self, batch_id: str, max_wait: float = 1800.0, poll_interval: float = 5.0
    ) -> Dict[str, Any]:
        deadline = time.time() + max_wait
        last: Optional[Dict[str, Any]] = None
        with self._client.stream(
            "GET",
            f"/api/render-progress/{batch_id}",
            headers=self._headers(),
            timeout=httpx.Timeout(30.0, read=None),
        ) as resp:
            for line in resp.iter_lines():
                if time.time() > deadline:
                    break
                if not line.startswith("data:"):
                    continue
                try:
                    batch = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                last = batch
                if batch.get("overall_status") in ("completed", "error"):
                    break
        if last is None:
            raise CheatClipError(f"No progress received for batch {batch_id}.")
        if last.get("overall_status") not in ("completed", "error") and time.time() > deadline:
            last["timed_out"] = True
        return last

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        # The progress endpoint streams and closes on terminal state; read the final frame.
        return self.wait_render(batch_id, max_wait=1.0)

    # ── downloads ─────────────────────────────────────────────────────────
    def download_to_file(self, path: str, dest_path: Path) -> Path:
        self._ensure_auth()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with self._client.stream(
            "GET", path, headers=self._headers(), timeout=httpx.Timeout(self.timeout, read=None)
        ) as resp:
            if resp.status_code != 200:
                resp.read()
                raise CheatClipError(f"Download failed ({resp.status_code}) for {path}.")
            with open(dest_path, "wb") as handle:
                for chunk in resp.iter_bytes():
                    handle.write(chunk)
        return dest_path

    def download_batch_zip(self, batch_id: str, dest_dir: Optional[Path] = None) -> Path:
        target_dir = Path(dest_dir) if dest_dir else self.output_dir
        dest = target_dir / f"cheat_clip_pro_{batch_id}.zip"
        return self.download_to_file(f"/api/download-batch-zip/{batch_id}", dest)

    def download_clip(self, file_name: str, dest_dir: Optional[Path] = None) -> Path:
        target_dir = Path(dest_dir) if dest_dir else self.output_dir
        return self.download_to_file(
            f"/api/download-rendered/{file_name}", target_dir / file_name
        )

    def absolute(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self.base_url}{path if path.startswith('/') else '/' + path}"


def summary_of_clips(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalizes the analyze result clips into a compact, index-addressable list."""
    clips: List[Dict[str, Any]] = []
    for idx, clip in enumerate(result.get("clips") or []):
        start = float(clip.get("start_time", 0.0))
        end = float(clip.get("end_time", start))
        clips.append(
            {
                "index": idx,
                "title": clip.get("title", ""),
                "title_suggestion": clip.get("title_suggestion", ""),
                "caption_suggestion": clip.get("caption_suggestion", ""),
                "hashtag_suggestion": clip.get("hashtag_suggestion", ""),
                "start_time": start,
                "end_time": end,
                "hook_time": float(clip.get("hook_time", start)),
                "duration": round(max(0.0, end - start), 1),
                "virality_score": clip.get("virality_score", 0),
                "key_quotes": clip.get("key_quotes", []),
                "transcript": clip.get("transcript", ""),
            }
        )
    return clips
