#!/usr/bin/env bash
# 👾 MONSTER_URL 2.0 Launcher for Linux & Termux

clear
echo "===================================================================="
echo " 👾 MONSTER_URL 2.0 — Linux & Termux Launcher"
echo "===================================================================="

# Check if running in Termux
if [ -d "/data/data/com.termux" ]; then
    echo " [*] Android Termux Environment Detected."
    if ! command -v python &> /dev/null; then
        echo " [+] Installing python..."
        pkg update && pkg install -y python openssh
    fi
else
    echo " [*] Linux Environment Detected."
    if ! command -v python3 &> /dev/null; then
        echo " [!] python3 is required. Please install python3."
        exit 1
    fi
fi

# Run python launcher
if command -v python3 &> /dev/null; then
    python3 monster.py
elif command -v python &> /dev/null; then
    python monster.py
else
    echo " [!] Python executable not found."
    exit 1
fi
