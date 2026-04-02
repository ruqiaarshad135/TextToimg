# 🚀 AI Text-to-Image Batch Generator

A powerful, high-performance **CLI & API-based Text-to-Image Generation Tool** that enables users to generate images from text prompts using multiple AI backends with **concurrency, automation, and telemetry support**.

---

## 👩‍💻 Developer
**Ruqia Arshad**

---

## ✨ Features

- 🎨 Text-to-Image Generation (Multiple APIs)
- ⚡ Concurrent Processing (Fast & Scalable)
- 🔁 Retry Mechanism for failed requests
- 📁 Automatic File Saving & Naming
- 🌐 Multiple AI API Support
- 🧠 Smart Response Handling (JSON / Image / URL)
- 📊 Telemetry & Logging System
- 🖥️ CLI Interface with Progress Bars
- 🌍 Optional HTTP API Server

---

## 🛠️ Installation

```bash
git clone https://github.com/your-username/text-to-image-generator.git
cd text-to-image-generator
pip install requests flask
```

---

## 🚀 Usage

### Run CLI
```bash
python text_to_img.py
```

### With Arguments
```bash
python text_to_img.py -p "A futuristic cyberpunk city" -n 10 -c 5
```

---

## 🌐 Run as API Server

```bash
python text_to_img.py --serve
```

### Endpoint:
```
GET /generate?prompt=your_text&api=1
```

---

## 📂 Output Example

```
outputs/
 ├── text2img_001.jpg
 ├── text2img_002.jpg
 └── diffusion_003.png
```

---

## 📊 Logging

Logs stored in:
```
image_generation.jsonl
```

Disable telemetry:
```bash
export IMGGEN_TELEMETRY=0
```

---

## ⚙️ Configuration

```bash
API_BASE=internal
IMGGEN_TELEMETRY=1
```

---

## ⚠️ Disclaimer

This project is for educational purposes only.

---

## ⭐ Support

Give a ⭐ if you like this project!
