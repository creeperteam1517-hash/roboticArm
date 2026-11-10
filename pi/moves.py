"""Named moves. To add one, add a name and its list of (joint, angle) steps."""

MOVES = {
    "claw_wiggle": [
        ("claw", 45),
        ("claw", 60),
        ("claw", 45),
        ("claw", 30),
        ("claw", 45),
    ],
    "clap": [
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 45),
    ],
    "wave": [
        ("base", 70),
        ("base", 110),
        ("base", 90),
    ],
    "base_sweep": [
        ("base", 0),
        ("base", 180),
        ("base", 0),
        ("base", 180),
    ],
    "victory_dance": [
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 45),
        ("base", 60),
        ("base", 120),
        ("base", 90),
    ],
    "nod": [
        ("shoulder", 20), ("shoulder", 40),
        ("shoulder", 20), ("shoulder", 40),
        ("shoulder", 30),
    ],
    "shake_head": [
        ("base", 60), ("base", 120),
        ("base", 60), ("base", 120),
        ("base", 90),
    ],
    "look_left": [
        ("base", 20),
        ("base", 20),
        ("base", 90),
    ],
    "look_right": [
        ("base", 160),
        ("base", 160),
        ("base", 90),
    ],
    "scan": [
        ("base", 0),
        ("base", 45),
        ("base", 90),
        ("base", 135),
        ("base", 180),
        ("base", 90),
    ],
    "pendulum": [
        ("base", 45), ("base", 135),
        ("base", 60), ("base", 120),
        ("base", 75), ("base", 105),
        ("base", 90),
    ],
    "snap": [
        ("claw", 80),
        ("claw", 10),
        ("claw", 45),
    ],
    "chomp": [
        ("claw", 70), ("claw", 20),
        ("claw", 70), ("claw", 20),
        ("claw", 70), ("claw", 20),
        ("claw", 45),
    ],
    "drum_roll": [
        ("claw", 40), ("claw", 55),
        ("claw", 40), ("claw", 55),
        ("claw", 40), ("claw", 55),
        ("claw", 40), ("claw", 55),
        ("claw", 45),
    ],
    "grab": [
        ("claw", 80),
        ("claw", 15),
    ],
    "release": [
        ("claw", 80),
        ("claw", 45),
    ],
    "high_five": [
        ("base", 90),
        ("claw", 80),
        ("claw", 10),
        ("claw", 45),
    ],
    "spin_and_snap": [
        ("base", 0), ("claw", 80), ("claw", 10),
        ("base", 180), ("claw", 80), ("claw", 10),
        ("base", 90), ("claw", 45),
    ],
    "party": [
        ("base", 60), ("claw", 80),
        ("base", 120), ("claw", 10),
        ("base", 60), ("claw", 80),
        ("base", 120), ("claw", 10),
        ("base", 90), ("claw", 45),
    ],
    "sleepy": [
        ("base", 100),
        ("base", 85),
        ("base", 95),
        ("base", 90),
        ("claw", 10),
    ],
}

# Seconds to wait after each step, for moves that don't use the normal 1 second.
DELAYS = {
    "clap": 0.5,
    "victory_dance": 0.5,
    "nod": 0.6,
    "shake_head": 0.6,
    "pendulum": 0.8,
    "snap": 0.5,
    "chomp": 0.4,
    "drum_roll": 0.25,
    "spin_and_snap": 0.8,
    "party": 0.6,
    "sleepy": 1.5,
}
