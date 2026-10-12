# 🎬 Cheat Clip PRO

> **AI Powered Auto Clipper — Turn long YouTube, Google Drive, and uploaded videos into viral TikToks, Shorts, and Reels with animated subtitles, face centering, and music in minutes.**

---

## ⚡ Quick Start & Setup

Follow these steps to set up and run Cheat Clip PRO locally on **Windows**, **macOS**, or **Linux**.

### Step 1: Prerequisites

Make sure you have the following installed:

1. **[Git](https://git-scm.com/)**
   * **Windows:** `winget install Git.Git` or download from [git-scm.com](https://git-scm.com/)
   * **macOS:** `brew install git`
   * **Linux:** `sudo apt install git`
2. **[Node.js](https://nodejs.org/)** (v18 or newer)
   * Download from [nodejs.org](https://nodejs.org/) or install via your package manager.
3. **[Python](https://www.python.org/)** (v3.10 or newer)
   * **Windows:** Install from [python.org](https://www.python.org/downloads/) (make sure to check *"Add Python to PATH"* during setup) or from Microsoft Store.
   * **macOS:** `brew install python`
   * **Linux:** `sudo apt install python3 python3-pip python3-venv`
4. **FFmpeg & yt-dlp** (Required to download, slice, and render clips)
   * **Windows (PowerShell):**
     ```powershell
     winget install Gyan.FFmpeg
     winget install yt-dlp.yt-dlp
     ```
     *(Close and reopen your terminal after installing so Windows recognizes them)*
   * **macOS (Terminal):**
     ```bash
     brew install ffmpeg-full yt-dlp
     ```
      `ffmpeg-full` is required for the libass subtitle filter used by rendered captions.
   * **Linux:**
     ```bash
     sudo apt update && sudo apt install ffmpeg
     pip install yt-dlp
     ```

---

### Step 2: Clone the Repository

Open your terminal and clone the repository:

```bash
git clone https://github.com/galihjuansaputra/cheat-clip-pro.git
cd cheat-clip-pro
```

---

### Step 3: Install Dependencies

#### 1. Frontend Dependencies
```bash
npm install
```

#### 2. Backend Dependencies
We recommend setting up a Python virtual environment:

* **Windows:**
  ```powershell
  python -m venv venv
  venv\Scripts\activate
  pip install -r backend/requirements.txt
  ```

* **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r backend/requirements.txt
  ```

---

### Step 4: Run the App

Launch both the frontend and backend servers concurrently:

```bash
npm run dev
```

* **Web App:** [`http://localhost:5173`](http://localhost:5173)
* **Backend API:** [`http://localhost:8000`](http://localhost:8000)
* **API Documentation:** [`http://localhost:8000/docs`](http://localhost:8000/docs)

---

## 🐳 Production Deploy (Docker / Coolify)

The repo ships a two-service `docker-compose.yml`:

| Service | Image | Role |
| --- | --- | --- |
| `frontend` | nginx + built React SPA | Serves the UI and reverse-proxies `/api` (streams progress live). Publishes port `80`. |
| `backend` | FastAPI + FFmpeg + yt-dlp + Whisper | All video download, transcription, AI analysis and rendering. Internal port `8000`. |

Images build **natively on ARM64 and AMD64** (tested on ARM). No GPU is required — the renderer falls back to
CPU `libx264`.

### Run locally

```bash
docker compose up -d --build
# App:      http://localhost:3000
# API docs: http://localhost:3000/docs
```

### Deploy on Coolify

1. Create a new Resource → **Docker Compose**, pointed at this repo.
2. Open **Domains → Add domain** and bind the domain to the **`frontend`** service with **internal port `80`**
   (e.g. `https://yourdomain.com:80`). **Do not** give the `backend` service a public domain — it is internal
   and reached by the frontend over the Compose network as `backend:8000`. Routing the domain to the backend
   is the usual cause of `GET / → 404` and a blank page.
3. Add environment variables (all optional):
   - `GEMINI_API_KEY` — server default AI key (users can also paste their own in the UI).
   - `SUPADATA_API_KEYS`, `WEBSHARE_PROXY` — reliable YouTube transcript fetching.
   - `ADMIN_API_KEY` — lock down admin/system endpoints on public deployments.
   - `BACKEND_MEM_LIMIT` (default `3g`) / `BACKEND_CPUS` (default `3`) — raise if your server has more RAM.
4. Deploy. Health checks: frontend `/healthz`, backend `/api/health`.

> First build downloads Python/Torch + the Whisper `base` model (~1–2 GB) once; later deploys are cached.

### Environment reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | — | Server-side default Gemini key |
| `SUPADATA_API_KEYS` | — | Supadata transcript keys (comma/space separated) |
| `WEBSHARE_PROXY` / `PROXY_URL` | — | Residential proxy to avoid YouTube IP bans |
| `ADMIN_API_KEY` | — | Protect admin endpoints with a token |
| `ALLOWED_ORIGINS` | — | Extra CORS origins (only if SPA and API differ) |
| `TEMP_MAX_AGE_SECONDS` | `3600` | Delete temp files older than this |
| `TEMP_STORAGE_QUOTA_GB` | `5.0` | Temp storage ceiling (FIFO purge) |
| `OMP_NUM_THREADS` / `MKL_NUM_THREADS` | `2` | Cap Torch/CPU threads |
| `BACKEND_MEM_LIMIT` / `BACKEND_CPUS` | `3g` / `3` | Backend resource guards |

📄 **Product & architecture guide:** open [`docs/CHEAT_CLIP_PRO_PRD.html`](docs/CHEAT_CLIP_PRO_PRD.html)
(use *Print → Save as PDF* for a PDF copy).

---

## 🔄 Updating to the Latest Version

To update Cheat Clip PRO to the latest release:

```bash
git pull
npm install
pip install -r backend/requirements.txt
```
*(Make sure your virtual environment is activated if you created one)*

---

## 🔑 Free Google Gemini API Key (Takes 1 Minute)

Cheat Clip PRO uses Google's AI to find the best viral moments for free:
1. Go to **[Google AI Studio](https://aistudio.google.com/)** and sign in with any Google account.
2. Click **"Get API key"** (or **"Create API key"**).
3. Copy your key (starts with `AIzaSy...`).
4. Paste it into the **Gemini API Key** field in the app.

> 💡 **Tip:** You can also type `mock` in the API Key box to test out the app with sample data without an API key!

---

## 🎯 How to Use

1. **Paste a YouTube URL** — Enter any podcast, stream, or video link.
2. **Choose Duration** — Pick `~15s` (fast hooks), `~30s` (standard shorts), or `~60s` (story clips).
3. **Click "Analyze Video"** — The AI finds the most exciting moments using YouTube audience retention data.
4. **Customize in Clip Studio** — Adjust your video style:
   * **Frame & Crop**: Fullscreen 9:16 vertical, square, or split-screen facecam.
   * **Face Tracking**: Automatically keeps the speaker in the center of the frame.
   * **Subtitles**: Choose viral animated karaoke caption styles and fonts.
   * **Branding & Audio**: Add your watermark logo, background music, and hook sound effects.
   * **Hardware Acceleration**: Choose your graphics card (NVIDIA, AMD, Intel) or CPU.
5. **Batch Render & Download** — Click **Batch Render**, then download all your finished videos together in one **.ZIP** file!

---

## ❓ Common Problems & Easy Fixes

### 1. "Failed to render video" or `The system cannot find the file specified`
* **Cause:** `ffmpeg` or `yt-dlp` is missing on your computer.
* **Fix:**
  * **Windows (PowerShell):**
    ```powershell
    winget install Gyan.FFmpeg
    winget install yt-dlp.yt-dlp
    ```
    *(Then close and reopen your terminal)*
  * **Mac (Terminal):**
    ```bash
    brew install ffmpeg-full yt-dlp
    ```
  * Or install directly via Python: `pip install yt-dlp`

### 2. `No such filter: 'subtitles'`
* **Cause:** FFmpeg was installed without the libass subtitle filter.
* **Fix (macOS):**
  ```bash
  brew install ffmpeg-full
  ```
  Restart the backend after installation. The app automatically prefers Homebrew's subtitle-capable `ffmpeg-full` binary.

### 3. "Sign in to confirm you're not a bot"
* **Cause:** YouTube blocks video downloads if too many requests are sent without logging in.
* **Fix:** Click the 🍪 **Cookies** button in the top navigation bar, export your YouTube cookies using a free browser extension (like *Get cookies.txt locally*), and paste them into the app.

### 4. Does this work on AMD graphics cards and Mac?
* **Yes!** Cheat Clip PRO automatically supports:
  * **NVIDIA** (`h264_nvenc`)
  * **AMD** (`h264_amf` on Radeon GPUs & Ryzen CPUs)
  * **Intel** (`h264_qsv` on Arc & UHD Graphics)
  * **Apple Mac & CPU Software** (`libx264` universal high-speed fallback)
* You can switch your preferred hardware acceleration encoder anytime in the Render Settings or History card.

---

## 📄 License

Distributed under the **MIT License**. Free for personal and commercial use!
