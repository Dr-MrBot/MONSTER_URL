#!/usr/bin/env python3
"""
👾 MONSTER_URL 2.0 — Cross-Platform Interactive Launcher
Supports: Windows, Linux, Android (Termux)
"""

import os
import sys
import subprocess
import shutil
import platform

def check_dependencies():
    print(" [*] Checking Python dependencies for MONSTER_URL 2.0...")
    missing = []
    try:
        import flask
    except ImportError:
        missing.append("flask")
    try:
        import requests
    except ImportError:
        missing.append("requests")
        
    if missing:
        print(f" [+] Installing missing packages: {', '.join(missing)}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print(" [✓] Dependencies installed successfully!")
        except Exception as e:
            print(f" [!] Warning: Could not auto-install dependencies: {e}")

    # Check/Download cloudflared binary into bin/ if missing
    bin_dir = os.path.join(os.path.dirname(__file__), "bin")
    os.makedirs(bin_dir, exist_ok=True)
    cloudflared_path = os.path.join(bin_dir, "cloudflared.exe" if os.name == "nt" else "cloudflared")

    if not shutil.which("cloudflared") and not os.path.exists(cloudflared_path):
        print(" [*] Downloading Cloudflare Tunnel binary (cloudflared)...")
        try:
            import urllib.request
            if os.name == "nt":
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            else:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
            
            urllib.request.urlretrieve(cf_url, cloudflared_path)
            if os.name != "nt":
                os.chmod(cloudflared_path, 0o755)
            print(" [✓] Cloudflare Tunnel binary downloaded successfully!")
        except Exception as err:
            print(f" [!] Notice: Automatic cloudflared download fallback to SSH tunnel: {err}")

def main():
    print(r"""
  __  __  ____  _  _  ____ _____ _____ ____   _  _ ____  _     ____  ___  
 |  \/  |/ __ \| \| |/ ___|_   _| ____|  _ \ | || |  _ \| |   |___ \/ _ \ 
 | |\/| | |  | |  ` | \___ \ | | |  _| | |_) || || | |_) | |     __) | | | |
 | |  | | |__| | |` |___) | | | | |___|  _ < | || |  _ <| |___ / __/| |_| |
 |_|  |_|\____/|_|\_|____/  |_| |_____|_| \_(_)__|_| \_\_____|_____|\___/ 
                                                                           
                   🚀 MONSTER_URL 2.0 - TARGET & PUBLIC URL HUB
    """)

    system_info = platform.system()
    machine_info = platform.machine()
    is_termux = "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")
    
    print(f" [+] Operating System : {system_info} ({machine_info})")
    if is_termux:
        print(" [+] Environment      : Android Termux Detected 📱")
    print(f" [+] Python Version   : {platform.python_version()}")
    print("-" * 65)

    check_dependencies()

    print("\n [*] Starting MONSTER_URL 2.0 Server & Automatic Public Tunnel...")
    print(" [*] Press Ctrl+C to stop the server anytime.\n")

    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    try:
        subprocess.run([sys.executable, app_path])
    except KeyboardInterrupt:
        print("\n [!] MONSTER_URL 2.0 Server Shutdown Cleanly.")

if __name__ == "__main__":
    main()
