"""Jarvis: a small web server on the Pi with buttons, sliders and a chat that can move the arm.

Starting this server never moves the arm. Only a button, slider, chat request or Stop touches the servos.
Uses Python's standard library, smbus2 through arm.py, and the anthropic library for chat.
"""
import hmac
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import jarvis_chat
import jarvis_data
from arm import Arm, JOINTS, check_angle
from moves import DELAYS, MOVES

HOST = os.environ.get("JARVIS_HOST", "0.0.0.0")
PORT = int(os.environ.get("JARVIS_PORT", "8000"))
PAGE = Path(__file__).with_name("jarvis.html")
# The page can also be opened at this private Tailscale address (secure, so the microphone works).
TAILSCALE_HOST = os.environ.get("JARVIS_TS_HOST", "the-coolest-raspberry-pi.taile11589.ts.net")

DEFAULT_DELAY = 1.0
HOLD_SECONDS = 10         # a slider or chat position relaxes after this long, so servos don't strain
# The shoulder and elbow stay powered after a move (only Stop relaxes them). Relaxing them lets the
# arm sag and makes the Pi forget where they are, so their next move would jump instead of gliding.
KEEP_POWERED = {"shoulder", "elbow"}
TESTED_JOINTS = {"claw", "base", "shoulder", "elbow"}   # the page locks any others until unlocked
MAX_BODY_BYTES = 8192


class Busy(Exception):
    pass


class HardwareError(Exception):
    pass


class Jarvis:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.arm = None
        self.worker = None
        self.running = None
        self.step = None
        self.last_angles = {}
        self.held = {}
        self.error = None

    def _with_arm(self, action):
        """Run a hardware action. The board is only touched once a command needs it."""
        try:
            if self.arm is None:
                self.arm = Arm()
            action(self.arm)
            self.error = None
        except OSError as problem:
            self.arm = None
            self.error = "Jarvis can't reach the servo board."
            raise HardwareError(self.error) from problem

    def _move(self, joint, angle):
        self._with_arm(lambda arm: arm.move(joint, angle))
        self.last_angles[joint] = angle

    def _release(self, joint):
        self._with_arm(lambda arm: arm.release(joint))
        self.held.pop(joint, None)

    def state(self):
        with self.lock:
            return {
                "running": self.running,
                "step": self.step,
                "error": self.error,
                "chat_ready": jarvis_chat.chat_ready(),
                "voice_ready": jarvis_chat.voice_ready(),
                "hold_seconds": HOLD_SECONDS,
                "moves": list(MOVES),
                "joints": [
                    {
                        "name": name,
                        "channel": channel,
                        "low": low,
                        "high": high,
                        "tested": name in TESTED_JOINTS,
                        "last_angle": self.last_angles.get(name),
                        "held": name in self.held,
                        "keep_powered": name in KEEP_POWERED,
                    }
                    for name, (channel, low, high) in JOINTS.items()
                ],
            }

    def start_move(self, name):
        if name not in MOVES:
            raise ValueError(f"There's no move called '{name}'.")
        for joint, angle in MOVES[name]:
            check_angle(joint, angle)
        with self.lock:
            if self.running:
                raise Busy(f"Jarvis is already running {self.running}.")
            self.stop_event.clear()
            self.running = name
            self.step = None
            self.worker = threading.Thread(target=self._run_move, args=(name,), daemon=True)
            self.worker.start()

    def _run_move(self, name):
        delay = DELAYS.get(name, DEFAULT_DELAY)
        used = set()
        try:
            for joint, angle in MOVES[name]:
                if self.stop_event.is_set():
                    break
                with self.lock:
                    self._move(joint, angle)
                    self.step = f"{joint} {angle}"
                    used.add(joint)
                if self.stop_event.wait(delay):
                    break
        except HardwareError:
            pass
        finally:
            with self.lock:
                try:
                    for joint in used:
                        if joint in KEEP_POWERED:
                            self.held[joint] = time.monotonic()
                        else:
                            self._release(joint)
                except HardwareError:
                    pass
                self.running = None
                self.step = None

    def set_joint(self, joint, angle):
        check_angle(joint, angle)
        with self.lock:
            if self.running:
                raise Busy(f"Jarvis is running {self.running}. Wait for it, or press Stop.")
            self._move(joint, angle)
            self.held[joint] = time.monotonic()

    def stop(self):
        """Cancel any move and relax every joint."""
        self.stop_event.set()
        worker = self.worker
        if worker and worker.is_alive():
            worker.join(timeout=2)
        with self.lock:
            if self.arm is None:
                return
            for joint in JOINTS:
                self._release(joint)

    def relax_expired_holds(self):
        with self.lock:
            now = time.monotonic()
            for joint, since in list(self.held.items()):
                if joint not in KEEP_POWERED and now - since >= HOLD_SECONDS:
                    try:
                        self._release(joint)
                    except HardwareError:
                        self.held.pop(joint, None)


jarvis = Jarvis()
store = jarvis_data.Store()
chat = jarvis_chat.Chat(jarvis, (Busy, HardwareError), store)


class Handler(BaseHTTPRequestHandler):
    server_version = "Jarvis"

    def log_message(self, format, *args):
        pass

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, data):
        self._send(status, json.dumps(data).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            self._json(200, jarvis.state())
        elif self.path == "/api/assistant":
            self._json(200, store.snapshot())
        elif self.path == "/api/chat/history":
            self._json(200, {"messages": chat.history()})
        else:
            self._json(404, {"error": "Not found."})

    def _from_this_page(self):
        """Stop other websites open in the same browser from sending arm commands."""
        if self.headers.get_content_type() != "application/json":
            return False
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        origin_host = urlsplit(origin).hostname
        return urlsplit(origin).netloc == self.headers.get("Host") or origin_host == TAILSCALE_HOST

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            raise ValueError("That request is too big.")
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            raise ValueError("That request wasn't valid.") from None
        if not isinstance(data, dict):
            raise ValueError("That request wasn't valid.")
        return data

    def do_POST(self):
        if not self._from_this_page():
            self._json(403, {"error": "Commands must come from the Jarvis page."})
            return
        try:
            data = self._read_json()
            if self.path == "/api/chat":
                text = data.get("message")
                if not isinstance(text, str):
                    raise ValueError("Type a message first.")
                reply, actions, fresh = chat.send(text)
                self._json(200, {"reply": reply, "actions": actions, "fresh_start": fresh, "queued": chat.has_queued()})
            elif self.path == "/api/chat/go":
                chat.go()
                self._json(200, {"ok": True})
            elif self.path == "/api/chat/reset":
                chat.reset()
                self._json(200, {"ok": True})
            elif self.path == "/api/speak":
                text = data.get("text")
                if not isinstance(text, str):
                    raise ValueError("Nothing to say.")
                self._send(200, jarvis_chat.speak(text), "audio/mpeg")
            elif self.path == "/api/move":
                name = data.get("move")
                if not isinstance(name, str):
                    raise ValueError("Choose a move.")
                jarvis.start_move(name)
                self._json(200, jarvis.state())
            elif self.path == "/api/joint":
                joint, angle = data.get("joint"), data.get("angle")
                if type(angle) is not int or not isinstance(joint, str):
                    raise ValueError("Choose a joint and a whole-number angle.")
                jarvis.set_joint(joint, angle)
                self._json(200, jarvis.state())
            elif self.path == "/api/stop":
                chat.cancel_queued()
                jarvis.stop()
                self._json(200, jarvis.state())
            elif self.path in ("/api/tasks/toggle", "/api/tasks/remove", "/api/reminders/remove"):
                item = data.get("id")
                if not isinstance(item, str):
                    raise ValueError("Choose an item.")
                if self.path == "/api/tasks/toggle":
                    store.set_task_done(item, bool(data.get("done")))
                elif self.path == "/api/tasks/remove":
                    store.remove_task(item)
                else:
                    store.remove_reminder(item)
                self._json(200, store.snapshot())
            else:
                self._json(404, {"error": "Not found."})
        except ValueError as problem:
            self._json(400, {"error": str(problem)})
        except (Busy, jarvis_chat.ChatBusy) as problem:
            self._json(409, {"error": str(problem)})
        except (HardwareError, jarvis_chat.ChatUnavailable) as problem:
            self._json(503, {"error": str(problem)})


REMOTE_PORT = int(os.environ.get("JARVIS_REMOTE_PORT", "8001"))
MIN_TOKEN_LENGTH = 20


class RemoteHandler(Handler):
    """Arm commands for claude.ai Jarvis, sent through Composio and Tailscale Funnel.

    It only listens inside the Pi (127.0.0.1), so only Tailscale can pass requests to it,
    and every request needs the secret code. Chat and voice aren't offered here.
    """

    def _token_ok(self):
        expected = os.environ.get("JARVIS_REMOTE_TOKEN", "")
        given = self.headers.get("X-Jarvis-Token", "")
        if len(expected) >= MIN_TOKEN_LENGTH and hmac.compare_digest(given.encode(), expected.encode()):
            return True
        time.sleep(1)   # slow down anyone guessing codes
        self._json(401, {"error": "Wrong or missing secret code."})
        return False

    def do_GET(self):
        if not self._token_ok():
            return
        if self.path == "/remote/state":
            self._json(200, jarvis.state())
        else:
            self._json(404, {"error": "Not found."})

    def do_POST(self):
        if not self._token_ok():
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Send JSON."})
            return
        try:
            data = self._read_json()
            if self.path == "/remote/move":
                name = data.get("move")
                if not isinstance(name, str):
                    raise ValueError("Choose a move.")
                jarvis.start_move(name)
            elif self.path == "/remote/joint":
                joint, angle = data.get("joint"), data.get("angle")
                if type(angle) is not int or not isinstance(joint, str):
                    raise ValueError("Choose a joint and a whole-number angle.")
                if joint not in TESTED_JOINTS:
                    raise ValueError(f"{joint} can't be moved remotely until it's tested.")
                jarvis.set_joint(joint, angle)
            elif self.path == "/remote/stop":
                jarvis.stop()
            else:
                self._json(404, {"error": "Not found."})
                return
            self._json(200, jarvis.state())
        except ValueError as problem:
            self._json(400, {"error": str(problem)})
        except Busy as problem:
            self._json(409, {"error": str(problem)})
        except HardwareError as problem:
            self._json(503, {"error": str(problem)})


def start_remote_server():
    token = os.environ.get("JARVIS_REMOTE_TOKEN", "")
    if len(token) < MIN_TOKEN_LENGTH:
        print("Remote entrance is off (no secret code set)")
        return
    remote = ThreadingHTTPServer(("127.0.0.1", REMOTE_PORT), RemoteHandler)
    remote.daemon_threads = True
    threading.Thread(target=remote.serve_forever, daemon=True).start()
    print(f"Remote entrance is listening inside the Pi on port {REMOTE_PORT}")


def watch_holds():
    while True:
        time.sleep(0.5)
        jarvis.relax_expired_holds()


def shut_down(signum, frame):
    try:
        jarvis.stop()
    except HardwareError:
        pass
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, shut_down)
    threading.Thread(target=watch_holds, daemon=True).start()
    start_remote_server()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print(f"Jarvis is listening on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
