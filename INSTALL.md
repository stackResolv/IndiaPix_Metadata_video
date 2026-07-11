# IndiaPix Metadata Automation System — Installation Guide

## Prerequisites

| Software | Version | Where to Get It |
|---|---|---|
| **Python** | 3.10+ (3.9 works but 3.10+ recommended) | [python.org](https://python.org) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) |
| **FFmpeg** | Latest stable | See below |
| **Anthropic API Key** | — | [console.anthropic.com](https://console.anthropic.com) |

## 1. Install FFmpeg (Windows)

1. Download FFmpeg from: https://ffmpeg.org/download.html
2. Choose **"Windows builds from gyan.dev"** → **"ffmpeg-release-full.7z"**
3. Extract the downloaded `.7z` file to `C:\ffmpeg` (you can use [7-Zip](https://7-zip.org/) to extract it)
4. Add FFmpeg to your system PATH:
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Go to the **Advanced** tab → **Environment Variables**
   - Under "System variables", find and select `Path`, click **Edit**
   - Click **New** and add `C:\ffmpeg\bin`
   - Click OK on all windows
5. **Restart your terminal** (or log out and back in)
6. Verify FFmpeg is installed:
   ```powershell
   ffmpeg -version
   ffprobe -version
   ```
   Both commands should print version information without errors.

## 2. Install Python (Windows)

1. Go to https://python.org → Downloads → Download Python 3.10+
2. Run the installer
3. **IMPORTANT:** Check the box **"Add Python to PATH"** at the bottom of the installer
4. Click **Install**
5. Verify installation:
   ```powershell
   python --version
   pip --version
   ```

## 3. Install Node.js (Windows)

1. Go to https://nodejs.org → Download the **LTS** version (18+)
2. Run the installer (default settings are fine)
3. Verify installation:
   ```powershell
   node --version
   npm --version
   ```

## 4. Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`)
5. **Keep this key safe** — you'll need it in Step 5

## 5. Setup & Run

### Option A: Quick Start (Recommended)

1. **Open PowerShell** in the project folder:
   - Navigate to the project folder in File Explorer
   - Hold `Shift` and right-click → **"Open PowerShell window here"**
   - (Or type `powershell` in the address bar)

2. **Run the start script:**
   ```powershell
   .\start.ps1
   ```

   If you see a security error about execution policy, run this first:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```
   Then run `.\start.ps1` again.

3. **Add your API key:**
   - After the first run, the script will create a file at `backend\.env`
   - Open `backend\.env` in Notepad (right-click → Open with → Notepad)
   - Replace the placeholder with your real Anthropic key:
     ```
     ANTHROPIC_API_KEY=sk-ant-your-real-key-here
     ```
   - Save the file

4. **Restart the servers:**
   - Press `Ctrl+C` in PowerShell to stop
   - Run `.\start.ps1` again

5. **Open the app:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option B: Manual Setup (Run in separate PowerShell windows)

**Terminal 1 — Backend:**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Now open `backend\.env` in Notepad, add your Anthropic API key, save. Then:
```powershell
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm install
npx next dev --port 3000
```

## 6. Access the Application

| Component | URL |
|---|---|
| **Frontend UI** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |

## 7. Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| `'python' is not recognized` | Python not in PATH | Reinstall Python and check "Add Python to PATH" |
| `'npm' is not recognized` | Node.js not installed or not in PATH | Reinstall Node.js from nodejs.org |
| `FFmpeg not found` error | FFmpeg not installed or not on PATH | Install FFmpeg (see Step 1) and restart terminal |
| "API key not configured" | Missing or placeholder API key | Edit `backend\.env` with real key |
| Upload fails with 413 | File too large | Max is 2GB; check file size |
| "Execution Policy" error | PowerShell restricts running scripts | Run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Port 8000/3000 already in use | Another app on that port | Change port in `backend\.env` or use `--port` flag |
| `pip` not recognized | Python not fully installed | Run: `python -m ensurepip` |

## 8. Supported File Formats

**Videos:** MP4, MOV, AVI, MXF, M4V, WMV
**Images (Phase 2):** JPG, PNG, TIFF, CR2, NEF, ARW
**Max file size:** 2,000 MB (2 GB)
**Max frames per video:** 15 (Claude limit is 20 images)