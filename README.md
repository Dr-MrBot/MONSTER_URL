# 👾 MONSTER_URL 2.0 — Advanced Target & Public URL Hub

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0.0-00ff88?style=for-the-badge&logo=appveyor" alt="Version 2.0">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Termux-00e5ff?style=for-the-badge" alt="Platforms">
  <img src="https://img.shields.io/badge/Developer-Mohammad%20Fahad-ffaa00?style=for-the-badge" alt="Developer">
  <img src="https://img.shields.io/badge/License-MIT-ff3366?style=for-the-badge" alt="License">
</p>

---

## 👤 Developer Information

- **Developer Name**: **Mohammad Fahad**
- **Instagram**: [dr_mr.bot](https://www.instagram.com/dr_mr.bot/)
- **GitHub**: [Dr-MrBot](https://github.com/Dr-MrBot)

---

## ⚠️ Legal & Ethical Disclaimer

> **IMPORTANT NOTICE:** This tool is designed strictly for **educational, academic final-year project demonstration, authorized security testing, and research purposes**. 
> The developer (**Mohammad Fahad**) and contributors assume no liability and are not responsible for any misuse, illegal activities, or unauthorized testing conducted with this software. Always obtain explicit permission before testing on any system or device.

---

## 🚀 Overview & Key Features

**MONSTER_URL 2.0** is an advanced multi-platform web application built with **Flask** and **Vanilla JavaScript**. It generates shareable, token-based public links that allow users to collect and monitor real device telemetry, GPS location, hardware footprints, camera snapshots, microphone audio, and participant form submissions in real time from a centralized admin console.

### 🌟 What's New in MONSTER_URL 2.0:

- 🌐 **Persistent Public HTTPS Tunnels**: Built-in `TunnelManager` automatically establishes and maintains free public HTTPS tunnels (Cloudflare TryCloudflare / Serveo SSH) with continuous auto-reconnection so your links stay active without manual port forwarding.
- 📱 **100% Fully Responsive UI**: Meticulously designed for mobile phones, tablets, and PCs. Smooth glassmorphism aesthetic with cyberpunk neon styling (`#070b12` dark background, glowing green/cyan accents).
- 🎮 **Real Device Hardware Footprinting**: Captures WebGL GPU renderer details (`WEBGL_debug_renderer_info`), screen resolution & pixel ratio, RAM estimate (`navigator.deviceMemory`), CPU logical core count (`navigator.hardwareConcurrency`), timezone, User-Agent, and client IP.
- 🎁 **Contest & Giveaway Entry Form Template**: Includes a participant form (`contest`) capturing Full Name, Social Username (`@username`), Phone Number, and Entry Description paragraph, complete with a 24-hour winner selection notice.
- 📝 **User Opinion & Feedback Form Template**: Dedicated survey template (`survey`) for user feedback collection.
- 💻 **All-in-One Diagnostic Template**: A unified system test template (`diag`) that executes GPS, Camera, Microphone, and Hardware footprinting upon interaction.
- 📁 **Media Vault with Download & Deletion**: View captured photos and voice recordings, stream audio, download files in 1-click, and delete individual or all media records.
- 🗑️ **Log & Record Management**: Individual deletion and bulk "Clear All" features across report logs, participant submissions, and media vaults.
- ⚙️ **Dashboard Password Settings**: Admin credential manager inside the settings panel to update admin username and password dynamically.
- 📱 **QR Code Generator**: Automatic mobile QR code generation for every link.
- 🔔 **Toggleable Audio Alert**: Optional audio chime whenever a target interacts or sends reports.

---

## 📁 Repository Structure

```text
MONSTER URL/
├── app.py              # Main Flask application & TunnelManager logic
├── monster.py          # Interactive Python launcher with auto-downloader
├── monster.bat         # One-click Batch script for Windows
├── monster.sh          # Shell execution script for Linux & Android Termux
├── requirements.txt    # Required Python dependencies
├── README.md           # Documentation & project guide
├── bin/                # Standalone binaries (auto-downloaded cloudflared)
├── uploads/            # Captured media files storage
└── templates/          # Jinja2 HTML templates
    ├── client.html     # Client-side target landing page (all themes)
    ├── dashboard.html  # Admin tracking console
    └── login.html      # Secure admin login screen
```

---

## 🛠️ Installation & Setup

### 📦 1. Install Python Dependencies

Run pip installation command:

```bash
pip install -r requirements.txt
```

---

### 🪟 Running on Windows

Double-click **`monster.bat`** or execute in Command Prompt / PowerShell:

```cmd
python monster.py
```

---

### 🐧 Running on Linux

Open terminal and execute:

```bash
chmod +x monster.sh
./monster.sh
```

---

### 📱 Running on Android (Termux)

In the Termux application, run:

```bash
pkg update && pkg install -y python git openssh
git clone https://github.com/Dr-MrBot/MONSTER_URL.git
cd MONSTER_URL
pip install -r requirements.txt
bash monster.sh
```

---

## 🔑 Admin Console Credentials

Access your dashboard locally at **`http://127.0.0.1:5000`** or through your live **Public HTTPS Tunnel URL**:

| Setting | Default Value |
| :--- | :--- |
| **Default Username** | `admin` |
| **Default Password** | `admin` |

> ⚙️ *You can update your username and password anytime from the **Settings ⚙️** tab inside the Dashboard.*

---

## 🎭 Disguise Landing Templates

| Template | Icon | Description |
| :--- | :---: | :--- |
| **System Diagnostic** | 💻 | Unified hardware readiness test (GPS + Camera + Mic + Footprint). |
| **Contest & Giveaway** | 🎁 | Official giveaway draw entry form with 24-hour winner notice. |
| **Feedback Survey** | 📝 | User feedback & opinion submission form. |
| **Package Tracking** | 📦 | Simulated express package delivery & transit map tracker. |
| **Video Call Meeting** | 🎥 | Interactive live video call interface. |
| **Voice Note** | 🎙 | Private encrypted audio recorder landing page. |

---

## 👨‍💻 Developer & Credits

Designed & Developed by **Mohammad Fahad**

- 🐙 **GitHub**: [@Dr-MrBot](https://github.com/Dr-MrBot)
- 📸 **Instagram**: [@dr_mr.bot](https://www.instagram.com/dr_mr.bot/)

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
