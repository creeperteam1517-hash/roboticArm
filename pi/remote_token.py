"""Make a new secret code for claude.ai Jarvis to send arm commands, then restart Jarvis.

Run from the PC with .\\remote_token. The code is shown once. Copy it into claude.ai Jarvis.
Making a new code locks out the old one.
"""
import secrets

from set_keys import read_existing, restart_jarvis, save


def main():
    values = read_existing()
    values["JARVIS_REMOTE_TOKEN"] = secrets.token_urlsafe(24)
    save(values)
    print()
    print("Your new secret code (keep it private, like a password):")
    print()
    print("    " + values["JARVIS_REMOTE_TOKEN"])
    print()
    print("Copy it into claude.ai Jarvis when it asks. Any older code no longer works.")
    print("Restarting Jarvis...")
    restart_jarvis()


if __name__ == "__main__":
    main()
