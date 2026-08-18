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
    try:
        import pyngrok
    except ImportError:
        missing.append("pyngrok")
        
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
            machine = platform.machine().lower()
            if os.name == "nt":
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            elif "aarch64" in machine or "arm64" in machine:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
            elif "arm" in machine:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
            elif "386" in machine or "i686" in machine:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386"
            else:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
            
            print(f" [+] Architecture detected ({machine}). Downloading from: {cf_url}")
            urllib.request.urlretrieve(cf_url, cloudflared_path)
            if os.name != "nt":
                os.chmod(cloudflared_path, 0o755)
            print(" [✓] Cloudflare Tunnel binary downloaded successfully!")
        except Exception as err:
            print(f" [!] Notice: Automatic cloudflared download failed: {err}")

def setup_ngrok():
    is_termux = "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")
    is_linux = platform.system().lower() == "linux"
    
    # Auto-check ngrok for Termux / Linux
    if (is_termux or is_linux) and not shutil.which("ngrok"):
        print(" [*] Ngrok not found in system PATH. Attempting automatic installation...")
        if is_termux:
            try:
                subprocess.run(["pkg", "install", "-y", "tur-repo"], check=False)
                subprocess.run(["pkg", "install", "-y", "ngrok"], check=False)
            except Exception:
                pass
        elif is_linux:
            print(" [i] On Linux, pyngrok will manage ngrok binary automatically.")

    # Check for saved NGROK_AUTHTOKEN in environment / .env
    token = os.environ.get("NGROK_AUTHTOKEN", "").strip()
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    if not token and (is_termux or is_linux):
        print("\n" + "="*65)
        print(" 🔑 NGROK AUTHTOKEN SETUP (Termux / Linux Public URL Forwarding)")
        print("    Get your free token at: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("    This will be asked ONLY ONCE and saved to .env for future runs.")
        print("="*65)
        try:
            token = input(" [>] Enter Ngrok AuthToken (or press Enter to skip): ").strip()
            if token:
                os.environ["NGROK_AUTHTOKEN"] = token
                with open(env_path, "a", encoding="utf-8") as f:
                    f.write(f"\nNGROK_AUTHTOKEN={token}\n")
                print(" [✓] Ngrok AuthToken saved to .env file successfully!\n")
        except Exception as e:
            print(f" [!] Error saving token: {e}")

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

    load_env()
    setup_ngrok()
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
