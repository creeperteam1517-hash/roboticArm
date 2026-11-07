#!/bin/bash
# Installs Tailscale on the Pi from Tailscale's official package site, then signs the Pi in.
# Run from the PC with .\install_tailscale. You type the Pi's password when asked.
set -e

CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
BASE="https://pkgs.tailscale.com/stable/debian"

if command -v tailscale >/dev/null; then
    echo "Tailscale is already installed."
else
    echo "Step 1 of 2: Installing Tailscale from $BASE ..."
    echo "Type the Pi's password if asked. Nothing shows as you type. That's normal."
    curl -fsSL "$BASE/$CODENAME.noarmor.gpg" | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
    curl -fsSL "$BASE/$CODENAME.tailscale-keyring.list" | sudo tee /etc/apt/sources.list.d/tailscale.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq tailscale
fi

echo
echo "Step 2 of 2: Connecting the Pi to your Tailscale account."
echo "Open the link below in a browser, sign in (or make a free account), and approve the Pi."
sudo tailscale up
echo
echo "All done! The Pi is on your Tailscale network. Nothing is public yet."
