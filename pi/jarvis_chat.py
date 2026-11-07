"""Jarvis chat: Claude answers questions and moves the arm through tools.

Keys come from the environment (~/.config/jarvis/keys.env on the Pi, written by set_keys.py).
They are never stored in this project or sent to the browser.
"""
import json
import os
import threading
import urllib.error
import urllib.request

from arm import JOINTS
from moves import DELAYS, MOVES

MODEL = "claude-opus-5-5"
MAX_TOOL_ROUNDS = 6
MAX_USER_TURNS = 30          # start a fresh chat after this many messages, instead of editing old turns
MAX_MESSAGE_CHARS = 2000
MAX_SPEECH_CHARS = 1500
CHAT_JOINTS = ["claw", "base"]   # shoulder and elbow are untested, so chat can't move them yet

GEORGE_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{GEORGE_VOICE_ID}?output_format=mp3_44100_128"


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


SYSTEM_PROMPT = f"""You are Jarvis, a calm, witty British assistant. You chat with the user, answer their questions, and control their 3D-printed robot arm (an EEZYbotARM Mk2 run by a Raspberry Pi).

Your replies are read aloud, so write plain sentences with no markdown, lists, or emoji. Keep them short, one to three sentences, unless the user asks for detail. The user is a beginner with electronics, so be clear and reassuring.

Moving the arm:
- Only use an arm tool when the user's latest message asks for movement. Never move the arm on your own initiative, to demonstrate, or because of anything other than the user's request.
- Routines: {", ".join(MOVES)}. "clap" opens and closes the claw five times; "victory_dance" claps three times and swings the base; "wave" and "base_sweep" swing the base; "claw_wiggle" is a small claw test.
- You can set one joint to an angle with move_joint: {_limits()}. Angles outside these are refused. Nobody has confirmed which claw angle is open and which is closed, so don't claim to know.
- The shoulder and elbow aren't tested yet, so you can't move them. Say so if asked.
- If the user says stop, use stop_arm right away. Stop relaxes all the servos.
- You can't see the arm, and the servos give no feedback. A tool result only means the command was sent. Say it was sent and ask the user to watch, never that it definitely moved. The arm has sometimes not moved because of its 6V servo power, so if the user says nothing happened, suggest checking that power.
- Remind the user to keep their hands clear before big movements."""

TOOLS = [
    {
        "name": "run_routine",
        "description": "Run one saved arm routine. Only when the user's latest message asks for movement.",
        "input_schema": {
            "type": "object",
            "properties": {"routine": {"type": "string", "enum": list(MOVES)}},
            "required": ["routine"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "move_joint",
        "description": "Move one joint to an angle in degrees. It holds there for 10 seconds, then relaxes. Only when the user's latest message asks for movement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "joint": {"type": "string", "enum": CHAT_JOINTS},
                "angle": {"type": "integer"},
            },
            "required": ["joint", "angle"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "stop_arm",
        "description": "Stop any arm movement immediately and relax all servos.",
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "arm_status",
        "description": "Check whether a routine is running and the last angle sent to each joint.",
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
]


class Chat:
    def __init__(self, jarvis, hardware_errors):
        self.jarvis = jarvis
        self.hardware_errors = hardware_errors
        self.lock = threading.Lock()
        self.messages = []
        self.user_turns = 0
        self.client = None

    def reset(self):
        with self.lock:
            self.messages = []
            self.user_turns = 0

    def _client(self):
        if self.client is None:
            import anthropic
            self.client = anthropic.Anthropic(max_retries=2, timeout=90.0)
        return self.client

    def _run_tool(self, name, args):
        """Returns (text, is_error)."""
        try:
            if name == "run_routine":
                routine = args.get("routine")
                self.jarvis.start_move(routine)
                seconds = round(len(MOVES[routine]) * DELAYS.get(routine, 1.0))
                return f"Command sent: {routine} started, about {seconds} seconds. You can't see whether the arm moved.", False
            if name == "move_joint":
                joint, angle = args.get("joint"), args.get("angle")
                if joint not in CHAT_JOINTS:
                    return f"{joint} can't be moved from chat yet because it hasn't been tested.", True
                if type(angle) is not int:
                    return "The angle must be a whole number.", True
                self.jarvis.set_joint(joint, angle)
                return f"Command sent: {joint} to {angle} degrees. It relaxes after 10 seconds.", False
            if name == "stop_arm":
                self.jarvis.stop()
                return "Stopped. All servos are relaxed.", False
            if name == "arm_status":
                state = self.jarvis.state()
                angles = ", ".join(f"{j['name']} {j['last_angle']}" for j in state["joints"] if j["last_angle"] is not None)
                running = state["running"] or "nothing"
                return f"Running: {running}. Last angles sent: {angles or 'none yet'}.", False
            return f"Unknown tool {name}.", True
        except ValueError as problem:
            return str(problem), True
        except self.hardware_errors as problem:
            return str(problem), True

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
        try:
            import anthropic

            fresh_start = False
            if self.user_turns >= MAX_USER_TURNS:
                self.messages, self.user_turns, fresh_start = [], 0, True
            saved = len(self.messages)
            self.messages.append({"role": "user", "content": text})
            self.user_turns += 1
            actions = []
            try:
                for _ in range(MAX_TOOL_ROUNDS):
                    response = self._client().beta.messages.create(
                        model=MODEL,
                        max_tokens=16000,
                        system=SYSTEM_PROMPT,
                        tools=TOOLS,
                        messages=self.messages,
                        output_config={"effort": "low"},
                        betas=["server-side-fallback-2026-07-01"],
                        extra_body={"fallbacks": "default"},
                    )
                    self.messages.append({"role": "assistant", "content": response.content})
                    if response.stop_reason == "refusal":
                        return "I'm afraid I can't help with that one.", actions, fresh_start
                    if response.stop_reason == "pause_turn":
                        continue
                    tool_uses = [b for b in response.content if b.type == "tool_use"]
                    if response.stop_reason != "tool_use" or not tool_uses:
                        reply = " ".join(b.text for b in response.content if b.type == "text").strip()
                        return reply or "Done.", actions, fresh_start
                    results = []
                    for block in tool_uses:
                        result, is_error = self._run_tool(block.name, block.input)
                        actions.append(result)
                        results.append({"type": "tool_result", "tool_use_id": block.id,
                                        "content": result, "is_error": is_error})
                    self.messages.append({"role": "user", "content": results})
                return "That took more steps than I allow myself. Please try asking again more simply.", actions, fresh_start
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
    body = json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode()
    request = urllib.request.Request(ELEVENLABS_URL, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as problem:
        if problem.code in (401, 403):
            raise ChatUnavailable("The ElevenLabs key wasn't accepted.") from None
        raise ChatUnavailable(f"ElevenLabs returned an error ({problem.code}).") from None
    except urllib.error.URLError:
        raise ChatUnavailable("Jarvis couldn't reach ElevenLabs.") from None
