"""Jarvis: a small web server on the Pi that controls the arm from a browser page.

Starting this server never moves the arm. Only a button or slider on the page does.
Uses only Python's standard library, plus smbus2 through arm.py.
"""
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from arm import Arm, JOINTS, check_angle
from moves import DELAYS, MOVES

HOST = os.environ.get("JARVIS_HOST", "0.0.0.0")
PORT = int(os.environ.get("JARVIS_PORT", "8000"))
PAGE = Path(__file__).with_name("jarvis.html")

DEFAULT_DELAY = 1.0
HOLD_SECONDS = 10         # a slider position relaxes after this long, so servos don't strain
TESTED_JOINTS = {"claw", "base"}   # the page locks the others until unlocked
MAX_BODY_BYTES = 1024


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
                if now - since >= HOLD_SECONDS:
                    try:
                        self._release(joint)
                    except HardwareError:
                        self.held.pop(joint, None)


jarvis = Jarvis()


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
        else:
            self._json(404, {"error": "Not found."})

    def _from_this_page(self):
        """Stop other websites open in the same browser from sending arm commands."""
        if self.headers.get_content_type() != "application/json":
            return False
        origin = self.headers.get("Origin")
        return origin is None or urlsplit(origin).netloc == self.headers.get("Host")

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
            if self.path == "/api/move":
                name = data.get("move")
                if not isinstance(name, str):
                    raise ValueError("Choose a move.")
                jarvis.start_move(name)
            elif self.path == "/api/joint":
                joint, angle = data.get("joint"), data.get("angle")
                if type(angle) is not int or not isinstance(joint, str):
                    raise ValueError("Choose a joint and a whole-number angle.")
                jarvis.set_joint(joint, angle)
            elif self.path == "/api/stop":
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
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print(f"Jarvis is listening on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
