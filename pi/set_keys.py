"""Save Jarvis's Claude and ElevenLabs keys on the Pi, then restart Jarvis.

Run from the PC with .\\set_keys. You type the keys yourself and they don't show on screen.
Leave a key blank to keep the one already saved.
"""
import getpass
import os
import subprocess
from pathlib import Path

KEY_FILE = Path.home() / ".config" / "jarvis" / "keys.env"
NAMES = [
    ("ANTHROPIC_API_KEY", "Claude API key (starts with sk-ant-)"),
    ("ELEVENLABS_API_KEY", "ElevenLabs API key, for George's voice (optional)"),
]


def read_existing():
    values = {}
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text().splitlines():
            name, _, value = line.partition("=")
            if value:
                values[name.strip()] = value.strip()
    return values


def save(values):
    """Write every saved value, readable only by this user."""
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEY_FILE.parent, 0o700)
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        for name, value in values.items():
            if value:
                handle.write(f"{name}={value}\n")
    os.chmod(KEY_FILE, 0o600)


def restart_jarvis():
    restarted = subprocess.run(["systemctl", "--user", "restart", "jarvis"]).returncode == 0
    print("Done! Refresh the Jarvis page." if restarted else "Saved, but Jarvis didn't restart. Run .\\deploy.")


def main():
    values = read_existing()
    print("Type or paste each key, then press Enter. Nothing shows as you type. That's normal.")
    for name, label in NAMES:
        note = " (one is saved; press Enter to keep it)" if name in values else ""
        entered = getpass.getpass(f"{label}{note}: ").strip()
        if entered:
            values[name] = entered
    save(values)
    print("Saved on the Pi only. Restarting Jarvis...")
    restart_jarvis()


if __name__ == "__main__":
    main()
