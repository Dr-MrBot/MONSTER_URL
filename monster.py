#!/usr/bin/env python3
"""
👾 MONSTER_URL 2.0 — Cross-Platform Interactive Launcher
Supports: Windows, Linux, Android (Termux), macOS
Zero-Configuration Cloudflare Tunneling
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

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
    exe_name = "cloudflared.exe" if os.name == "nt" else "cloudflared"
    cloudflared_path = os.path.join(bin_dir, exe_name)

    is_termux = "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")
    
    # On Termux, attempt pkg install cloudflared if not present
    if is_termux and not shutil.which("cloudflared") and not os.path.exists(cloudflared_path):
        try:
            print(" [*] Termux detected. Checking for native cloudflared package...")
            subprocess.run(["pkg", "install", "-y", "tur-repo"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["pkg", "install", "-y", "cloudflared"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass

    if not shutil.which("cloudflared") and not os.path.exists(cloudflared_path):
        print(" [*] Cloudflare Tunnel binary (cloudflared) not found. Downloading...")
        try:
            import urllib.request
            sys_name = platform.system().lower()
            machine = platform.machine().lower()
            
            if os.name == "nt" or sys_name == "windows":
                if "64" in machine or "amd64" in machine or "x86_64" in machine:
                    cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
                else:
                    cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe"
            elif "darwin" in sys_name:
                if "arm64" in machine or "aarch64" in machine:
                    cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz"
                else:
                    cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
            elif "aarch64" in machine or "arm64" in machine:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
            elif "arm" in machine:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
            elif "386" in machine or "i686" in machine:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386"
            else:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
            
            print(f" [+] Architecture detected: {sys_name} ({machine}). Downloading from: {cf_url}")
            
            if cf_url.endswith(".tgz"):
                import tarfile
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".tgz", delete=False) as tmp_f:
                    tmp_tar_path = tmp_f.name
                urllib.request.urlretrieve(cf_url, tmp_tar_path)
                with tarfile.open(tmp_tar_path, "r:gz") as tar:
                    tar.extract("cloudflared", path=bin_dir)
                try:
                    os.remove(tmp_tar_path)
                except Exception:
                    pass
            else:
                urllib.request.urlretrieve(cf_url, cloudflared_path)
                
            if os.name != "nt":
                os.chmod(cloudflared_path, 0o755)
            print(" [✓] Cloudflare Tunnel binary downloaded successfully!")
        except Exception as err:
            print(f" [!] Notice: Automatic cloudflared download failed: {err}")

def main():
    print(r"""
  __  __  ____  _  _  ____ _____ _____ ____   _  _ ____  _     ____  ___  
 |  \/  |/ __ \| \| |/ ___|_   _| ____|  _ \ | || |  _ \| |   |___ \/ _ \ 
 | |\/| | |  | |  ` | \___ \ | | |  _| | |_) || || | |_) | |     __) | | | |
 | |  | | |__| | |` |___) | | | | |___|  _ < | || |  _ <| |___ / __/| |_| |
 |_|  |_|\____/|_|\_|____/  |_| |_____|_| \_(_)__|_| \_\_____|_____|\___/ 
                                                                           
                   🚀 MONSTER_URL 2.0 - TARGET & PUBLIC URL HUB
                   🛡 Powered by Zero-Config Cloudflare Tunnel
    """)

    system_info = platform.system()
    machine_info = platform.machine()
    is_termux = "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")
    
    print(f" [+] Operating System : {system_info} ({machine_info})")
    if is_termux:
        print(" [+] Environment      : Android Termux Detected 📱")
    print(f" [+] Python Version   : {platform.python_version()}")
    print("-" * 65)

    load_env()
    check_dependencies()

    print("\n [*] Starting MONSTER_URL 2.0 Server & Automatic Cloudflare Public Tunnel...")
    print(" [*] Press Ctrl+C to stop the server anytime.\n")

    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    try:
        subprocess.run([sys.executable, app_path])
    except KeyboardInterrupt:
        print("\n [!] MONSTER_URL 2.0 Server Shutdown Cleanly.")

if __name__ == "__main__":
    main()
