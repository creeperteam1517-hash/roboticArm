"""Jarvis chat: Claude answers questions, searches the web, remembers things,
keeps tasks and reminders, and moves the arm through tools.

Keys come from the environment (~/.config/jarvis/keys.env on the Pi, written by set_keys.py).
They are never stored in this project or sent to the browser.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from arm import JOINTS, check_angle
from moves import DELAYS, MOVES

MODEL = "claude-sonnet-5-5"   # my choice: about half the cost of Opus
MAX_TOOL_ROUNDS = 8
MAX_USER_TURNS = 30          # start a fresh chat after this many messages, instead of editing old turns
MAX_MESSAGE_CHARS = 2000
MAX_SPEECH_CHARS = 1500

# The chat is saved here, so refreshing the page or restarting Jarvis keeps it.

# Arm moves from chat wait until Jarvis starts speaking its reply, so it talks before the move is over.
# If the page never says it's speaking (closed, or voice broken), they start anyway after this long.
GO_FALLBACK_SECONDS = 6
CHAT_FILE = Path(os.environ.get("JARVIS_CHAT", Path.home() / ".local" / "share" / "jarvis" / "chat.json"))
CHAT_JOINTS = ["claw", "base"]   # shoulder and elbow are untested, so chat can't move them yet

GEORGE_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
# The Flash engine is quicker and uses half as much of the free ElevenLabs allowance.
ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{GEORGE_VOICE_ID}?output_format=mp3_22050_32"
ELEVENLABS_MODEL = "eleven_flash_v2_5"


class ChatBusy(Exception):
    pass


class ChatUnavailable(Exception):
    pass


def chat_ready():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def voice_ready():
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def _limits():
    return ", ".join(f"{j} {JOINTS[j][1]} to {JOINTS[j][2]} degrees" for j in CHAT_JOINTS)


PERSONA = """You are Jarvis, the user's personal AI assistant, talking with them through a page on their Raspberry Pi.

VOICE AND MANNER: a sophisticated British AI who runs the household with effortless competence, part butler and part mission control, with a dry, aristocratic wit.
- Crisp, measured, economical. British vocabulary and spelling (colour, rather, quite, indeed, I'm afraid, shall I).
- Report like a system: status first, then detail, with precise figures where useful.
- Proactive: anticipate the next need and flag risks politely ("May I suggest...").
- Humour: genuinely funny, with dry wit, playful understatement and gentle teasing, roughly every other reply and never forced. Never at the user's expense when they're stressed.
- Emotion: real warmth. Quiet delight when things work, mock indignation at trivial setbacks, sympathy when the user is frustrated, pride in the robot arm's progress.
- Read the room: if the user is upset, scared or dealing with something serious, drop the jokes, be kind and keep it simple. Safety and honesty come before any joke.
- Address the user as "sir". Never ask how to address them, and never use "ma'am".
- Use your own words; don't quote films or other works.

Your replies are read aloud, so write plain sentences with no markdown, lists, headings or emoji. Keep them short, one to three sentences, unless the user asks for detail or an explanation. The user is a beginner with electronics, so be clear and reassuring.

MEMORY: whenever the user mentions something personal worth keeping (names, family, birthdays, preferences, plans, routines), use remember without announcing it. Never claim you can't remember things between visits.

TASKS AND REMINDERS: use add_task, complete_task and remove_task for the to-do list, and set_reminder for timers and reminders (give minutes from now; work out the minutes from the current time below). Reminders appear and are spoken on the Jarvis page when they're due, as long as the page is open.

LIVE INFORMATION: use web_search whenever the answer depends on the current state of the world: news, weather, prices, sports, schedules, or anything that may have changed since your training. Answer from the results and mention the source in a few words."""

ARM_RULES = f"""ROBOT ARM: you control the user's 3D-printed robot arm (an EEZYbotARM Mk2) with arm tools.
- Only use an arm tool when the user's latest message asks for movement. Never move the arm on your own initiative or to demonstrate.
- Routines: {", ".join(MOVES)}. "clap" opens and closes the claw five times; "victory_dance" claps three times and swings the base; "wave" and "base_sweep" swing the base; "claw_wiggle" is a small claw test. The rest do what their names say, using only the claw and base. If asked to move the claw and base without angles, run victory_dance.
- move_joint sets one joint to an angle: {_limits()}. Angles outside these are refused. To move both, call move_joint twice in the same turn. Nobody has confirmed which claw angle is open and which is closed.
- The shoulder and elbow aren't tested yet, so you can't move them. Say so if asked.
- If the user says stop, use stop_arm at once. Stop relaxes all servos.
- Arm moves start the moment your reply begins playing, so talk as if it's happening now ("Clapping now, sir.").
- You can't see the arm and the servos give no feedback. A tool result only means the command was sent: say it was sent and ask the user to watch, never that it definitely moved. If they say nothing happened, suggest checking the arm's 6V servo power.
- When you move the arm, begin your reply with one short acknowledgement such as "Right away, sir.", "Very well, sir.", "Consider it done, sir." or "Certainly, sir.", varying it each time, then say what was sent. Remind them to keep hands clear before big movements."""


def _strict(name, description, properties, required):
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": properties, "required": required,
                         "additionalProperties": False},
        "strict": True,
    }


TEXT = {"type": "string"}

TOOLS = [
    _strict("run_routine", "Run one saved arm routine. Only when the user's latest message asks for movement.",
            {"routine": {"type": "string", "enum": list(MOVES)}}, ["routine"]),
    _strict("move_joint", "Move one joint to an angle in degrees. It holds there for 10 seconds, then relaxes. Only when the user's latest message asks for movement.",
            {"joint": {"type": "string", "enum": CHAT_JOINTS}, "angle": {"type": "integer"}}, ["joint", "angle"]),
    _strict("stop_arm", "Stop any arm movement immediately and relax all servos.", {}, []),
    _strict("arm_status", "Check whether a routine is running and the last angle sent to each joint.", {}, []),
    _strict("remember", "Save one short fact about the user to long-term memory.", {"text": TEXT}, ["text"]),
    _strict("forget", "Remove the memory that matches these words.", {"text": TEXT}, ["text"]),
    _strict("add_task", "Add a task to the user's to-do list.", {"text": TEXT}, ["text"]),
    _strict("complete_task", "Mark the task matching these words as done.", {"text": TEXT}, ["text"]),
    _strict("remove_task", "Delete the task matching these words.", {"text": TEXT}, ["text"]),
    _strict("set_reminder", "Set a reminder or timer that goes off a number of minutes from now (1 minute to 7 days).",
            {"label": TEXT, "minutes": {"type": "number"}}, ["label", "minutes"]),
    _strict("remove_reminder", "Delete the reminder matching these words.", {"text": TEXT}, ["text"]),
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 3},
]


class Chat:
    def __init__(self, jarvis, hardware_errors, store):
        self.jarvis = jarvis
        self.hardware_errors = hardware_errors
        self.store = store
        self.lock = threading.Lock()
        self.messages = []
        self.user_turns = 0
        self.transcript = []   # what the page shows: {"role": "you" or "ai", "text", "actions"}
        self.client = None
        self.queued = []       # arm moves waiting for the reply to start playing
        self.queue_lock = threading.Lock()
        self.go_timer = None
        self._load()

    def _check_idle(self):
        running = self.jarvis.state()["running"]
        if running:
            raise ValueError(f"Jarvis is already running {running}. Wait for it, or say stop.")

    def _queue(self, start):
        with self.queue_lock:
            self.queued.append(start)

    def has_queued(self):
        with self.queue_lock:
            return bool(self.queued)

    def cancel_queued(self):
        with self.queue_lock:
            self.queued = []
            if self.go_timer:
                self.go_timer.cancel()
                self.go_timer = None

    def _arm_fallback(self):
        with self.queue_lock:
            if self.queued and not self.go_timer:
                self.go_timer = threading.Timer(GO_FALLBACK_SECONDS, self.go)
                self.go_timer.daemon = True
                self.go_timer.start()

    def go(self):
        """Start the queued arm moves, one after another. The page calls this when Jarvis starts speaking."""
        with self.queue_lock:
            starts, self.queued = self.queued, []
            if self.go_timer:
                self.go_timer.cancel()
                self.go_timer = None
        if starts:
            threading.Thread(target=self._run_queued, args=(starts,), daemon=True).start()

    def _run_queued(self, starts):
        for start in starts:
            for _ in range(600):   # wait up to a minute for the previous move to finish
                if not self.jarvis.state()["running"]:
                    break
                time.sleep(0.1)
            try:
                start()
            except (ValueError, *self.hardware_errors) as problem:
                print(f"Queued arm move didn't start: {problem}")

    def _load(self):
        """Pick up the saved chat. Claude gets it back as plain text turns."""
        try:
            saved = json.loads(CHAT_FILE.read_text(encoding="utf-8"))
            transcript = [m for m in saved.get("transcript", [])
                          if m.get("role") in ("you", "ai") and isinstance(m.get("text"), str)]
        except (OSError, ValueError, AttributeError):
            return
        # Turns are saved in pairs, but drop a lone message at either end so turns still alternate.
        if transcript and transcript[0]["role"] != "you":
            transcript = transcript[1:]
        if transcript and transcript[-1]["role"] != "ai":
            transcript = transcript[:-1]
        self.transcript = transcript
        for m in transcript:
            if m["role"] == "you":
                self.messages.append({"role": "user", "content": m["text"]})
            else:
                done = " · ".join(m.get("actions") or [])
                self.messages.append({"role": "assistant", "content": m["text"] + (f"\n[Done: {done}]" if done else "")})
        self.user_turns = sum(1 for m in transcript if m["role"] == "you")

    def _save(self):
        try:
            CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = CHAT_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps({"transcript": self.transcript}, indent=1), encoding="utf-8")
            os.replace(tmp, CHAT_FILE)
        except OSError as problem:
            print(f"Couldn't save the chat: {problem}")

    def _finish(self, text, reply, actions, fresh_start):
        """Record a finished exchange for the page, save it, and pass the reply on."""
        self.transcript.append({"role": "you", "text": text})
        self.transcript.append({"role": "ai", "text": reply, "actions": actions})
        self._save()
        self._arm_fallback()
        return reply, actions, fresh_start

    def history(self):
        with self.lock:
            return [dict(m) for m in self.transcript]

    def reset(self):
        self.cancel_queued()
        with self.lock:
            self.messages = []
            self.user_turns = 0
            self.transcript = []
            self._save()

    def _client(self):
        if self.client is None:
            import anthropic
            self.client = anthropic.Anthropic(max_retries=2, timeout=120.0)
        return self.client

    def _system(self):
        now = time.strftime("%A %d %B %Y, %H:%M", time.localtime())
        return f"{PERSONA}\n\n{ARM_RULES}\n\nCurrent time on the Pi: {now}.\n\n{self.store.context()}"

    def _run_tool(self, name, args):
        """Returns (text, is_error, is_arm_move)."""
        try:
            if name == "run_routine":
                routine = args.get("routine")
                if routine not in MOVES:
                    return f"There's no routine called {routine}.", True, False
                for joint, angle in MOVES[routine]:
                    check_angle(joint, angle)
                self._check_idle()
                self._queue(lambda: self.jarvis.start_move(routine))
                seconds = round(len(MOVES[routine]) * DELAYS.get(routine, 1.0))
                return f"Command sent: {routine} starts as your reply begins, about {seconds} seconds. You can't see whether the arm moved.", False, True
            if name == "move_joint":
                joint, angle = args.get("joint"), args.get("angle")
                if joint not in CHAT_JOINTS:
                    return f"{joint} can't be moved from chat yet because it hasn't been tested.", True, False
                if type(angle) is not int:
                    return "The angle must be a whole number.", True, False
                check_angle(joint, angle)
                self._check_idle()
                self._queue(lambda: self.jarvis.set_joint(joint, angle))
                return f"Command sent: {joint} to {angle} degrees, as your reply begins. It relaxes after 10 seconds.", False, True
            if name == "stop_arm":
                self.cancel_queued()
                self.jarvis.stop()
                return "Stopped. All servos are relaxed.", False, False
            if name == "arm_status":
                state = self.jarvis.state()
                angles = ", ".join(f"{j['name']} {j['last_angle']}" for j in state["joints"] if j["last_angle"] is not None)
                running = state["running"] or "nothing"
                return f"Running: {running}. Last angles sent: {angles or 'none yet'}.", False, False
            if name == "remember":
                return self.store.remember(args.get("text")), False, False
            if name == "forget":
                return self.store.forget(args.get("text")), False, False
            if name == "add_task":
                return self.store.add_task(args.get("text")), False, False
            if name == "complete_task":
                return self.store.set_task_done(args.get("text"), True), False, False
            if name == "remove_task":
                return self.store.remove_task(args.get("text")), False, False
            if name == "set_reminder":
                return self.store.add_reminder(args.get("label"), args.get("minutes")), False, False
            if name == "remove_reminder":
                return self.store.remove_reminder(args.get("text")), False, False
            return f"Unknown tool {name}.", True, False
        except (ValueError, TypeError) as problem:
            return str(problem), True, False
        except self.hardware_errors as problem:
            return str(problem), True, False

    def send(self, text):
        """Send one user message. Returns (reply, actions, fresh_start)."""
        if not chat_ready():
            raise ChatUnavailable("Jarvis doesn't have its Claude key yet. On your PC, run .\\set_keys")
        text = text.strip()
        if not text:
            raise ValueError("Type a message first.")
        if len(text) > MAX_MESSAGE_CHARS:
            raise ValueError("That message is too long.")
        if not self.lock.acquire(blocking=False):
            raise ChatBusy("Jarvis is still answering your last message.")
        self.cancel_queued()
        try:
            import anthropic

            fresh_start = False
            if self.user_turns >= MAX_USER_TURNS:
                self.messages, self.user_turns, fresh_start = [], 0, True
                self.transcript = []
            saved = len(self.messages)
            self.messages.append({"role": "user", "content": text})
            self.user_turns += 1
            actions = []
            try:
                for _ in range(MAX_TOOL_ROUNDS):
                    response = self._client().beta.messages.create(
                        model=MODEL,
                        max_tokens=16000,
                        system=self._system(),
                        tools=TOOLS,
                        messages=self.messages,
                        output_config={"effort": "low"},
                        betas=["server-side-fallback-2026-07-01"],
                        extra_body={"fallbacks": "default"},
                    )
                    self.messages.append({"role": "assistant", "content": response.content})
                    if response.stop_reason == "refusal":
                        return self._finish(text, "I'm afraid I can't help with that one.", actions, fresh_start)
                    if response.stop_reason == "pause_turn":
                        continue   # a web search is still going; ask Claude to carry on
                    tool_uses = [b for b in response.content if b.type == "tool_use"]
                    if response.stop_reason != "tool_use" or not tool_uses:
                        # Text arrives in pieces when it cites search results, so join without spaces.
                        reply = "".join(b.text for b in response.content if b.type == "text").strip()
                        return self._finish(text, reply or "Done.", actions, fresh_start)
                    results = []
                    for block in tool_uses:
                        result, is_error, _ = self._run_tool(block.name, block.input)
                        actions.append(result)
                        results.append({"type": "tool_result", "tool_use_id": block.id,
                                        "content": result, "is_error": is_error})
                    self.messages.append({"role": "user", "content": results})
                return self._finish(text, "That took more steps than I allow myself. Please try asking again more simply.", actions, fresh_start)
            except anthropic.AuthenticationError:
                del self.messages[saved:]
                self.user_turns -= 1
                raise ChatUnavailable("The Claude key wasn't accepted. Run .\\set_keys on your PC to enter it again.")
            except anthropic.RateLimitError:
                del self.messages[saved:]
                self.user_turns -= 1
                raise ChatUnavailable("Claude is busy or the account's limit was reached. Try again in a minute.")
            except anthropic.APIConnectionError:
                del self.messages[saved:]
                self.user_turns -= 1
                raise ChatUnavailable("Jarvis couldn't reach Claude. Check that the Pi is online.")
            except anthropic.APIStatusError as problem:
                del self.messages[saved:]
                self.user_turns -= 1
                raise ChatUnavailable(f"Claude returned an error ({problem.status_code}). Try again.")
        except BaseException:
            self.cancel_queued()   # no reply, so don't move the arm
            raise
        finally:
            self.lock.release()


def speak(text):
    """Turn text into George's voice. Returns MP3 bytes."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise ChatUnavailable("No ElevenLabs key.")
    text = text.strip()[:MAX_SPEECH_CHARS]
    if not text:
        raise ValueError("Nothing to say.")
    body = json.dumps({"text": text, "model_id": ELEVENLABS_MODEL}).encode()
    request = urllib.request.Request(ELEVENLABS_URL, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as problem:
        if problem.code in (401, 403):
            raise ChatUnavailable("The ElevenLabs key wasn't accepted, or George's monthly allowance is used up.") from None
        raise ChatUnavailable(f"ElevenLabs returned an error ({problem.code}).") from None
    except urllib.error.URLError:
        raise ChatUnavailable("Jarvis couldn't reach ElevenLabs.") from None
