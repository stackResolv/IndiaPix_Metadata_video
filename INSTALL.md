# IndiaPix Metadata Automation System — Installation Guide

## Prerequisites

| Software | Version | Where to Get It |
|---|---|---|
| **Python** | 3.10+ (3.9 works but 3.10+ recommended) | [python.org](https://python.org) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) |
| **FFmpeg** | Latest stable | See below |
| **Anthropic API Key** | — | [console.anthropic.com](https://console.anthropic.com) |

## 1. Install FFmpeg

FFmpeg is required for extracting frames from video files.

### macOS (using Homebrew)
```bash
brew install ffmpeg
```

### Windows
1. Download from https://ffmpeg.org/download.html
2. Choose "Windows builds from gyan.dev" → "ffmpeg-release-full.7z"
3. Extract to `C:\ffmpeg`
4. Add `C:\ffmpeg\bin` to your system PATH:
   - Open System Properties → Advanced → Environment Variables
   - Edit the `Path` variable, add `C:\ffmpeg\bin`
   - Click OK and restart your terminal

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install ffmpeg
```

**Verify installation** by running:
```bash
ffmpeg -version
ffprobe -version
```
Both commands should print version information without errors.

## 2. Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys → Create Key
4. Copy the key (starts with `sk-ant-...`)

## 3. Setup & Run

### Option A: Quick Start (Recommended)

**macOS / Linux:**
Run the automated start script from the project root:
```bash
./start.sh
```

**Windows (PowerShell):**
Run the PowerShell start script from the project root:
```powershell
.\start.ps1
```

If you see a security error, you may need to set the execution policy first:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

On the first run, this will:
- Create a Python virtual environment
- Install all Python dependencies
- Install all frontend dependencies
- Create a `.env` file from the template
- Start both the backend and frontend servers

**Important**: After the first start, open `backend/.env` and replace the placeholder API key with your real Anthropic key:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

Then restart the servers (Ctrl+C and run the start script again).

### Option B: Manual Setup

**Backend:**
```bash
cd backend
python3 -m venv venv              # Create virtual environment
source venv/bin/activate          # Activate it (Windows: venv\Scripts\activate)
pip install -r requirements.txt   # Install dependencies
cp .env.example .env              # Create config file
# Edit .env and add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000   # Start backend
```

**Frontend (in a new terminal):**
```bash
cd frontend
npm install                       # Install dependencies
npx next dev --port 3000          # Start frontend
```

## 4. Access the Application

| Component | URL |
|---|---|
| **Frontend UI** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |

## 5. Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| "FFmpeg not found" error | FFmpeg not installed or not on PATH | Install FFmpeg (see Step 1) |
| "API key not configured" | Missing or placeholder API key | Edit `backend/.env` with real key |
| Upload fails with 413 | File too large | Max is 2GB; check file size |
| "Failed to parse Claude response" | API returned unexpected format | Check API key has access to claude-sonnet-4-6-20250514 |
| Port 8000/3000 already in use | Another application using the port | Change port in `backend/.env` or use `--port` flag |
| Windows: `source` not found | Wrong shell command | Use `venv\Scripts\activate` instead |

## 6. Supported File Formats

**Videos:** MP4, MOV, AVI, MXF, M4V, WMV
**Images (Phase 2):** JPG, PNG, TIFF, CR2, NEF, ARW
**Max file size:** 2,000 MB (2 GB)
**Max frames per video:** 15 (Claude limit is 20 images)