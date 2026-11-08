"""Jarvis's memory, tasks and reminders, saved on the Pi in one small JSON file."""
import json
import os
import threading
import time
import uuid
from pathlib import Path

DATA_FILE = Path(os.environ.get("JARVIS_DATA", Path.home() / ".local" / "share" / "jarvis" / "data.json"))
MAX_MEMORY = 200
MAX_TASKS = 200
MAX_REMINDERS = 100
MAX_TEXT = 300


def _id():
    return uuid.uuid4().hex[:8]


class Store:
    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.data = {"memory": [], "tasks": [], "reminders": []}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            for key in self.data:
                if isinstance(loaded.get(key), list):
                    self.data[key] = loaded[key]
        except (OSError, ValueError):
            pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _clean(text):
        text = " ".join(str(text or "").split())[:MAX_TEXT]
        if not text:
            raise ValueError("The text can't be empty.")
        return text

    @staticmethod
    def _match(items, words, field):
        words = str(words or "").strip().lower()
        if not words:
            return None
        for item in items:
            if item["id"] == words:
                return item
        for item in items:
            if words in item[field].lower():
                return item
        return None

    def _fire_due(self):
        now = time.time()
        changed = False
        for reminder in self.data["reminders"]:
            if not reminder.get("fired") and reminder["at"] <= now:
                reminder["fired"] = True
                changed = True
        if changed:
            self._save()

    def snapshot(self):
        with self.lock:
            self._fire_due()
            return json.loads(json.dumps(self.data))

    # ---- memory ----
    def remember(self, text):
        with self.lock:
            self.data["memory"].append({"id": _id(), "text": self._clean(text)})
            self.data["memory"] = self.data["memory"][-MAX_MEMORY:]
            self._save()
            return "Remembered."

    def forget(self, words):
        with self.lock:
            item = self._match(self.data["memory"], words, "text")
            if not item:
                raise ValueError("Nothing in memory matches that.")
            self.data["memory"].remove(item)
            self._save()
            return f"Forgot: {item['text']}"

    # ---- tasks ----
    def add_task(self, text):
        with self.lock:
            if len(self.data["tasks"]) >= MAX_TASKS:
                raise ValueError("The task list is full. Remove some first.")
            self.data["tasks"].insert(0, {"id": _id(), "text": self._clean(text), "done": False})
            self._save()
            return "Task added."

    def set_task_done(self, words, done=True):
        with self.lock:
            item = self._match(self.data["tasks"], words, "text")
            if not item:
                raise ValueError("No task matches that.")
            item["done"] = bool(done)
            self._save()
            return f"Marked {'done' if done else 'not done'}: {item['text']}"

    def remove_task(self, words):
        with self.lock:
            item = self._match(self.data["tasks"], words, "text")
            if not item:
                raise ValueError("No task matches that.")
            self.data["tasks"].remove(item)
            self._save()
            return f"Removed: {item['text']}"

    # ---- reminders ----
    def add_reminder(self, label, minutes):
        minutes = float(minutes)
        if not 0 < minutes <= 7 * 24 * 60:
            raise ValueError("Reminders can be set from 1 minute to 7 days ahead.")
        with self.lock:
            if len(self.data["reminders"]) >= MAX_REMINDERS:
                raise ValueError("Too many reminders. Remove some first.")
            at = time.time() + minutes * 60
            self.data["reminders"].append({"id": _id(), "label": self._clean(label), "at": at, "fired": False})
            self.data["reminders"].sort(key=lambda r: r["at"])
            self._save()
            return "Reminder set for " + time.strftime("%H:%M on %a %d %b", time.localtime(at)) + "."

    def remove_reminder(self, words):
        with self.lock:
            item = self._match(self.data["reminders"], words, "label")
            if not item:
                raise ValueError("No reminder matches that.")
            self.data["reminders"].remove(item)
            self._save()
            return f"Removed reminder: {item['label']}"

    def context(self):
        """A short summary for Jarvis's instructions."""
        snap = self.snapshot()
        memory = "\n".join("- " + m["text"] for m in snap["memory"]) or "(nothing yet)"
        tasks = "\n".join(f"- [{'x' if t['done'] else ' '}] {t['text']}" for t in snap["tasks"]) or "(empty)"
        upcoming = [r for r in snap["reminders"] if not r["fired"]]
        reminders = "\n".join(
            f"- {r['label']} at " + time.strftime("%H:%M %a %d %b", time.localtime(r["at"])) for r in upcoming
        ) or "(none)"
        return (f"WHAT YOU KNOW ABOUT THE USER:\n{memory}\n\nTO-DO LIST:\n{tasks}\n\n"
                f"UPCOMING REMINDERS:\n{reminders}")
