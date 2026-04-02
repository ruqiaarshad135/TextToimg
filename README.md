# 🎨 INNO CYBER AI Image Generator

**Batch Image Generation Tool by M.Sabir Ali**

A powerful command-line tool for generating AI images in batch using multiple API options including Text-to-Image and Diffusion AI models.

---

## 📋 Table of Contents
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [API Server Mode](#api-server-mode)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

- **Multiple AI APIs**: Choose between Text-to-Image and Diffusion AI models
- **Batch Generation**: Generate up to 200 images in a single run
- **Concurrent Processing**: Multi-threaded for faster generation
- **Auto Retry**: Automatic retry on failures
- **Progress Tracking**: Real-time progress display
- **API Server Mode**: Run as HTTP API server
- **Telemetry & Analytics**: Session tracking and analytics
- **Multiple Output Formats**: Supports JPG, PNG, WebP

---

## 🖥️ System Requirements

- **Operating System**: Windows 10/11, Linux, or macOS
- **Python**: Version 3.8 or higher
- **Internet Connection**: Required for API calls
- **Disk Space**: At least 500MB free for outputs

---

## 📦 Installation

### Step 1: Install Python
If Python is not installed, download from [python.org](https://www.python.org/downloads/)

**Verify Python installation:**
```powershell
python --version
```

### Step 2: Clone or Download Project
Download the project to your desired location, e.g.:
```
C:\Users\YourName\Desktop\My Projects\txt_to_img@inno
```

### Step 3: Create Virtual Environment
Open PowerShell in the project directory and run:

```powershell
# Navigate to project directory
cd "C:\Users\Muhammad Sabir Ali\Desktop\My Projects\txt_to_img@inno"

# Create virtual environment
python -m venv .venv
```

### Step 4: Activate Virtual Environment

**On Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**If you get execution policy error, run this first:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**On Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**On Linux/Mac:**
```bash
source .venv/bin/activate
```

### Step 5: Install Dependencies

```powershell
# Ensure pip is up to date
python -m pip install --upgrade pip

# Install required packages
pip install requests flask
```

**Or install from requirements.txt (if available):**
```powershell
pip install -r requirements.txt
```

---

## 🚀 Quick Start

### Basic Usage (Interactive Mode)

```powershell
# Activate virtual environment first
.\.venv\Scripts\Activate.ps1

# Run the script
python text_to_img@inno.py
```

The script will prompt you for:
1. **API Selection** (1 for Text-to-Image, 2 for Diffusion)
2. **Prompt** (your image description)
3. **Count** (number of images to generate, 1-200)

### Example Session:
```
Available APIs:
  1. Text-to-Image
     High-quality text-to-image generation (generates 2 images per request)
  2. Diffusion
     Advanced AI diffusion model powered by Stable Diffusion 3.5

Select your Choice! (1-2): 1

Enter prompt: a beautiful sunset over mountains

How many img you want? (1-200): 5
```

---

## 📖 Usage

### Command-Line Arguments

```powershell
python text_to_img@inno.py [OPTIONS]
```

**Options:**

| Argument | Description | Default |
|----------|-------------|---------|
| `-p, --prompt` | Image prompt text | Interactive |
| `-n, --count` | Number of images (1-200) | Interactive |
| `-o, --outdir` | Output directory | `outputs` |
| `-t, --timeout` | Request timeout (seconds) | `60` |
| `--retries` | Retry attempts per request | `3` |
| `-c, --concurrency` | Parallel workers | `10` |
| `--prefix` | Filename prefix | `""` |
| `--manifest` | JSONL manifest file path | None |
| `--quiet` | Minimal output | `False` |
| `--no-color` | Disable ANSI colors | `False` |
| `--serve` | Start HTTP API server | `False` |
| `--host` | API server host | `0.0.0.0` |
| `--port` | API server port | `8000` |

### Example Commands

**Generate 10 images with a specific prompt:**
```powershell
python text_to_img@inno.py -p "a futuristic city at night" -n 10
```

**Generate with custom output directory:**
```powershell
python text_to_img@inno.py -p "anime character" -n 5 -o "my_images"
```

**Generate with prefix for organization:**
```powershell
python text_to_img@inno.py -p "landscape" -n 3 --prefix "nature_"
```

**High concurrency for faster generation:**
```powershell
python text_to_img@inno.py -p "abstract art" -n 20 -c 20
```

**Quiet mode (minimal output):**
```powershell
python text_to_img@inno.py -p "portrait" -n 5 --quiet
```

**Save manifest log:**
```powershell
python text_to_img@inno.py -p "cars" -n 10 --manifest "generation_log.jsonl"
```

---

## 🌐 API Server Mode

Run as an HTTP API server for integration with other applications.

### Start Server:

```powershell
python text_to_img@inno.py --serve
```

**Custom host and port:**
```powershell
python text_to_img@inno.py --serve --host 127.0.0.1 --port 5000
```

### API Endpoints:

#### GET/POST `/generate`

**Parameters:**
- `prompt` (required): Image description
- `api` (optional): API choice (1 or 2, default: 1)

**Example GET Request:**
```
http://localhost:8000/generate?prompt=sunset&api=1
```

**Example POST Request (JSON):**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "beautiful landscape", "api": 2}'
```

**Response:**
```json
{
  "ok": true,
  "used_prompt": "beautiful landscape",
  "api_used": "Diffusion",
  "duration_seconds": 3.45,
  "image_urls": ["https://..."],
  "creator": "INNO CYBER"
}
```

#### GET `/`
Returns API information and available endpoints.

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set system environment variables:

```bash
# API Configuration
API_BASE=internal                    # or external API URL
API_TIMEOUT=60                       # Request timeout in seconds

# Telemetry (Optional)
IMGGEN_TELEMETRY=1                   # 1 = enabled, 0 = disabled
IMGGEN_TELEMETRY_URL=http://...     # Custom telemetry endpoint
IMGGEN_LOG=image_generation.jsonl   # Log file path

# Server Mode
HOST=0.0.0.0                         # API server host
PORT=8000                            # API server port
```

### Available APIs

1. **Text-to-Image** (`text2img`)
   - URL: `https://text-to-img.apis-bj-devs.workers.dev/`
   - Generates 2 images per request
   - Best for: General purpose, varied styles

2. **Diffusion** (`diffusion`)
   - URL: `https://diffusion-ai.bjcoderx.workers.dev/`
   - Powered by Stable Diffusion 3.5
   - Best for: High-quality, detailed images

---

## 💡 Examples

### Example 1: Batch Portrait Generation
```powershell
python text_to_img@inno.py -p "professional headshot, studio lighting" -n 10 --prefix "portrait_"
```

### Example 2: Landscape Collection
```powershell
python text_to_img@inno.py -p "mountain landscape, golden hour" -n 15 -o "landscapes" -c 15
```

### Example 3: Multiple Prompts via Loop
```powershell
# Create a batch script
$prompts = @("sunset", "forest", "ocean", "city")
foreach ($p in $prompts) {
    python text_to_img@inno.py -p $p -n 5 --prefix "${p}_"
}
```

### Example 4: Using Different APIs
```powershell
# Use Text-to-Image API
python text_to_img@inno.py -p "anime character"

# When prompted, select: 1

# For Diffusion API
python text_to_img@inno.py -p "photorealistic portrait"

# When prompted, select: 2
```

---

## 🛠️ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'requests'"

**Solution:**
```powershell
# Ensure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install requests flask
```

### Issue: "pip is not installed"

**Solution:**
```powershell
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

### Issue: Virtual environment activation fails (PowerShell)

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Script runs but no images generated

**Possible causes:**
1. No internet connection
2. API timeout - increase with `-t 120`
3. API rate limiting - reduce concurrency with `-c 5`

**Check logs:**
```powershell
# View the log file
cat image_generation.jsonl
```

### Issue: Images save as JSON files

This happens when the API returns JSON instead of direct images. The script handles this automatically by:
- Downloading URLs from JSON response
- Saving JSON for debugging if no URLs found

### Issue: Slow generation

**Solutions:**
- Increase concurrency: `-c 20`
- Check internet speed
- Try different API (option 1 vs 2)
- Reduce timeout if stuck: `-t 30`

---

## 📂 Output Structure

```
outputs/
├── text2img_001.jpg
├── text2img_002.jpg
├── text2img_003.png
├── diffusion_001.jpg
└── ...
```

**With prefix:**
```
outputs/
├── nature_text2img_001.jpg
├── nature_text2img_002.jpg
└── ...
```

---

## 📊 Log Files

### image_generation.jsonl
Contains session information and generation events:
```json
{"type": "app_start", "ts": 1234567890, "properties": {...}}
{"type": "generation_started", "ts": 1234567891, "properties": {...}}
{"type": "generation_completed", "ts": 1234567900, "properties": {...}}
```

### Manifest File (Optional)
When using `--manifest`, each generated image is logged:
```json
{"index": 1, "path": "outputs/img_001.jpg", "time_utc": "2025-11-16T..."}
{"index": 2, "path": "outputs/img_002.jpg", "time_utc": "2025-11-16T..."}
```

---

## 🔧 Advanced Usage

### Running Without Virtual Environment

```powershell
# Using full path to Python executable
"C:\Users\Muhammad Sabir Ali\Desktop\My Projects\txt_to_img@inno\.venv\Scripts\python.exe" text_to_img@inno.py
```

### Batch Processing Script

Create `batch_generate.ps1`:
```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Generate multiple sets
python text_to_img@inno.py -p "sunset" -n 10 --prefix "sunset_"
python text_to_img@inno.py -p "forest" -n 10 --prefix "forest_"
python text_to_img@inno.py -p "ocean" -n 10 --prefix "ocean_"

# Deactivate
deactivate
```

Run it:
```powershell
.\batch_generate.ps1
```

### Integration with Other Scripts

```python
import subprocess
import json

def generate_images(prompt, count=5, api=1):
    cmd = [
        "python", "text_to_img@inno.py",
        "-p", prompt,
        "-n", str(count),
        "--quiet",
        "--manifest", "temp_manifest.jsonl"
    ]
    subprocess.run(cmd)
    
    # Read generated files
    with open("temp_manifest.jsonl") as f:
        files = [json.loads(line)["path"] for line in f]
    
    return files

# Use it
images = generate_images("beautiful sunset", count=3)
print(f"Generated {len(images)} images: {images}")
```

---

## 📱 Contact & Support

- **Brand**: INNO CYBER
- **Owner**: M.Sabir Ali
- **Lab**: INNO CYBER (CHF)
- **Version**: v2.5

**WhatsApp Channels:**
- https://whatsapp.com/channel/0029Vb636xOFy72JLTU4ow1H
- https://chat.whatsapp.com/BFvFDDRFwZ7CTfIXxRlwNW

---

## 📄 License

© 2025 INNO CYBER - All Rights Reserved

---

## 🎯 Quick Reference

### Complete Setup (Fresh System)
```powershell
# 1. Install Python from python.org (if not installed)

# 2. Navigate to project
cd "C:\Users\Muhammad Sabir Ali\Desktop\My Projects\txt_to_img@inno"

# 3. Create virtual environment
python -m venv .venv

# 4. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 5. Install dependencies
python -m pip install --upgrade pip
pip install requests flask

# 6. Run the script
python text_to_img@inno.py

# 7. Follow prompts
# Select API: 1 or 2
# Enter prompt: "your image description"
# Enter count: 1-200
```

### Daily Use
```powershell
# Navigate to project
cd "C:\Users\Muhammad Sabir Ali\Desktop\My Projects\txt_to_img@inno"

# Activate environment
.\.venv\Scripts\Activate.ps1

# Run
python text_to_img@inno.py -p "your prompt" -n 10

# When done
deactivate
```

---

**Happy Generating! 🎨✨**
